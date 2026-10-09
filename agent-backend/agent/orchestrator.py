"""Week 5 bounded agent: Sense -> Context -> Plan/Decide -> Act/Tool -> Observe -> Stop/Re-plan.

Builds on, rather than replaces, the Week 3 retrieval pipeline and the
Week 4 tools: evidence comes from the same retriever, and every tool
request goes through the same `tools.registry.dispatch_tool_call` choke
point (allow-list, schema validation, authorization, safe execution).

What this adds over the Week 4 loop in llm/service.py is an explicit,
inspectable run: a contract (agent/contract.py) bounds it, a per-run
state (agent/state.py) records every decision as a step, and every run
ends in exactly one terminal status from the contract - never left
"running".

Week 6 adds bounded per-session memory: `run_agent` accepts an optional
`prior_turn` dict (the previous turn in the same session) and prepends a
short summary to the user prompt so the model can resolve references like
"that ticket" or "it". Memory only supplies context; it does not trigger
tool calls, alter limits, or change any stop condition.
"""

import json
import logging

from agent.contract import AgentTaskContract, build_contract
from agent.state import AgentState, AgentStep
from auth import Actor
from config import Settings, get_settings
from llm.client import GroqClient, LLMRequestError
from llm.prompts import build_rag_user_message, get_prompt
from llm.service import _assistant_message_dict, _retrieve_evidence
from tools.registry import TOOL_DEFINITIONS, ToolContext, dispatch_tool_call

logger = logging.getLogger(__name__)

AGENT_PROMPT_VERSION = "agent-v1.0"

DEFAULT_ACTOR = Actor(role="student", user_id="anonymous")

SAFE_LIMIT_RESPONSE = (
    "I wasn't able to finish this request within my allowed number of steps. "
    "Please rephrase your question, or contact student support staff directly."
)
SAFE_LLM_ERROR_RESPONSE = (
    "The assistant is temporarily unable to reach its language model. "
    "Please try again shortly."
)


def _parse_arguments(raw: str | None) -> dict:
    try:
        parsed = json.loads(raw or "{}")
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _observe(tool_name: str, result: dict) -> str:
    """Observe: turn a validated tool result into a one-line observation."""
    if not result.get("success"):
        return f"Tool failed: {result.get('error')} - re-planning with this information."
    if tool_name == "check_timetable":
        count = len(result.get("sessions") or [])
        return f"Found {count} timetable session(s) for {result.get('course_code')}."
    if tool_name == "create_support_ticket":
        return (
            f"Draft ticket {result.get('ticket_id')} created with status "
            f"{result.get('status')}; it needs staff approval before anything happens."
        )
    return "Tool succeeded."


def _plan_summary(state: AgentState, contract: AgentTaskContract) -> str:
    return (
        f"{len(state.sources)} evidence source(s) retrieved; approved tools: "
        f"{', '.join(sorted(contract.approved_tools))}; budget: "
        f"{contract.max_iterations} iteration(s), {contract.max_tool_calls} tool call(s)."
    )


def _prefix_prior_context(user_message: str, prior_turn: dict) -> str:
    """Week 6: prepend a bounded summary of the previous turn in this session.

    Memory only supplies context for the model's Plan/Decide phase. It does
    not trigger tool calls and does not alter the agent's limits or stop
    conditions.
    """
    ticket_ids = prior_turn.get("last_drafted_ticket_ids") or []
    tickets_str = ", ".join(ticket_ids) if ticket_ids else "none"
    return (
        "## Prior context (same session, earlier turn)\n"
        f"The student previously asked: {prior_turn.get('last_message', '')!r}\n"
        f"You responded: {prior_turn.get('last_response', '')!r}\n"
        f"You drafted ticket(s): {tickets_str}\n"
        f"The previous run ended with status: {prior_turn.get('last_status', '')!r}\n\n"
        "If the student's new message refers to the earlier turn (for example "
        "\"that ticket\", \"it\", or \"the thing I asked about\"), use this context. "
        "Do not re-draft the same ticket unless the student explicitly asks for "
        "a new one.\n\n"
        "## Current turn\n"
        + user_message
    )


