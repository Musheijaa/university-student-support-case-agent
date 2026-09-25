"""Tool 2: GetCaseStatusTool.

Retrieves current status, department assignment, and audit history for a student support case.
"""

from tools.base import BaseTool
from tools.mock_db import get_mock_db
from tools.schemas import CaseNote, GetCaseStatusInput, GetCaseStatusOutput


class GetCaseStatusTool(BaseTool[GetCaseStatusInput, GetCaseStatusOutput]):
    """Tool to check student case status."""

    name = "get_case_status"
    description = (
        "Retrieves the live status, assigned university officer, department, and progress notes "
        "for a given student support case or ticket ID."
    )
    input_schema_class = GetCaseStatusInput
    output_schema_class = GetCaseStatusOutput

    def authorize(self, input_data: GetCaseStatusInput) -> tuple[bool, str]:
        """Verify token and ensure case ownership or staff role."""
        token = input_data.auth_token.strip().lower()
        if token in {"unauthorized", "expired", "invalid", "forbidden"}:
            return False, f"Auth token '{input_data.auth_token}' is invalid or expired."

        # Check ownership match if case exists
        db = get_mock_db()
        case = db.get_case(input_data.case_id)
        if case and not token.startswith("staff-"):
            if case["student_id"] != input_data.student_id:
                return (
                    False,
                    f"Student ID '{input_data.student_id}' is not authorized to access case '{input_data.case_id}'.",
                )

        return True, "Authorization successful."

    def _run(self, input_data: GetCaseStatusInput) -> GetCaseStatusOutput:
        """Fetch case status from mock DB and return structured response."""
        db = get_mock_db()
        case = db.get_case(input_data.case_id)

        if not case:
            return GetCaseStatusOutput(
                success=False,
                case_id=input_data.case_id,
                student_id=input_data.student_id,
                category=None,
                subject=None,
                status="NOT_FOUND",
                assigned_officer=None,
                created_at=None,
                last_updated=None,
                notes=[],
                message=f"No case found matching ID '{input_data.case_id}'.",
                error="CASE_NOT_FOUND",
            )

        notes_objs = [
            n if isinstance(n, CaseNote) else CaseNote(**n) for n in case["notes"]
        ]

        return GetCaseStatusOutput(
            success=True,
            case_id=case["case_id"],
            student_id=case["student_id"],
            category=case["category"],
            subject=case["subject"],
            status=case["status"],
            assigned_officer=case["assigned_officer"],
            created_at=case["created_at"],
            last_updated=case["last_updated"],
            notes=notes_objs,
            message=f"Case status for '{case['case_id']}' is currently '{case['status']}'.",
            error=None,
        )

    def _handle_validation_error(self, error_msg: str) -> GetCaseStatusOutput:
        return GetCaseStatusOutput(
            success=False,
            case_id=None,
            student_id=None,
            category=None,
            subject=None,
            status="INVALID_INPUT",
            assigned_officer=None,
            created_at=None,
            last_updated=None,
            notes=[],
            message="Failed to query case status due to invalid input parameters.",
            error=f"VALIDATION_ERROR: {error_msg}",
        )

    def _handle_authorization_failure(self, reason: str) -> GetCaseStatusOutput:
        return GetCaseStatusOutput(
            success=False,
            case_id=None,
            student_id=None,
            category=None,
            subject=None,
            status="UNAUTHORIZED",
            assigned_officer=None,
            created_at=None,
            last_updated=None,
            notes=[],
            message="Case status retrieval unauthorized.",
            error=f"AUTH_DENIED: {reason}",
        )

    def _handle_execution_error(self, exc: Exception) -> GetCaseStatusOutput:
        return GetCaseStatusOutput(
            success=False,
            case_id=None,
            student_id=None,
            category=None,
            subject=None,
            status="SERVICE_ERROR",
            assigned_officer=None,
            created_at=None,
            last_updated=None,
            notes=[],
            message="An unexpected system error occurred while retrieving case status.",
            error=f"EXECUTION_ERROR: {str(exc)}",
        )
