"""Tool allow-list, Groq function-calling schemas, and bounded dispatch.

This is the only place a tool name coming back from the model is ever
turned into an actual function call. `dispatch_tool_call` is the single
choke point that enforces: the tool is on the allow-list, its arguments
parse and validate, the caller is authorized, execution failures are
caught and turned into safe messages (never a raw exception/stack
trace), and the tool's own output is schema-validated before it is
trusted. It always returns a plain, JSON-serializable dict - it never
raises - so the tool-calling loop in llm/service.py can treat every
outcome uniformly.
"""

import json
import logging
import sqlite3
from dataclasses import dataclass
from typing import Any, Callable

from pydantic import BaseModel, ValidationError

from auth import Actor
from tools import tickets, timetable
from tools.schemas import (
    ALLOWED_TICKET_CATEGORIES,
    CheckTimetableInput,
    CheckTimetableOutput,
    CreateSupportTicketInput,
    CreateSupportTicketOutput,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ToolContext:
    """Paths/config the tool executors need - not secrets, never sent to the model."""

    timetable_data_path: str
    tickets_db_path: str


@dataclass(frozen=True)
class ToolSpec:
    input_model: type[BaseModel]
    output_model: type[BaseModel]
    allowed_roles: frozenset[str]
    executor: Callable[[BaseModel, ToolContext], BaseModel]


def _run_check_timetable(input_data: CheckTimetableInput, ctx: ToolContext) -> CheckTimetableOutput:
    return timetable.check_timetable(input_data, data_path=ctx.timetable_data_path)


def _run_create_support_ticket(
    input_data: CreateSupportTicketInput, ctx: ToolContext
) -> CreateSupportTicketOutput:
    return tickets.create_support_ticket(input_data, db_path=ctx.tickets_db_path)


TOOL_REGISTRY: dict[str, ToolSpec] = {
    "check_timetable": ToolSpec(
        input_model=CheckTimetableInput,
        output_model=CheckTimetableOutput,
        allowed_roles=frozenset({"student", "staff"}),
        executor=_run_check_timetable,
    ),
    "create_support_ticket": ToolSpec(
        input_model=CreateSupportTicketInput,
        output_model=CreateSupportTicketOutput,
        allowed_roles=frozenset({"student", "staff"}),
        executor=_run_create_support_ticket,
    ),
}


TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "check_timetable",
            "description": (
                "Retrieve real class schedule sessions for a course code from the "
                "university's timetable data. Use this whenever a student asks when "
                "or where a course meets. Never guess or invent a schedule yourself."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "course_code": {
                        "type": "string",
                        "description": "The course code, e.g. 'BSE4104'.",
                    },
                    "date": {
                        "type": "string",
                        "description": "Optional ISO date (YYYY-MM-DD) to filter to one session.",
                    },
                },
                "required": ["course_code"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_support_ticket",
            "description": (
                "Create a DRAFT support ticket (status PENDING_APPROVAL) for a "
                "student's support request. This does NOT submit, resolve, or act on "
                "the request - a human must approve it separately before anything "
                "happens. Use this when a student describes a problem needing "
                "follow-up (e.g. portal access, a technical issue, a process query "
                "that needs staff attention)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "enum": list(ALLOWED_TICKET_CATEGORIES),
                    },
                    "subject": {"type": "string", "description": "Short summary, under 200 chars."},
                    "description": {"type": "string", "description": "Full details of the issue."},
                },
                "required": ["category", "subject", "description"],
            },
        },
    },
]


def dispatch_tool_call(
    tool_name: str, arguments_json: str, actor: Actor, ctx: ToolContext
) -> dict:
    """Execute one model-requested tool call. Never raises - always returns a dict."""
    spec = TOOL_REGISTRY.get(tool_name)
    if spec is None:
        logger.warning("Rejected call to unregistered tool: %s", tool_name)
        return {"success": False, "error": f"Tool {tool_name!r} is not available."}

    try:
        raw_arguments = json.loads(arguments_json) if arguments_json else {}
    except json.JSONDecodeError:
        return {"success": False, "error": "Tool arguments were not valid JSON."}

    if actor.role not in spec.allowed_roles:
        logger.warning("Unauthorized tool call: tool=%s role=%s", tool_name, actor.role)
        return {"success": False, "error": f"You are not authorized to use {tool_name!r}."}

    try:
        input_data = spec.input_model.model_validate(raw_arguments)
    except ValidationError as exc:
        return {"success": False, "error": f"Invalid input for {tool_name!r}: {exc.errors()[0]['msg']}"}

    try:
        result = spec.executor(input_data, ctx)
    except (OSError, json.JSONDecodeError, KeyError) as exc:
        logger.error("Timetable data unavailable for %s: %s", tool_name, exc)
        return {
            "success": False,
            "error": "The timetable service is temporarily unavailable. Please try again later.",
        }
    except sqlite3.Error as exc:
        logger.error("Ticket store unavailable for %s: %s", tool_name, exc)
        return {
            "success": False,
            "error": "The support ticket service is temporarily unavailable. Please try again later.",
        }
    except Exception:  # noqa: BLE001 - never let a tool crash the request or leak internals
        logger.exception("Unexpected error executing tool %s", tool_name)
        return {"success": False, "error": "The tool encountered an unexpected error."}

    if not isinstance(result, spec.output_model):
        try:
            result = spec.output_model.model_validate(result)
        except ValidationError:
            logger.error("Tool %s returned a response that failed output validation.", tool_name)
            return {
                "success": False,
                "error": f"The {tool_name!r} tool returned an unexpected response.",
            }

    return result.model_dump()