def run_agent(
    student_message: str,
    settings: Settings | None = None,
    actor: Actor | None = None,
    prior_turn: dict | None = None,
) -> AgentState:
    """Run one bounded agent episode. Raises LLMConfigurationError if Groq isn't configured;
    every other failure ends the run with a terminal status instead of raising."""
    settings = settings or get_settings()
    actor = actor or DEFAULT_ACTOR
    contract = build_contract(settings)
    prompt = get_prompt(AGENT_PROMPT_VERSION)
    client = GroqClient(api_key=settings.groq_api_key, model=settings.groq_model)
    tool_ctx = ToolContext(
        timetable_data_path=settings.timetable_data_path,
        tickets_db_path=settings.tickets_db_path,
    )

    # Sense: the request is already validated by the API schema; record it.
    state = AgentState(message=student_message)

    # Context: same retrieved evidence as Week 3/4.
    evidence_block, state.sources = _retrieve_evidence(student_message, settings)
    state.plan = _plan_summary(state, contract)

    # Build the user prompt. Week 6: if a prior turn exists for this
    # session, prepend a bounded summary so the model can resolve
    # references like "that ticket".
    user_message = prompt.build_user_prompt(
        build_rag_user_message(question=student_message, evidence_block=evidence_block)
    )
    if prior_turn:
        user_message = _prefix_prior_context(user_message, prior_turn)

    messages: list[dict] = [
        {"role": "system", "content": prompt.system_prompt},
        {"role": "user", "content": user_message},
    ]

    while state.iteration_count < contract.max_iterations:
        state.iteration_count += 1
        iteration = state.iteration_count
        tools_allowed = state.tool_call_count < contract.max_tool_calls

        # Plan/Decide: the model chooses a final answer or an approved tool.
        try:
            message = client.create_completion(
                messages=messages,
                tools=TOOL_DEFINITIONS if tools_allowed else None,
                tool_choice="auto" if tools_allowed else "none",
            )
        except LLMRequestError as exc:
            logger.warning("Agent run %s: LLM error: %s", state.run_id, exc)
            state.steps.append(AgentStep(iteration=iteration, decision="error", error=str(exc)))
            return state.stop("llm_error", SAFE_LLM_ERROR_RESPONSE)

        tool_calls = getattr(message, "tool_calls", None) or []
        if not tool_calls:
            answer = (message.content or "").strip()
            state.steps.append(
                AgentStep(iteration=iteration, decision="final_answer", observation="Model produced a final answer.")
            )
            if state.drafted_ticket_ids:
                # Stop: the agent's authority ends at a draft; a human takes over.
                state.steps.append(
                    AgentStep(
                        iteration=iteration,
                        decision="stop",
                        observation=(
                            f"Handing over to staff: {', '.join(state.drafted_ticket_ids)} "
                            "awaiting human approval."
                        ),
                    )
                )
                return state.stop("human_approval_required", answer)
            return state.stop("completed", answer)

        messages.append(_assistant_message_dict(message))
        for tool_call in tool_calls:
            tool_name = tool_call.function.name
            arguments = _parse_arguments(tool_call.function.arguments)

            if not contract.is_approved_tool(tool_name):
                state.steps.append(
                    AgentStep(
                        iteration=iteration,
                        decision="stop",
                        tool_name=tool_name,
                        tool_arguments=arguments,
                        error=f"Tool {tool_name!r} is not approved for this agent; it was not executed.",
                    )
                )
                return state.stop(
                    "tool_not_approved",
                    "I can't do that - it's outside what this assistant is allowed to do. "
                    "A member of staff can help you with it.",
                )

            if state.tool_call_count >= contract.max_tool_calls:
                state.steps.append(
                    AgentStep(
                        iteration=iteration,
                        decision="stop",
                        tool_name=tool_name,
                        tool_arguments=arguments,
                        error="Tool call limit reached; no further tools were executed.",
                    )
                )
                return state.stop("max_tool_calls_reached", SAFE_LIMIT_RESPONSE)

            # Act/Tool: the application, not the model, executes the tool.
            result = dispatch_tool_call(tool_name, tool_call.function.arguments, actor, tool_ctx)
            state.tool_call_count += 1
            if tool_name == "create_support_ticket" and result.get("success"):
                state.drafted_ticket_ids.append(result["ticket_id"])

            # Observe: record the outcome, feed it back, and re-plan.
            state.steps.append(
                AgentStep(
                    iteration=iteration,
                    decision="tool_call",
                    tool_name=tool_name,
                    tool_arguments=arguments,
                    tool_result=result,
                    observation=_observe(tool_name, result),
                )
            )
            messages.append(
                {"role": "tool", "tool_call_id": tool_call.id, "content": json.dumps(result)}
            )

    state.steps.append(
        AgentStep(
            iteration=state.iteration_count,
            decision="stop",
            error=f"Maximum of {contract.max_iterations} iteration(s) reached without a final answer.",
        )
    )
    return state.stop("max_iterations_reached", SAFE_LIMIT_RESPONSE)