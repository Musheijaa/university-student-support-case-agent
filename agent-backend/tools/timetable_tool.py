"""Tool 3: CheckTimetableTool.

Queries course lecture, lab, and examination schedules for Makerere University students.
"""

from tools.base import BaseTool
from tools.mock_db import get_mock_db
from tools.schemas import CheckTimetableInput, CheckTimetableOutput


class CheckTimetableTool(BaseTool[CheckTimetableInput, CheckTimetableOutput]):
    """Tool to check course and examination timetables."""

    name = "check_timetable"
    description = (
        "Queries lecture, tutorial, laboratory, and examination timetable schedules "
        "for Makerere University courses or specific student course codes."
    )
    input_schema_class = CheckTimetableInput
    output_schema_class = CheckTimetableOutput

    def authorize(self, input_data: CheckTimetableInput) -> tuple[bool, str]:
        """Verify caller auth token."""
        token = input_data.auth_token.strip().lower()
        if token in {"unauthorized", "expired", "invalid", "forbidden"}:
            return False, f"Auth token '{input_data.auth_token}' is invalid or expired."
        return True, "Authorization successful."

    def _run(self, input_data: CheckTimetableInput) -> CheckTimetableOutput:
        """Fetch timetable schedule entries from mock database."""
        db = get_mock_db()
        entries = db.get_timetable(
            student_id=input_data.student_id, course_code=input_data.course_code
        )

        if not entries:
            course_str = (
                f" for course '{input_data.course_code}'"
                if input_data.course_code
                else ""
            )
            return CheckTimetableOutput(
                success=True,
                student_id=input_data.student_id,
                semester=input_data.semester,
                total_found=0,
                entries=[],
                message=f"No published timetable entries found{course_str} in {input_data.semester}.",
                error=None,
            )

        return CheckTimetableOutput(
            success=True,
            student_id=input_data.student_id,
            semester=input_data.semester,
            total_found=len(entries),
            entries=entries,
            message=(
                f"Successfully retrieved {len(entries)} timetable entry/entries for "
                f"student '{input_data.student_id}' in {input_data.semester}."
            ),
            error=None,
        )

    def _handle_validation_error(self, error_msg: str) -> CheckTimetableOutput:
        return CheckTimetableOutput(
            success=False,
            student_id=None,
            semester=None,
            total_found=0,
            entries=[],
            message="Failed to query timetable due to invalid input parameters.",
            error=f"VALIDATION_ERROR: {error_msg}",
        )

    def _handle_authorization_failure(self, reason: str) -> CheckTimetableOutput:
        return CheckTimetableOutput(
            success=False,
            student_id=None,
            semester=None,
            total_found=0,
            entries=[],
            message="Timetable lookup unauthorized.",
            error=f"AUTH_DENIED: {reason}",
        )

    def _handle_execution_error(self, exc: Exception) -> CheckTimetableOutput:
        return CheckTimetableOutput(
            success=False,
            student_id=None,
            semester=None,
            total_found=0,
            entries=[],
            message="An unexpected system error occurred while looking up timetable.",
            error=f"EXECUTION_ERROR: {str(exc)}",
        )
