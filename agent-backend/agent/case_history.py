"""Task 4: Privacy-Preserving Case-History Memory Store.

Implements long-term memory across student-support cases with strict data handling controls:
1. Stores only approved fields: case_id, student_id, category, summary, status, action_taken, ticket_id, created_at.
2. Strictly forbids and rejects raw chat transcripts or personal data beyond student ID.
3. Provides save_case_summary(), get_case_history(student_id), and delete_case_history(student_id).
4. Logs every memory read, write, and deletion to observability traces.
"""

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import logging
from pathlib import Path
import sqlite3
from typing import Any
import uuid

from agent.traces import log_memory_trace
from config import get_settings

logger = logging.getLogger("agent.case_history")

# Task 4 Approved Fields (Data Handling Contract)
APPROVED_FIELDS = frozenset(
    {
        "case_id",
        "student_id",
        "category",
        "summary",
        "status",
        "action_taken",
        "ticket_id",
        "created_at",
    }
)

# Strictly forbidden transcript keys (prohibited from persistent memory)
FORBIDDEN_TRANSCRIPT_KEYS = frozenset(
    {
        "raw_transcript",
        "chat_transcript",
        "transcript",
        "messages",
        "chat_history",
        "raw_chat",
        "conversation",
        "dialogue",
        "transcripts",
    }
)

# Strictly forbidden personal data keys beyond student ID (privacy protection)
FORBIDDEN_PERSONAL_DATA_KEYS = frozenset(
    {
        "name",
        "student_name",
        "full_name",
        "first_name",
        "last_name",
        "email",
        "phone",
        "phone_number",
        "national_id",
        "nin",
        "dob",
        "date_of_birth",
        "address",
        "gender",
        "gpa",
        "cgpa",
        "grades",
        "grade",
        "marks",
        "medical_info",
        "financial_info",
    }
)


class PrivacyViolationError(ValueError):
    """Raised when an attempt is made to store forbidden data (transcripts or unapproved PII)."""

    def __init__(self, message: str, offending_field: str | None = None) -> None:
        super().__init__(message)
        self.offending_field = offending_field


