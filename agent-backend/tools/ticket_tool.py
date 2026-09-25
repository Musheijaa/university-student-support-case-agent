"""Tool 1: CreateSupportTicketTool.

Creates a student support ticket and routes it to the responsible Makerere University
department. Fulfills the Week 4 requirement for a tool performing a low-risk simulated side effect.
"""

from tools.base import BaseTool
from tools.mock_db import get_mock_db
from tools.schemas import CreateTicketInput, CreateTicketOutput


class CreateSupportTicketTool(BaseTool[CreateTicketInput, CreateTicketOutput]):
    """Tool to create and route a student support ticket."""

    name = "create_support_ticket"
    description = (
        "Creates a formal student support case ticket for issues requiring university "
        "department follow-up (e.g. missing marks, tuition clearance, hall allocation, "
        "or IT assistance). Performs a low-risk side-effect record creation."
    )
    input_schema_class = CreateTicketInput
    output_schema_class = CreateTicketOutput

    def authorize(self, input_data: CreateTicketInput) -> tuple[bool, str]:
        """Verify student or agent token authorization.

        Reject tokens that are explicitly invalid/expired or blank.
        """
        token = input_data.auth_token.strip().lower()
        if token in {"unauthorized", "expired", "invalid", "revoked", "forbidden"}:
            return False, f"Auth token '{input_data.auth_token}' is invalid or expired."
        if token.startswith("invalid-") or token.startswith("unauthorized-"):
            return False, "Provided credentials do not have permission to log support tickets."
        return True, "Authorization successful."

    def _run(self, input_data: CreateTicketInput) -> CreateTicketOutput:
        """Create ticket in mock database and return structured output."""
        db = get_mock_db()
        case_record = db.create_ticket(
            student_id=input_data.student_id,
            category=input_data.category.value,
            subject=input_data.subject,
            description=input_data.description,
            priority=input_data.priority.value,
        )

        return CreateTicketOutput(
            success=True,
            ticket_id=case_record["case_id"],
            status="CREATED",
            assigned_department=case_record["assigned_department"],
            created_at=case_record["created_at"],
            estimated_response_days=2,
            message=(
                f"Support ticket {case_record['case_id']} successfully created and "
                f"assigned to {case_record['assigned_department']}."
            ),
            error=None,
        )

    def _handle_validation_error(self, error_msg: str) -> CreateTicketOutput:
        return CreateTicketOutput(
            success=False,
            ticket_id=None,
            status="INVALID_INPUT",
            assigned_department=None,
            created_at=None,
            estimated_response_days=None,
            message="Failed to create support ticket due to invalid or missing parameters.",
            error=f"VALIDATION_ERROR: {error_msg}",
        )

    def _handle_authorization_failure(self, reason: str) -> CreateTicketOutput:
        return CreateTicketOutput(
            success=False,
            ticket_id=None,
            status="UNAUTHORIZED",
            assigned_department=None,
            created_at=None,
            estimated_response_days=None,
            message="Ticket creation unauthorized.",
            error=f"AUTH_DENIED: {reason}",
        )

    def _handle_execution_error(self, exc: Exception) -> CreateTicketOutput:
        return CreateTicketOutput(
            success=False,
            ticket_id=None,
            status="SERVICE_ERROR",
            assigned_department=None,
            created_at=None,
            estimated_response_days=None,
            message="An unexpected system error occurred while creating the ticket.",
            error=f"EXECUTION_ERROR: {str(exc)}",
        )
