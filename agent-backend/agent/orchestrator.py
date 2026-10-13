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

Observability: alongside the state, a RunTrace (observability/trace.py)
records the model parameters and prompt fingerprint, every retrieval
candidate with its relevance score, each LLM call (latency, tokens,
finish reason, provider request id), each tool call (arguments,
response, latency), per-iteration latency, and an error code for every
failure. Each of those is also logged as a structured event, and the
finished trace is exported to `settings.trace_export_dir`. The trace is
closed even when the run raises (status "aborted"), so no run is ever
unaccounted for.
"""

import json
import logging
from time import perf_counter

from agent.case_history import save_case_summary
from agent.contract import AgentTaskContract, build_contract
from agent.state import AgentStage, AgentState, AgentStep
from agent.state_store import save_session_state
from auth import Actor
from config import Settings, get_settings
from llm.client import GroqClient, LLMConfigurationError, LLMRequestError
from llm.prompts import PromptTemplate, build_rag_user_message, get_prompt
from llm.service import _assistant_message_dict
from observability import error_codes
from observability.export import write_trace
from observability.trace import ABORTED, RunTrace, elapsed_ms, sha256
from rag.context_builder import build_evidence_block, build_sources
from rag.retriever import RetrievedChunk, retrieve_with_rejected
from rag.vector_store import get_vector_store
from tools.registry import TOOL_DEFINITIONS, ToolContext, dispatch_tool_call

logger = logging.getLogger(__name__)

AGENT_PROMPT_VERSION = "agent-v1.0"

DEFAULT_ACTOR = Actor(role="student", user_id="anonymous")

TOOL_NAMES = [definition["function"]["name"] for definition in TOOL_DEFINITIONS]
TOOL_DEFINITIONS_SHA256 = sha256(json.dumps(TOOL_DEFINITIONS, sort_keys=True))

SAFE_LIMIT_RESPONSE = (
    "I wasn't able to finish this request within my allowed number of steps. "
    "Please rephrase your question, or contact student support staff directly."
)
SAFE_LLM_ERROR_RESPONSE = (
    "The assistant is temporarily unable to reach its language model. "
    "Please try again shortly."
)


def _parse_arguments(raw: str | None) -> tuple[dict, bool]:
    """Return (arguments, parsed_ok); arguments is {} when `raw` isn't a JSON object."""
    try:
        parsed = json.loads(raw or "{}")
    except json.JSONDecodeError:
        return {}, False
    return (parsed, True) if isinstance(parsed, dict) else ({}, False)


def _retrieve(
    student_message: str, settings: Settings
) -> tuple[list[RetrievedChunk], list[RetrievedChunk]]:
    """Context: same retriever as Week 3/4, keeping below-threshold candidates for the trace."""
    vector_store = get_vector_store(
        persist_directory=settings.chroma_persist_directory,
        collection_name=settings.rag_collection_name,
    )
    return retrieve_with_rejected(
        vector_store=vector_store,
        question=student_message,
        top_k=settings.rag_top_k,
        min_score=settings.rag_min_score,
    )


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
    error_code: str | None = None,
) -> AgentState:
    state.stop(status, response, error_code=error_code)
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


def _trace_config(settings: Settings, contract: AgentTaskContract, prompt: PromptTemplate) -> dict:
    return {
        "model": {
            "provider": "groq",
            "name": settings.groq_model,
            "temperature": settings.llm_temperature,
            "max_tokens": settings.llm_max_tokens,
            "timeout_seconds": settings.llm_timeout_seconds,
            "max_retries": settings.llm_max_retries,
        },
        "prompt": {
            "version": prompt.version,
            "system_prompt_sha256": sha256(prompt.system_prompt),
            "system_prompt_chars": len(prompt.system_prompt),
        },
        "tools": {"defined": TOOL_NAMES, "definitions_sha256": TOOL_DEFINITIONS_SHA256},
        "contract": {
            "max_iterations": contract.max_iterations,
            "max_tool_calls": contract.max_tool_calls,
            "approved_tools": sorted(contract.approved_tools),
        },
        "rag": {
            "collection": settings.rag_collection_name,
            "embedding_model": settings.embedding_model,
            "top_k": settings.rag_top_k,
            "min_score": settings.rag_min_score,
        },
        "app": {"name": settings.app_name, "env": settings.app_env},
    }


