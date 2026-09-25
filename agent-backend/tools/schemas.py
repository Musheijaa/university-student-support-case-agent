"""Pydantic schemas for tool inputs, outputs, authorization, and error handling.

Defines explicit contracts for:
1. CreateSupportTicketTool
2. GetCaseStatusTool
3. CheckTimetableTool
"""

from enum import Enum
from pydantic import BaseModel, Field, field_validator


class TicketCategory(str, Enum):
    ACADEMIC_REGISTRAR = "Academic Registrar"
    FINANCIAL_AID = "Financial Aid & Bursary"
    HALL_ALLOCATION = "Hall Allocation & Accommodation"
    LIBRARY_SERVICES = "Library Services"
    IT_SUPPORT = "DICTS / IT Support"
    GENERAL = "General Student Affairs"


class TicketPriority(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    URGENT = "URGENT"


# ---------------------------------------------------------------------------
# Tool 1: CreateSupportTicketTool Schemas
# ---------------------------------------------------------------------------
class CreateTicketInput(BaseModel):
    """Input schema for creating a student support ticket."""

    student_id: str = Field(
        ...,
        description="Student registration number or student ID (e.g., 2100701234 or STU-1001).",
        min_length=3,
        max_length=20,
    )
    category: TicketCategory = Field(
        ...,
        description="University department category for routing the support ticket.",
    )
    subject: str = Field(
        ...,
        description="Brief summary title of the student's issue.",
        min_length=5,
        max_length=100,
    )
    description: str = Field(
        ...,
        description="Detailed explanation of the student case or query.",
        min_length=10,
        max_length=1000,
    )
    priority: TicketPriority = Field(
        TicketPriority.MEDIUM,
        description="Priority level of the support ticket.",
    )
    auth_token: str = Field(
        ...,
        description="Authorization token representing the student or agent credentials.",
    )

    @field_validator("student_id", "subject", "description", "auth_token")
    @classmethod
    def field_must_not_be_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Field must not be empty or whitespace-only")
        return stripped


class CreateTicketOutput(BaseModel):
    """Output schema for ticket creation result."""

    success: bool = Field(
        ..., description="True if ticket creation succeeded, False otherwise."
    )
    ticket_id: str | None = Field(
        None, description="Unique ticket identifier generated upon creation."
    )
    status: str = Field(
        ...,
        description="Result status code (e.g., CREATED, UNAUTHORIZED, INVALID_INPUT, SERVICE_ERROR).",
    )
    assigned_department: str | None = Field(
        None, description="Makerere University department assigned to resolve the case."
    )
    created_at: str | None = Field(
        None, description="ISO 8601 timestamp when ticket was created."
    )
    estimated_response_days: int | None = Field(
        None, description="Estimated SLA response time in business days."
    )
    message: str = Field(
        ..., description="Human-readable explanation of outcome or failure."
    )
    error: str | None = Field(
        None, description="Explicit error code or detail string if operation failed."
    )


# ---------------------------------------------------------------------------
# Tool 2: GetCaseStatusTool Schemas
# ---------------------------------------------------------------------------
class GetCaseStatusInput(BaseModel):
    """Input schema for checking student support case status."""

    case_id: str = Field(
        ...,
        description="Unique case identifier (e.g., TICK-2026-1042).",
        min_length=5,
        max_length=30,
    )
    student_id: str = Field(
        ...,
        description="Student ID requesting the status view.",
        min_length=3,
        max_length=20,
    )
    auth_token: str = Field(
        ...,
        description="Authorization token for identity verification.",
    )

    @field_validator("case_id", "student_id", "auth_token")
    @classmethod
    def field_must_not_be_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Field must not be empty or whitespace-only")
        return stripped


class CaseNote(BaseModel):
    timestamp: str = Field(..., description="ISO 8601 timestamp of update.")
    author: str = Field(..., description="Staff member or system role writing note.")
    note: str = Field(..., description="Public case progress note.")


class GetCaseStatusOutput(BaseModel):
    """Output schema for case status lookup result."""

    success: bool = Field(
        ..., description="True if status lookup succeeded, False otherwise."
    )
    case_id: str | None = Field(None, description="Queried case ID.")
    student_id: str | None = Field(
        None, description="Student ID associated with case."
    )
    category: str | None = Field(None, description="Assigned department category.")
    subject: str | None = Field(None, description="Subject title of case.")
    status: str = Field(
        ...,
        description="Current case status (e.g., UNDER_REVIEW, RESOLVED, PENDING_INFO, NOT_FOUND, UNAUTHORIZED).",
    )
    assigned_officer: str | None = Field(
        None, description="Staff member currently handling case."
    )
    created_at: str | None = Field(
        None, description="ISO 8601 timestamp when case was opened."
    )
    last_updated: str | None = Field(
        None, description="ISO 8601 timestamp of last status update."
    )
    notes: list[CaseNote] = Field(
        default_factory=list, description="Public audit/progress notes on case."
    )
    message: str = Field(
        ..., description="Human-readable outcome or failure explanation."
    )
    error: str | None = Field(
        None, description="Error code or description if query failed."
    )


# ---------------------------------------------------------------------------
# Tool 3: CheckTimetableTool Schemas
# ---------------------------------------------------------------------------
class CheckTimetableInput(BaseModel):
    """Input schema for checking course/exam timetable information."""

    student_id: str = Field(
        ...,
        description="Student registration number or student ID.",
        min_length=3,
        max_length=20,
    )
    course_code: str | None = Field(
        None,
        description="Optional course code filter (e.g., BSE4104, BIT2101).",
    )
    semester: str = Field(
        "2026/2027-SEM1",
        description="Academic semester for timetable query.",
    )
    auth_token: str = Field(
        ...,
        description="Authorization token for verification.",
    )

    @field_validator("student_id", "auth_token")
    @classmethod
    def field_must_not_be_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Field must not be empty or whitespace-only")
        return stripped


class TimetableEntry(BaseModel):
    course_code: str = Field(..., description="Course code (e.g., BSE4104).")
    course_title: str = Field(..., description="Full course title.")
    entry_type: str = Field(
        ..., description="Schedule entry type: LECTURE, LAB, TUTORIAL, or EXAM."
    )
    day: str = Field(..., description="Day of week (Monday through Saturday).")
    start_time: str = Field(..., description="Start time (e.g., 09:00 AM).")
    end_time: str = Field(..., description="End time (e.g., 11:00 AM).")
    venue: str = Field(..., description="Building room or lecture hall venue.")
    instructor: str | None = Field(
        None, description="Course lecturer or exam invigilator."
    )


class CheckTimetableOutput(BaseModel):
    """Output schema for timetable query result."""

    success: bool = Field(
        ..., description="True if timetable lookup succeeded, False otherwise."
    )
    student_id: str | None = Field(None, description="Student ID.")
    semester: str | None = Field(None, description="Queried academic semester.")
    total_found: int = Field(0, description="Total matching schedule entries.")
    entries: list[TimetableEntry] = Field(
        default_factory=list, description="Matching timetable entries."
    )
    message: str = Field(
        ..., description="Human-readable outcome or status message."
    )
    error: str | None = Field(
        None, description="Error code or details if operation failed."
    )


# ---------------------------------------------------------------------------
# Tool 4 (High-Impact): SubmitGradeAppealTool Schemas
# ---------------------------------------------------------------------------
class AppealType(str, Enum):
    REMARKING = "REMARKING"
    CALCULATION_CHECK = "CALCULATION_CHECK"
    SPECIAL_CIRCUMSTANCES = "SPECIAL_CIRCUMSTANCES"


class SubmitGradeAppealInput(BaseModel):
    """Input schema for formal grade appeal (requires human approval)."""

    student_id: str = Field(
        ...,
        description="Student registration number or student ID.",
        min_length=3,
        max_length=20,
    )
    course_code: str = Field(
        ...,
        description="Course code being appealed (e.g., BSE4104).",
        min_length=4,
        max_length=12,
    )
    semester: str = Field(
        "2026/2027-SEM1",
        description="Academic semester of examination.",
    )
    appeal_type: AppealType = Field(
        AppealType.REMARKING,
        description="Type of appeal: REMARKING, CALCULATION_CHECK, or SPECIAL_CIRCUMSTANCES.",
    )
    claimed_score: float | None = Field(
        None,
        description="Estimated or expected score if calculation discrepancy is claimed.",
        ge=0,
        le=100,
    )
    justification: str = Field(
        ...,
        description="Detailed grounds for academic appeal.",
        min_length=20,
        max_length=1000,
    )
    confirm_fee_obligation: bool = Field(
        ...,
        description="Explicit student confirmation of non-refundable 50,000 UGX appeal deposit fee.",
    )
    auth_token: str = Field(
        ...,
        description="Authorization token representing student credentials.",
    )

    @field_validator("student_id", "course_code", "justification", "auth_token")
    @classmethod
    def field_must_not_be_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Field must not be empty or whitespace-only")
        return stripped

    @field_validator("confirm_fee_obligation")
    @classmethod
    def fee_must_be_acknowledged(cls, value: bool) -> bool:
        if not value:
            raise ValueError("Student must acknowledge the 50,000 UGX appeal fee obligation.")
        return value


class SubmitGradeAppealOutput(BaseModel):
    """Output schema for formal grade appeal submission."""

    success: bool = Field(
        ..., description="True if grade appeal was lodged, False otherwise."
    )
    appeal_id: str | None = Field(
        None, description="Unique appeal identifier (e.g., APPL-2026-4012)."
    )
    status: str = Field(
        ...,
        description="Outcome status (e.g., LODGED, PENDING_APPROVAL, UNAUTHORIZED, INVALID_INPUT, REJECTED).",
    )
    course_code: str | None = Field(None, description="Course appealed.")
    appeal_fee_ugx: int | None = Field(
        None, description="Required fee deposit in UGX."
    )
    assigned_board: str | None = Field(
        None, description="Committee reviewing appeal (e.g. Senate Examinations Committee)."
    )
    created_at: str | None = Field(
        None, description="ISO 8601 timestamp when appeal was lodged."
    )
    message: str = Field(..., description="Human-readable result summary.")
    error: str | None = Field(None, description="Error code or detail if failed.")


# ---------------------------------------------------------------------------
# Human-in-the-Loop (HITL) Approval Schemas
# ---------------------------------------------------------------------------
class ApprovalStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


class ApprovalDecision(str, Enum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"


class ApprovalRequest(BaseModel):
    """State model for an action paused waiting for human approval."""

    approval_id: str = Field(..., description="Unique approval request ID.")
    tool_name: str = Field(..., description="Target tool to fire upon confirmation.")
    action_summary: str = Field(..., description="Plain-language explanation of proposed action.")
    parameters: dict = Field(..., description="Proposed parameters for tool execution.")
    requester: str = Field(..., description="Student or agent requesting execution.")
    risk_level: str = Field("HIGH", description="Risk level (LOW, MEDIUM, HIGH, CRITICAL).")
    status: ApprovalStatus = Field(ApprovalStatus.PENDING, description="Current approval status.")
    created_at: str = Field(..., description="ISO 8601 timestamp when approval was requested.")
    decided_at: str | None = Field(None, description="ISO 8601 timestamp of human decision.")
    reviewer: str | None = Field(None, description="Human reviewer or student approver.")
    review_notes: str | None = Field(None, description="Notes from human reviewer.")
    execution_result: dict | None = Field(
        None, description="Output from tool execution if approval was confirmed."
    )


class CreateApprovalInput(BaseModel):
    """Input payload to request human approval and pause tool execution."""

    tool_name: str = Field(..., description="Target tool to fire once confirmed.")
    parameters: dict = Field(..., description="Proposed tool parameters.")
    action_summary: str = Field(..., description="Human-readable summary of the action.")
    requester: str = Field(..., description="Student ID or agent identifier.")
    risk_level: str = Field("HIGH", description="Risk level categorization.")


class ApprovalDecisionInput(BaseModel):
    """Human decision payload to confirm or reject a paused action."""

    decision: ApprovalDecision = Field(..., description="APPROVE or REJECT.")
    reviewer: str = Field(..., description="Name or role of person making decision.")
    notes: str = Field(..., description="Decision justification or conditions.")


class ApprovalExecutionResult(BaseModel):
    """Result returned after human decision is processed."""

    approval_id: str
    status: ApprovalStatus
    tool_fired: bool = Field(..., description="True if target tool was triggered.")
    tool_output: dict | None = Field(None, description="Result payload if tool was fired.")
    message: str = Field(..., description="Status summary of human review outcome.")

