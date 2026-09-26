"""create_support_ticket tool + the ticket draft/approval store.

Tickets are stored in a small SQLite database (stdlib `sqlite3`, no new
dependency). The LLM can only ever create a PENDING_APPROVAL draft via
the `create_support_ticket` tool - `approve_ticket`/`reject_ticket`
below are never exposed to the model as callable tools (see
tools/registry.py's allow-list). They are only reachable through the
authenticated HTTP endpoints in main.py, so there is no code path by
which the model can submit or approve a ticket itself.
"""

import sqlite3
from datetime import datetime, timezone

from tools.schemas import CreateSupportTicketInput, CreateSupportTicketOutput, TicketRecord

_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS tickets (
    ticket_id TEXT PRIMARY KEY,
    category TEXT NOT NULL,
    subject TEXT NOT NULL,
    description TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
)
"""


def _connect(db_path: str) -> sqlite3.Connection:
    """Isolated so tests can monkeypatch this to simulate the service being unavailable."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute(_CREATE_TABLE_SQL)
    return conn


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_support_ticket(
    input_data: CreateSupportTicketInput, db_path: str
) -> CreateSupportTicketOutput:
    conn = _connect(db_path)
    try:
        cursor = conn.execute("SELECT COUNT(*) FROM tickets")
        next_number = cursor.fetchone()[0] + 1
        ticket_id = f"DRAFT-{next_number:03d}"
        now = _now()
        conn.execute(
            "INSERT INTO tickets (ticket_id, category, subject, description, status, "
            "created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                ticket_id,
                input_data.category,
                input_data.subject,
                input_data.description,
                "PENDING_APPROVAL",
                now,
                now,
            ),
        )
        conn.commit()
    finally:
        conn.close()

    return CreateSupportTicketOutput(
        success=True,
        ticket_id=ticket_id,
        status="PENDING_APPROVAL",
        category=input_data.category,
        subject=input_data.subject,
    )


def get_ticket(ticket_id: str, db_path: str) -> TicketRecord | None:
    conn = _connect(db_path)
    try:
        row = conn.execute(
            "SELECT * FROM tickets WHERE ticket_id = ?", (ticket_id,)
        ).fetchone()
    finally:
        conn.close()

    if row is None:
        return None
    return TicketRecord(
        ticket_id=row["ticket_id"],
        category=row["category"],
        subject=row["subject"],
        description=row["description"],
        status=row["status"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _transition_ticket(ticket_id: str, target_status: str, db_path: str) -> dict:
    record = get_ticket(ticket_id, db_path)
    if record is None:
        return {"success": False, "error": f"Ticket {ticket_id!r} was not found."}

    if record.status != "PENDING_APPROVAL":
        return {
            "success": False,
            "error": f"Ticket {ticket_id!r} is already {record.status}; its state cannot be changed.",
        }

    conn = _connect(db_path)
    try:
        conn.execute(
            "UPDATE tickets SET status = ?, updated_at = ? WHERE ticket_id = ?",
            (target_status, _now(), ticket_id),
        )
        conn.commit()
    finally:
        conn.close()

    return {"success": True, "ticket_id": ticket_id, "status": target_status}


def approve_ticket(ticket_id: str, db_path: str) -> dict:
    return _transition_ticket(ticket_id, "SUBMITTED", db_path)


def reject_ticket(ticket_id: str, db_path: str) -> dict:
    return _transition_ticket(ticket_id, "REJECTED", db_path)