def run_agent(
    student_message: str,
    settings: Settings | None = None,
    actor: Actor | None = None,
    prior_turn: dict | None = None,
) -> AgentState:
    """Run one bounded agent episode. Raises LLMConfigurationError if Groq isn't configured;
    every other failure ends the run with a terminal status instead of raising.

    Whatever happens, the run's trace is closed, logged, and exported
    before this returns or raises; it is also attached as `state.trace`.
    """
    settings = settings or get_settings()
    actor = actor or DEFAULT_ACTOR

    # Sense: the request is already validated by the API schema; record it.
    state = AgentState(message=student_message, student_id=actor.user_id)
    trace = RunTrace(
        state.run_id,
        request={"message": student_message, "actor_role": actor.role, "actor_id": actor.user_id},
    )

    try:
        _run(state, trace, settings, actor, prior_turn)
    except Exception as exc:
        if isinstance(exc, LLMConfigurationError):
            code = error_codes.LLM_NOT_CONFIGURED
        elif trace.stage == "retrieval":
            code = error_codes.RETRIEVAL_ERROR
        else:
            code = error_codes.AGENT_UNHANDLED_EXCEPTION
        trace.record_error(code, trace.stage, f"{type(exc).__name__}: {exc}")
        state.error_code = code
        _close_trace(trace, state, ABORTED, settings)
        raise

    _close_trace(trace, state, state.status, settings)
    return state


def _close_trace(trace: RunTrace, state: AgentState, status: str, settings: Settings) -> None:
    state.trace = trace.finish(
        status,
        response=state.response,
        error_code=state.error_code,
        iteration_count=state.iteration_count,
        tool_call_count=state.tool_call_count,
        drafted_ticket_ids=list(state.drafted_ticket_ids),
    )
    if settings.trace_export_dir:
        try:
            write_trace(state.trace, settings.trace_export_dir)
        except OSError:
            # Losing the file must never fail the student's request; the
            # structured log lines already carry the same events.
            logger.exception("Could not export trace for run %s", state.run_id)


