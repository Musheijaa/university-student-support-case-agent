"""LLM service: orchestrates retrieval, tool calling, prompt selection, and the Groq client.

This is the seam the API route talks to. It knows nothing about HTTP;
it just turns a student message into a grounded model reply plus the
sources/tool calls that reply is grounded in.

Week 3 added a retrieval step ahead of the client call for RAG prompt
versions. Week 4 adds a bounded tool-calling loop for "tools-" prompt
versions: the model is offered the registered tools (see
tools/registry.py) alongside the same retrieved evidence, and if it
requests a tool, this module - not the model - executes it (via
tools.registry.dispatch_tool_call, which enforces the allow-list,
schema validation, and authorization) and feeds the result back before
asking the model for a final answer. The loop is bounded by
`settings.max_tool_calls` so it always terminates.
"""

import json
from dataclasses import dataclass, field
from typing import Any

from auth import Actor
from config import Settings, get_settings
from llm.client import GroqClient, LLMConfigurationError, LLMRequestError
from llm.prompts import build_rag_user_message, get_prompt
from rag.context_builder import Source, build_evidence_block, build_sources
from rag.retriever import retrieve
from rag.vector_store import get_vector_store
from tools.registry import TOOL_DEFINITIONS, ToolContext, dispatch_tool_call

__all__ = [
    "LLMConfigurationError",
    "LLMRequestError",
    "StudentSupportResult",
    "ToolInvocation",
    "get_student_support_response",
]

DEFAULT_ACTOR = Actor(role="student", user_id="anonymous")


@dataclass(frozen=True)
class ToolInvocation:
    tool: str
    arguments: dict
    result: dict


@dataclass(frozen=True)
class StudentSupportResult:
    response: str
    prompt_version: str
    model: str
    sources: list[Source] = field(default_factory=list)
    tool_calls: list[ToolInvocation] = field(default_factory=list)


def _retrieve_evidence(student_message: str, settings: Settings) -> tuple[str, list[Source]]:
    vector_store = get_vector_store(
        persist_directory=settings.chroma_persist_directory,
        collection_name=settings.rag_collection_name,
    )
    retrieved_chunks = retrieve(
        vector_store=vector_store,
        question=student_message,
        top_k=settings.rag_top_k,
        min_score=settings.rag_min_score,
    )
    return build_evidence_block(retrieved_chunks), build_sources(retrieved_chunks)


def _assistant_message_dict(message: Any) -> dict:
    return {
        "role": "assistant",
        "content": message.content or "",
        "tool_calls": [
            {
                "id": tc.id,
                "type": "function",
                "function": {"name": tc.function.name, "arguments": tc.function.arguments},
            }
            for tc in message.tool_calls
        ],
    }


def _run_tool_calling_loop(
    client: GroqClient,
    system_prompt: str,
    user_prompt: str,
    actor: Actor,
    settings: Settings,
) -> tuple[str, list[ToolInvocation]]:
    ctx = ToolContext(
        timetable_data_path=settings.timetable_data_path,
        tickets_db_path=settings.tickets_db_path,
    )
    messages: list[dict] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    invocations: list[ToolInvocation] = []
    executed = 0

    # Bounds the number of Groq round-trips, not just the number of tool
    # executions: this guarantees the loop terminates even if the model (or
    # a misbehaving/mocked provider) keeps returning tool_calls after
    # tool_choice="none" was requested, rather than relying on the provider
    # to honor that request. A compliant provider stops requesting tools
    # well before this is reached.
    max_iterations = settings.max_tool_calls + 2

    for _ in range(max_iterations):
        allow_tools = executed < settings.max_tool_calls
        message = client.create_completion(
            messages=messages,
            tools=TOOL_DEFINITIONS if allow_tools else None,
            tool_choice="auto" if allow_tools else "none",
        )

        if not getattr(message, "tool_calls", None):
            return (message.content or "").strip(), invocations

        messages.append(_assistant_message_dict(message))
        for tool_call in message.tool_calls:
            if executed >= settings.max_tool_calls:
                # Defensive: the provider was told tool_choice="none" but
                # returned a tool call anyway. Never execute past the bound.
                result = {
                    "success": False,
                    "error": "Tool call limit reached for this request; no further tools can be used.",
                }
            else:
                result = dispatch_tool_call(
                    tool_call.function.name, tool_call.function.arguments, actor, ctx
                )
                executed += 1

            try:
                parsed_arguments = json.loads(tool_call.function.arguments or "{}")
            except json.JSONDecodeError:
                parsed_arguments = {}
            invocations.append(
                ToolInvocation(tool=tool_call.function.name, arguments=parsed_arguments, result=result)
            )
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(result),
                }
            )

    # The model never settled on a final answer within max_iterations - this
    # should not happen against a compliant provider, but the loop must
    # still return rather than run unbounded.
    return (
        "I was unable to complete this request within the allowed number of "
        "tool calls. Please rephrase your question or try again.",
        invocations,
    )


def get_student_support_response(
    student_message: str,
    settings: Settings | None = None,
    actor: Actor | None = None,
) -> StudentSupportResult:
    """Generate a student-support reply for the given message.

    Raises LLMConfigurationError if the provider is not configured, and
    LLMRequestError if the provider call fails. Callers (the API route)
    are responsible for translating these into safe HTTP responses.
    """
    settings = settings or get_settings()
    actor = actor or DEFAULT_ACTOR

    prompt = get_prompt(settings.active_prompt_version)
    client = GroqClient(api_key=settings.groq_api_key, model=settings.groq_model)

    sources: list[Source] = []
    tool_calls: list[ToolInvocation] = []

    if prompt.version.startswith("rag-") or prompt.version.startswith("tools-"):
        evidence_block, sources = _retrieve_evidence(student_message, settings)
        user_prompt = prompt.build_user_prompt(
            build_rag_user_message(question=student_message, evidence_block=evidence_block)
        )
    else:
        user_prompt = prompt.build_user_prompt(student_message)

    if prompt.version.startswith("tools-"):
        reply, tool_calls = _run_tool_calling_loop(
            client, prompt.system_prompt, user_prompt, actor, settings
        )
    else:
        reply = client.generate(system_prompt=prompt.system_prompt, user_prompt=user_prompt)

    return StudentSupportResult(
        response=reply,
        prompt_version=prompt.version,
        model=settings.groq_model,
        sources=sources,
        tool_calls=tool_calls,
    )