@dataclass
class CaseSummary:
    """Approved representation of a resolved or pending student-support case."""

    case_id: str
    student_id: str
    category: str
    summary: str
    status: str
    action_taken: str
    created_at: str
    ticket_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS case_history (
    case_id TEXT PRIMARY KEY,
    student_id TEXT NOT NULL,
    category TEXT NOT NULL,
    summary TEXT NOT NULL,
    status TEXT NOT NULL,
    action_taken TEXT NOT NULL,
    ticket_id TEXT,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_case_student_id ON case_history(student_id);
CREATE INDEX IF NOT EXISTS idx_case_created_at ON case_history(created_at);
"""


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _get_db_path(db_path: str | None = None) -> str:
    if db_path is not None:
        return db_path
    try:
        return get_settings().case_history_db_path
    except Exception:
        return "data/case_history.db"


def _connect(db_path: str) -> sqlite3.Connection:
    path = Path(db_path)
    if str(db_path) != ":memory:":
        path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.executescript(_CREATE_TABLE_SQL)
    return conn


def _validate_case_data(data: dict[str, Any]) -> None:
    """Validate data against Task 4 approved schema and privacy constraints."""
    # 1. Check for raw chat transcripts
    for forbidden_key in FORBIDDEN_TRANSCRIPT_KEYS:
        if forbidden_key in data:
            raise PrivacyViolationError(
                f"Privacy policy violation: Raw chat transcripts are strictly forbidden in persistent memory. "
                f"Field '{forbidden_key}' is not allowed.",
                offending_field=forbidden_key,
            )

    # 2. Check for personal data beyond student ID
    for forbidden_key in FORBIDDEN_PERSONAL_DATA_KEYS:
        if forbidden_key in data:
            raise PrivacyViolationError(
                f"Privacy policy violation: Personal data beyond student ID is strictly forbidden in persistent memory. "
                f"Field '{forbidden_key}' is not allowed.",
                offending_field=forbidden_key,
            )

    # 3. Check for any other unapproved fields
    unapproved = set(data.keys()) - APPROVED_FIELDS
    if unapproved:
        raise PrivacyViolationError(
            f"Privacy policy violation: Unapproved field(s) detected: {sorted(list(unapproved))}. "
            f"Task 4 allows only: {sorted(list(APPROVED_FIELDS))}.",
            offending_field=sorted(list(unapproved))[0],
        )

    # 4. Mandatory fields
    student_id = data.get("student_id")
    if not student_id or not str(student_id).strip():
        raise ValueError("student_id is required for case history.")

    summary = data.get("summary")
    if not summary or not str(summary).strip():
        raise ValueError("summary is required for case history.")


def save_case_summary(
    case_data: CaseSummary | dict[str, Any],
    db_path: str | None = None,
    traces_db_path: str | None = None,
) -> CaseSummary:
    """Save an approved case summary to persistent memory.

    Validates that only Task 4 approved fields are stored (rejecting raw transcripts
    and personal data beyond student ID) and logs a WRITE trace.
    """
    raw_dict = case_data.to_dict() if isinstance(case_data, CaseSummary) else dict(case_data)
    student_id = str(raw_dict.get("student_id", "unknown")).strip()

    try:
        _validate_case_data(raw_dict)
    except PrivacyViolationError as exc:
        log_memory_trace(
            operation="WRITE",
            store="case_history",
            key=student_id,
            details={"error": "privacy_violation", "offending_field": exc.offending_field, "message": str(exc)},
            status="REJECTED",
            db_path=traces_db_path,
        )
        raise

    case_id = str(raw_dict.get("case_id") or uuid.uuid4())
    category = str(raw_dict.get("category", "General Inquiry")).strip()
    summary = str(raw_dict.get("summary", "")).strip()
    status = str(raw_dict.get("status", "completed")).strip()
    action_taken = str(raw_dict.get("action_taken", "Information provided")).strip()
    ticket_id = raw_dict.get("ticket_id")
    ticket_id = str(ticket_id).strip() if ticket_id else None
    created_at = str(raw_dict.get("created_at") or _now_iso())

    summary_obj = CaseSummary(
        case_id=case_id,
        student_id=student_id,
        category=category,
        summary=summary,
        status=status,
        action_taken=action_taken,
        ticket_id=ticket_id,
        created_at=created_at,
    )

    resolved_path = _get_db_path(db_path)
    conn = _connect(resolved_path)
    try:
        with conn:
            conn.execute(
                """
                INSERT INTO case_history (
                    case_id, student_id, category, summary, status, action_taken, ticket_id, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(case_id) DO UPDATE SET
                    student_id = excluded.student_id,
                    category = excluded.category,
                    summary = excluded.summary,
                    status = excluded.status,
                    action_taken = excluded.action_taken,
                    ticket_id = excluded.ticket_id,
                    created_at = excluded.created_at
                """,
                (
                    summary_obj.case_id,
                    summary_obj.student_id,
                    summary_obj.category,
                    summary_obj.summary,
                    summary_obj.status,
                    summary_obj.action_taken,
                    summary_obj.ticket_id,
                    summary_obj.created_at,
                ),
            )
    finally:
        conn.close()

    log_memory_trace(
        operation="WRITE",
        store="case_history",
        key=summary_obj.student_id,
        details={
            "case_id": summary_obj.case_id,
            "category": summary_obj.category,
            "status": summary_obj.status,
            "has_ticket": bool(summary_obj.ticket_id),
        },
        status="SUCCESS",
        db_path=traces_db_path,
    )

    return summary_obj


def get_case_history(
    student_id: str,
    db_path: str | None = None,
    traces_db_path: str | None = None,
) -> list[CaseSummary]:
    """Retrieve all case summaries for a specific student, logged to traces."""
    student_id = str(student_id).strip()
    resolved_path = _get_db_path(db_path)
    conn = _connect(resolved_path)
    try:
        cursor = conn.execute(
            """
            SELECT case_id, student_id, category, summary, status, action_taken, ticket_id, created_at
            FROM case_history
            WHERE student_id = ?
            ORDER BY created_at DESC
            """,
            (student_id,),
        )
        rows = cursor.fetchall()
        summaries = [
            CaseSummary(
                case_id=row["case_id"],
                student_id=row["student_id"],
                category=row["category"],
                summary=row["summary"],
                status=row["status"],
                action_taken=row["action_taken"],
                ticket_id=row["ticket_id"],
                created_at=row["created_at"],
            )
            for row in rows
        ]

        log_memory_trace(
            operation="READ",
            store="case_history",
            key=student_id,
            details={"records_retrieved": len(summaries)},
            status="SUCCESS",
            db_path=traces_db_path,
        )

        return summaries
    finally:
        conn.close()


def delete_case_history(
    student_id: str,
    db_path: str | None = None,
    traces_db_path: str | None = None,
) -> int:
    """Delete all case summaries for a specific student (right-to-be-forgotten), logged to traces."""
    student_id = str(student_id).strip()
    resolved_path = _get_db_path(db_path)
    conn = _connect(resolved_path)
    try:
        with conn:
            cursor = conn.execute(
                "DELETE FROM case_history WHERE student_id = ?",
                (student_id,),
            )
            deleted_count = cursor.rowcount

        log_memory_trace(
            operation="DELETE",
            store="case_history",
            key=student_id,
            details={"deleted_records": deleted_count},
            status="SUCCESS",
            db_path=traces_db_path,
        )

        return deleted_count
    finally:
        conn.close()