def _run(
    state: AgentState, trace: RunTrace, settings: Settings, actor: Actor, prior_turn: dict | None
) -> None:
    contract = build_contract(settings)
    prompt = get_prompt(AGENT_PROMPT_VERSION)
    trace.record_config(_trace_config(settings, contract, prompt))
    client = GroqClient(
        api_key=settings.groq_api_key,
        model=settings.groq_model,
        timeout_seconds=settings.llm_timeout_seconds,
        temperature=settings.llm_temperature,
        max_tokens=settings.llm_max_tokens,
        max_retries=settings.llm_max_retries,
    )
    tool_ctx = ToolContext(
        timetable_data_path=settings.timetable_data_path,
        tickets_db_path=settings.tickets_db_path,
    )
    state.transition_stage(AgentStage.SENSE)
    _persist(state, settings)

    # Context: same retrieved evidence as Week 3/4.
    trace.stage = "retrieval"
    started = perf_counter()
    kept, rejected = _retrieve(state.message, settings)
    trace.record_retrieval(
        query=state.message,
        top_k=settings.rag_top_k,
        min_score=settings.rag_min_score,
        latency_ms=elapsed_ms(started),
        kept=kept,
        rejected=rejected,
    )
    state.sources = build_sources(kept)
    state.plan = _plan_summary(state, contract)

    # Week 6: if a prior turn exists for this session, prepend a bounded
    # summary so the model can resolve references like "that ticket".
    user_message = prompt.build_user_prompt(
        build_rag_user_message(question=state.message, evidence_block=build_evidence_block(kept))
    )
    if prior_turn:
        user_message = _prefix_prior_context(user_message, prior_turn)
    state.transition_stage(AgentStage.CONTEXT)
    _persist(state, settings)

    messages: list[dict] = [
        {"role": "system", "content": prompt.system_prompt},
        {"role": "user", "content": user_message},
    ]

    while state.iteration_count < contract.max_iterations:
        state.iteration_count += 1
        iteration = state.iteration_count
        tools_allowed = state.tool_call_count < contract.max_tool_calls
        tool_choice = "auto" if tools_allowed else "none"
        trace.stage = f"iteration {iteration}"
        record = trace.start_iteration(
            iteration, tools_offered=TOOL_NAMES if tools_allowed else [], tool_choice=tool_choice
        )
        try:
            # Plan/Decide: the model chooses a final answer or an approved tool.
            state.transition_stage(AgentStage.PLAN)
            _persist(state, settings)
            started = perf_counter()
            try:
                message = client.create_completion(
                    messages=messages,
                    tools=TOOL_DEFINITIONS if tools_allowed else None,
                    tool_choice=tool_choice,
                )
            except LLMRequestError as exc:
                llm_ms = elapsed_ms(started)
                logger.warning("Agent run %s: LLM error: %s", state.run_id, exc)
                trace.record_llm_call(
                    record,
                    latency_ms=llm_ms,
                    message_count=len(messages),
                    call_info=client.last_call,
                    error_code=exc.code,
                    error=str(exc),
                )
                state.steps.append(
                    AgentStep(
                        iteration=iteration,
                        decision="error",
                        error=str(exc),
                        error_code=exc.code,
                        latency_ms=llm_ms,
                    )
                )
                _finalize_run(
                    state, "llm_error", SAFE_LLM_ERROR_RESPONSE, actor, settings, error_code=exc.code
                )
                return
            llm_ms = elapsed_ms(started)

            tool_calls = getattr(message, "tool_calls", None) or []
            trace.record_llm_call(
                record,
                latency_ms=llm_ms,
                message_count=len(messages),
                call_info=client.last_call,
                content=message.content,
                requested_tools=[tc.function.name for tc in tool_calls],
            )

            if not tool_calls:
                answer = (message.content or "").strip()
                state.steps.append(
                    AgentStep(
                        iteration=iteration,
                        decision="final_answer",
                        observation="Model produced a final answer.",
                        latency_ms=llm_ms,
                    )
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
                    _finalize_run(state, "human_approval_required", answer, actor, settings)
                    return
                _finalize_run(state, "completed", answer, actor, settings)
                return

            messages.append(_assistant_message_dict(message))
            for tool_call in tool_calls:
                tool_name = tool_call.function.name
                raw_arguments = tool_call.function.arguments
                arguments, parsed_ok = _parse_arguments(raw_arguments)
                trace_call = {
                    "tool_call_id": tool_call.id,
                    "tool_name": tool_name,
                    "arguments": arguments,
                    "arguments_raw": None if parsed_ok else raw_arguments,
                }

                if not contract.is_approved_tool(tool_name):
                    error = f"Tool {tool_name!r} is not approved for this agent; it was not executed."
                    code = error_codes.AGENT_TOOL_NOT_APPROVED
                    trace.record_tool_call(
                        record, **trace_call, approved=False, executed=False, error_code=code
                    )
                    trace.record_error(code, "contract", error, iteration=iteration)
                    state.steps.append(
                        AgentStep(
                            iteration=iteration,
                            decision="stop",
                            tool_name=tool_name,
                            tool_arguments=arguments,
                            error=error,
                            error_code=code,
                        )
                    )
                    _finalize_run(
                        state,
                        "tool_not_approved",
                        "I can't do that - it's outside what this assistant is allowed to do. "
                        "A member of staff can help you with it.",
                        actor,
                        settings,
                        error_code=code,
                    )
                    return

                if state.tool_call_count >= contract.max_tool_calls:
                    error = "Tool call limit reached; no further tools were executed."
                    code = error_codes.AGENT_TOOL_BUDGET_EXHAUSTED
                    trace.record_tool_call(
                        record, **trace_call, approved=True, executed=False, error_code=code
                    )
                    trace.record_error(code, "contract", error, iteration=iteration)
                    state.steps.append(
                        AgentStep(
                            iteration=iteration,
                            decision="stop",
                            tool_name=tool_name,
                            tool_arguments=arguments,
                            error=error,
                            error_code=code,
                        )
                    )
                    _finalize_run(
                        state, "max_tool_calls_reached", SAFE_LIMIT_RESPONSE, actor, settings, error_code=code
                    )
                    return

                # Act/Tool: the application, not the model, executes the tool.
                if state.stage == AgentStage.REPLAN:
                    # A second tool call in the same model reply: the stage model
                    # only allows REPLAN -> PLAN, and that reply is the plan.
                    state.transition_stage(AgentStage.PLAN)
                state.transition_stage(AgentStage.ACT)
                started = perf_counter()
                result = dispatch_tool_call(tool_name, raw_arguments, actor, tool_ctx)
                tool_ms = elapsed_ms(started)
                state.tool_call_count += 1
                if tool_name == "create_support_ticket" and result.get("success"):
                    state.drafted_ticket_ids.append(result["ticket_id"])

                # Observe: record the outcome, feed it back, and re-plan.
                observation = _observe(tool_name, result)
                code = None if result.get("success") else (
                    result.get("error_code") or error_codes.TOOL_NO_RESULT
                )
                trace.record_tool_call(
                    record,
                    **trace_call,
                    approved=True,
                    executed=True,
                    latency_ms=tool_ms,
                    response=result,
                    error_code=code,
                    observation=observation,
                )
                if code:
                    trace.record_error(code, "tool", result.get("error") or "", iteration=iteration)
                state.steps.append(
                    AgentStep(
                        iteration=iteration,
                        decision="tool_call",
                        tool_name=tool_name,
                        tool_arguments=arguments,
                        tool_result=result,
                        observation=observation,
                        error_code=code,
                        latency_ms=tool_ms,
                    )
                )
                state.transition_stage(AgentStage.OBSERVE)
                _persist(state, settings)
                state.transition_stage(AgentStage.REPLAN)
                _persist(state, settings)
                messages.append(
                    {"role": "tool", "tool_call_id": tool_call.id, "content": json.dumps(result)}
                )
        finally:
            trace.end_iteration(record, [s.decision for s in state.steps if s.iteration == iteration])

    error = f"Maximum of {contract.max_iterations} iteration(s) reached without a final answer."
    code = error_codes.AGENT_ITERATION_BUDGET_EXHAUSTED
    trace.record_error(code, "contract", error, iteration=state.iteration_count)
    state.steps.append(
        AgentStep(iteration=state.iteration_count, decision="stop", error=error, error_code=code)
    )
    _finalize_run(state, "max_iterations_reached", SAFE_LIMIT_RESPONSE, actor, settings, error_code=code)
