"""FastAPI application entry point.

Exposes:
  GET  /health                    - liveness check, independent of the LLM provider
  POST /api/v1/student-support    - RAG-grounded student-support interaction (Week 3);
                                     retrieves evidence from the ingested corpus before
                                     calling Groq, and returns the sources used
"""

import logging

from fastapi import FastAPI, HTTPException, status

from config import get_settings
from llm.service import (
    LLMConfigurationError,
    LLMRequestError,
    get_student_support_response,
)
from schemas import (
    HealthResponse,
    SourceResponse,
    StudentSupportRequest,
    StudentSupportResponse,
    ToolCatalogueItem,
    ToolExecutionRequest,
)
from tools import (
    ApprovalDecisionInput,
    ApprovalExecutionResult,
    ApprovalRequest,
    CreateApprovalInput,
    get_approval_manager,
    get_tool_registry,
)

logging.basicConfig(level=get_settings().log_level)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="University Student-Support Case Agent API",
    description=(
        "Week 4: Retrieval-augmented student support with explicit, safe software tools "
        "(support ticket creation, case status lookup, timetable verification, and formal "
        "grade appeals) featuring Human-in-the-Loop (HITL) approval controls for high-impact actions."
    ),
    version="0.4.0",
)


@app.get("/health", response_model=HealthResponse, tags=["health"])
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@app.get("/api/v1/tools", response_model=list[ToolCatalogueItem], tags=["tools"])
def list_tools() -> list[ToolCatalogueItem]:
    registry = get_tool_registry()
    return [
        ToolCatalogueItem(
            name=tool.name,
            description=tool.description,
            purpose=tool.tool_purpose,
            json_schema=tool.get_json_schema(),
        )
        for tool in registry.list_tools()
    ]


@app.post("/api/v1/tools/execute", tags=["tools"])
def execute_tool(request: ToolExecutionRequest) -> dict:
    registry = get_tool_registry()
    tool = registry.get_tool(request.tool_name)
    if not tool:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tool '{request.tool_name}' not found in registry.",
        )

    # Check if tool requires human approval
    requires_approval = getattr(tool, "requires_human_approval", False)
    is_confirmed = request.parameters.pop("confirmed_by_human", False)

    if requires_approval and not is_confirmed:
        # Pause execution, create approval request, and prompt for human approval
        approval_mgr = get_approval_manager()
        student_id = request.parameters.get("student_id", "anonymous_student")
        appr_req = approval_mgr.request_approval(
            tool_name=request.tool_name,
            parameters=request.parameters,
            requester=student_id,
            action_summary=(
                f"Action '{request.tool_name}' has high impact. Paused for human confirmation."
            ),
            risk_level="HIGH",
        )
        return {
            "status": "PAUSED_PENDING_APPROVAL",
            "approval_id": appr_req.approval_id,
            "message": (
                f"High-impact action '{request.tool_name}' requires human approval before firing. "
                f"Approval request {appr_req.approval_id} created."
            ),
            "approval_details": appr_req.model_dump(),
        }

    result = tool.execute(request.parameters)
    return result.model_dump()


# ---------------------------------------------------------------------------
# Human-in-the-Loop (HITL) Approval Endpoints
# ---------------------------------------------------------------------------
@app.post(
    "/api/v1/approvals/request",
    response_model=ApprovalRequest,
    tags=["human-approval"],
)
def request_human_approval(payload: CreateApprovalInput) -> ApprovalRequest:
    """Create an approval request and pause execution."""
    approval_mgr = get_approval_manager()
    try:
        return approval_mgr.request_approval(
            tool_name=payload.tool_name,
            parameters=payload.parameters,
            requester=payload.requester,
            action_summary=payload.action_summary,
            risk_level=payload.risk_level,
        )
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@app.get(
    "/api/v1/approvals/pending",
    response_model=list[ApprovalRequest],
    tags=["human-approval"],
)
def list_pending_approvals() -> list[ApprovalRequest]:
    """List all actions currently paused waiting for human approval."""
    approval_mgr = get_approval_manager()
    return approval_mgr.get_pending_approvals()


@app.get(
    "/api/v1/approvals/{approval_id}",
    response_model=ApprovalRequest,
    tags=["human-approval"],
)
def get_approval_status(approval_id: str) -> ApprovalRequest:
    """Get the state and details of an approval request."""
    approval_mgr = get_approval_manager()
    record = approval_mgr.get_approval(approval_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Approval request '{approval_id}' not found.",
        )
    return record


@app.post(
    "/api/v1/approvals/{approval_id}/decide",
    response_model=ApprovalExecutionResult,
    tags=["human-approval"],
)
def decide_approval(
    approval_id: str, payload: ApprovalDecisionInput
) -> ApprovalExecutionResult:
    """Submit human decision. If APPROVE, fires the underlying tool now."""
    approval_mgr = get_approval_manager()
    try:
        return approval_mgr.decide_approval(
            approval_id=approval_id,
            decision=payload.decision,
            reviewer=payload.reviewer,
            notes=payload.notes,
        )
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc



@app.post(
    "/api/v1/student-support",
    response_model=StudentSupportResponse,
    tags=["student-support"],
)
def student_support(payload: StudentSupportRequest) -> StudentSupportResponse:
    try:
        result = get_student_support_response(payload.message)
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
    )

