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
"""

import json
import logging

from agent.case_history import save_case_summary
from agent.contract import AgentTaskContract, build_contract
from agent.state import AgentStage, AgentState, AgentStep
from agent.state_store import save_session_state
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


def _persist(state: AgentState, settings: Settings) -> None:
    try:
        db_path = getattr(settings, "state_db_path", None)
        save_session_state(state, db_path=db_path)
    except Exception as exc:
        logger.warning("Agent run %s: Failed to persist session state: %s", state.run_id, exc)


def _finalize_run(
    state: AgentState,
    status: str,
    response: str,
    actor: Actor,
    settings: Settings,
) -> AgentState:
    state.stop(status, response)
    _persist(state, settings)

    # Task 4: Store only approved case summary fields in long-term case-history memory
    try:
        category = "General Inquiry"
        if state.drafted_ticket_ids:
            category = "Support Ticket"
        elif any(s.tool_name == "check_timetable" for s in state.steps):
            category = "Timetable Query"
        elif state.sources:
            category = "Policy Query"

        summary_text = state.message[:150]
        action_text = response[:200]
        ticket_id = state.drafted_ticket_ids[0] if state.drafted_ticket_ids else None
        student_id = actor.user_id if actor and actor.user_id else "anonymous"

        case_db_path = getattr(settings, "case_history_db_path", None)
        save_case_summary(
            {
                "case_id": state.run_id,
                "student_id": student_id,
                "category": category,
                "summary": summary_text,
                "status": state.status,
                "action_taken": action_text,
                "ticket_id": ticket_id,
            },
            db_path=case_db_path,
        )
    except Exception as exc:
        logger.warning("Agent run %s: Failed to save case summary: %s", state.run_id, exc)

    return state


def run_agent(
    student_message: str,
    settings: Settings | None = None,
    actor: Actor | None = None,
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
    state = AgentState(message=student_message, student_id=actor.user_id)
    state.transition_stage(AgentStage.SENSE)
    _persist(state, settings)

    # Context: same retrieved evidence as Week 3/4.
    evidence_block, state.sources = _retrieve_evidence(student_message, settings)
    state.plan = _plan_summary(state, contract)
    state.transition_stage(AgentStage.CONTEXT)
    _persist(state, settings)

    messages: list[dict] = [
        {"role": "system", "content": prompt.system_prompt},
        {
            "role": "user",
            "content": prompt.build_user_prompt(
                build_rag_user_message(question=student_message, evidence_block=evidence_block)
            ),
        },
    ]

    while state.iteration_count < contract.max_iterations:
        state.iteration_count += 1
        iteration = state.iteration_count
        tools_allowed = state.tool_call_count < contract.max_tool_calls

        # Plan/Decide: the model chooses a final answer or an approved tool.
        state.transition_stage(AgentStage.PLAN)
        _persist(state, settings)

        try:
            message = client.create_completion(
                messages=messages,
                tools=TOOL_DEFINITIONS if tools_allowed else None,
                tool_choice="auto" if tools_allowed else "none",
            )
        except LLMRequestError as exc:
            logger.warning("Agent run %s: LLM error: %s", state.run_id, exc)
            state.steps.append(AgentStep(iteration=iteration, decision="error", error=str(exc)))
            return _finalize_run(state, "llm_error", SAFE_LLM_ERROR_RESPONSE, actor, settings)

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
                return _finalize_run(state, "human_approval_required", answer, actor, settings)
            return _finalize_run(state, "completed", answer, actor, settings)

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
                return _finalize_run(
                    state,
                    "tool_not_approved",
                    "I can't do that - it's outside what this assistant is allowed to do. "
                    "A member of staff can help you with it.",
                    actor,
                    settings,
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
                return _finalize_run(state, "max_tool_calls_reached", SAFE_LIMIT_RESPONSE, actor, settings)

            # Act/Tool: the application, not the model, executes the tool.
            state.transition_stage(AgentStage.ACT)
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
            state.transition_stage(AgentStage.OBSERVE)
            _persist(state, settings)

            state.transition_stage(AgentStage.REPLAN)
            _persist(state, settings)

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
    return _finalize_run(state, "max_iterations_reached", SAFE_LIMIT_RESPONSE, actor, settings)
