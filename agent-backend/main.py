"""FastAPI application entry point.

Exposes:
  GET  /health                                        - liveness check, independent of the LLM provider
  POST /api/v1/student-support                        - RAG-grounded, tool-using student-support interaction
  POST /api/v1/agent/student-support                  - Week 5: bounded agent run with a full execution trace
  GET  /api/v1/support-tickets/{ticket_id}             - read a ticket's current state
  POST /api/v1/support-tickets/{ticket_id}/approve     - staff-only: PENDING_APPROVAL -> SUBMITTED
  POST /api/v1/support-tickets/{ticket_id}/reject      - staff-only: PENDING_APPROVAL -> REJECTED

Week 4 adds explicit tool calling (see tools/registry.py): the model can
request check_timetable or create_support_ticket, but only the
application executes them, and only a human calling the approve/reject
endpoints above can move a ticket out of PENDING_APPROVAL - the model
has no path to submit or approve a ticket itself.
"""

import logging
from dataclasses import asdict

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from agent.contract import build_contract
from agent.orchestrator import AGENT_PROMPT_VERSION, run_agent
from auth import Actor, get_actor
from config import get_settings
from llm.service import (
    LLMConfigurationError,
    LLMRequestError,
    get_student_support_response,
)
from schemas import (
    AgentRunResponse,
    AgentStepResponse,
    HealthResponse,
    SourceResponse,
    StudentSupportRequest,
    StudentSupportResponse,
    TicketActionResponse,
    TicketDetailResponse,
    ToolCallResponse,
)
from tools import tickets

logging.basicConfig(level=get_settings().log_level)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="University Student-Support Case Agent API",
    description=(
        "Week 4: retrieval-augmented, tool-using student-support interaction. "
        "The model can request the check_timetable and create_support_ticket "
        "tools, executed by the application after validation and "
        "authorization; ticket submission still requires a separate human "
        "approval step the model cannot bypass."
    ),
    version="0.4.0",
)

# Permissive CORS for local development only (e.g. the Vite dev server on
# another port). This is a student-project test console, not a public
# deployment - tighten this to explicit origins before deploying anywhere
# real. No credentials/cookies are used, so a wildcard origin is safe here.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse, tags=["health"])
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@app.post(
    "/api/v1/student-support",
    response_model=StudentSupportResponse,
    tags=["student-support"],
)
def student_support(
    payload: StudentSupportRequest, actor: Actor = Depends(get_actor)
) -> StudentSupportResponse:
    try:
        result = get_student_support_response(payload.message, actor=actor)
    except LLMConfigurationError as exc:
        logger.error("LLM configuration error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The student-support assistant is not configured. Please contact an administrator.",
        ) from exc
    except LLMRequestError as exc:
        logger.error("LLM request error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    return StudentSupportResponse(
        response=result.response,
        prompt_version=result.prompt_version,
        model=result.model,
        sources=[
            SourceResponse(document_id=s.document_id, document=s.document, page=s.page)
            for s in result.sources
        ],
        tool_calls=[
            ToolCallResponse(tool=t.tool, arguments=t.arguments, result=t.result)
            for t in result.tool_calls
        ],
    )


@app.post(
    "/api/v1/agent/student-support",
    response_model=AgentRunResponse,
    tags=["agent"],
)
def agent_student_support(
    payload: StudentSupportRequest, actor: Actor = Depends(get_actor)
) -> AgentRunResponse:
    settings = get_settings()
    try:
        state = run_agent(payload.message, settings=settings, actor=actor)
    except LLMConfigurationError as exc:
        logger.error("LLM configuration error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The student-support assistant is not configured. Please contact an administrator.",
        ) from exc

    contract = build_contract(settings)
    logger.info(
        "Agent run %s finished: status=%s iterations=%d tool_calls=%d",
        state.run_id, state.status, state.iteration_count, state.tool_call_count,
    )
    return AgentRunResponse(
        run_id=state.run_id,
        status=state.status,
        response=state.response,
        plan=state.plan,
        iteration_count=state.iteration_count,
        tool_call_count=state.tool_call_count,
        max_iterations=contract.max_iterations,
        max_tool_calls=contract.max_tool_calls,
        prompt_version=AGENT_PROMPT_VERSION,
        model=settings.groq_model,
        steps=[AgentStepResponse(**asdict(step)) for step in state.steps],
        sources=[
            SourceResponse(document_id=s.document_id, document=s.document, page=s.page)
            for s in state.sources
        ],
    )


@app.get(
    "/api/v1/support-tickets/{ticket_id}",
    response_model=TicketDetailResponse,
    tags=["support-tickets"],
)
def get_support_ticket(ticket_id: str) -> TicketDetailResponse:
    settings = get_settings()
    record = tickets.get_ticket(ticket_id, db_path=settings.tickets_db_path)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found.")
    return TicketDetailResponse(**record.model_dump())


@app.post(
    "/api/v1/support-tickets/{ticket_id}/approve",
    response_model=TicketActionResponse,
    tags=["support-tickets"],
)
def approve_support_ticket(
    ticket_id: str, actor: Actor = Depends(get_actor)
) -> TicketActionResponse:
    if actor.role != "staff":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only staff may approve a support ticket.",
        )
    settings = get_settings()
    result = tickets.approve_ticket(ticket_id, db_path=settings.tickets_db_path)
    return TicketActionResponse(**result)


@app.post(
    "/api/v1/support-tickets/{ticket_id}/reject",
    response_model=TicketActionResponse,
    tags=["support-tickets"],
)
def reject_support_ticket(
    ticket_id: str, actor: Actor = Depends(get_actor)
) -> TicketActionResponse:
    if actor.role != "staff":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only staff may reject a support ticket.",
        )
    settings = get_settings()
    result = tickets.reject_ticket(ticket_id, db_path=settings.tickets_db_path)
    return TicketActionResponse(**result)
