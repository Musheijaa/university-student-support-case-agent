"""Tool 4 (High-Impact): SubmitGradeAppealTool.

Lodges an official academic grade remarking / appeal request to the Makerere University
Senate Examinations Committee. Because this is a high-impact academic decision with financial
obligations (50,000 UGX appeal deposit) and irreversible senate review, it requires explicit
human-in-the-loop approval before firing.
"""

from datetime import datetime, timezone
import random

from tools.base import BaseTool
from tools.schemas import SubmitGradeAppealInput, SubmitGradeAppealOutput


class SubmitGradeAppealTool(BaseTool[SubmitGradeAppealInput, SubmitGradeAppealOutput]):
    """High-impact tool to lodge a formal university grade appeal."""

    name = "submit_grade_appeal"
    description = (
        "Submits a formal academic grade appeal/re-marking request to the Makerere University "
        "Academic Registrar & Senate Examinations Committee. Requires non-refundable 50,000 UGX "
        "fee acknowledgment and explicit human-in-the-loop approval."
    )
    input_schema_class = SubmitGradeAppealInput
    output_schema_class = SubmitGradeAppealOutput
    requires_human_approval: bool = True

    def authorize(self, input_data: SubmitGradeAppealInput) -> tuple[bool, str]:
        """Verify student credentials."""
        token = input_data.auth_token.strip().lower()
        if token in {"unauthorized", "expired", "invalid", "revoked", "forbidden"}:
            return False, f"Auth token '{input_data.auth_token}' is invalid or expired."
        if token.startswith("invalid-") or token.startswith("unauthorized-"):
            return False, "Provided credentials do not have permission to lodge grade appeals."
        return True, "Authorization successful."

    def _run(self, input_data: SubmitGradeAppealInput) -> SubmitGradeAppealOutput:
        """Lodge formal appeal record."""
        random_num = random.randint(1000, 9999)
        appeal_id = f"APPL-2026-{random_num}"
        now_iso = datetime.now(timezone.utc).isoformat()

        return SubmitGradeAppealOutput(
            success=True,
            appeal_id=appeal_id,
            status="LODGED",
            course_code=input_data.course_code.upper(),
            appeal_fee_ugx=50000,
            assigned_board="Makerere Senate Examinations Committee",
            created_at=now_iso,
            message=(
                f"Formal grade appeal {appeal_id} successfully lodged for course "
                f"'{input_data.course_code.upper()}'. Routed to Senate Examinations Committee. "
                "Deposit fee of 50,000 UGX charged to student account."
            ),
            error=None,
        )

    def _handle_validation_error(self, error_msg: str) -> SubmitGradeAppealOutput:
        return SubmitGradeAppealOutput(
            success=False,
            appeal_id=None,
            status="INVALID_INPUT",
            course_code=None,
            appeal_fee_ugx=None,
            assigned_board=None,
            created_at=None,
            message="Failed to submit grade appeal due to invalid parameters or missing fee agreement.",
            error=f"VALIDATION_ERROR: {error_msg}",
        )

    def _handle_authorization_failure(self, reason: str) -> SubmitGradeAppealOutput:
        return SubmitGradeAppealOutput(
            success=False,
            appeal_id=None,
            status="UNAUTHORIZED",
            course_code=None,
            appeal_fee_ugx=None,
            assigned_board=None,
            created_at=None,
            message="Grade appeal submission unauthorized.",
            error=f"AUTH_DENIED: {reason}",
        )

    def _handle_execution_error(self, exc: Exception) -> SubmitGradeAppealOutput:
        return SubmitGradeAppealOutput(
            success=False,
            appeal_id=None,
            status="SERVICE_ERROR",
            course_code=None,
            appeal_fee_ugx=None,
            assigned_board=None,
            created_at=None,
            message="An unexpected system error occurred while submitting grade appeal.",
            error=f"EXECUTION_ERROR: {str(exc)}",
        )
