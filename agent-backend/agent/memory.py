"""Bounded per-session memory for the Week 6 agent.

Deliberately minimal:

- one row per session (not one per turn)
- no credentials, no source documents, no step traces
- expires after MEMORY_TTL_HOURS (default 24)
- keyed by session ID; there is no cross-session lookup

The store lives in its own SQLite database (data/sessions.db) so that
memory can be reset, inspected, or deleted without touching the tickets
store (data/tickets.db). Both use the same stdlib `sqlite3` pattern.

Rationale and retention policy are documented in docs/memory-design.md.
"""

import json
import sqlite3
from datetime import datetime, timedelta, timezone

_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS session_memory (
    session_id TEXT PRIMARY KEY,
    last_message TEXT NOT NULL,
    last_response TEXT NOT NULL,
    last_drafted_ticket_ids TEXT NOT NULL,
    last_status TEXT NOT NULL,
    updated_at TEXT NOT NULL
)
"""


def _connect(db_path: str) -> sqlite3.Connection:
    """Isolated so tests can monkeypatch this to simulate an unavailable store."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute(_CREATE_TABLE_SQL)
    return conn


def _now() -> datetime:
    return datetime.now(timezone.utc)


def read_session(session_id: str, db_path: str, ttl_hours: int = 24) -> dict | None:
    """Return the last turn for this session, or None if absent or expired."""
    conn = _connect(db_path)
    try:
        row = conn.execute(
            "SELECT * FROM session_memory WHERE session_id = ?", (session_id,)
        ).fetchone()
    finally:
        conn.close()

    if row is None:
        return None

    updated = datetime.fromisoformat(row["updated_at"])
    if _now() - updated > timedelta(hours=ttl_hours):
        return None

    try:
        ticket_ids = json.loads(row["last_drafted_ticket_ids"])
    except (json.JSONDecodeError, TypeError):
        ticket_ids = []

    return {
        "last_message": row["last_message"],
        "last_response": row["last_response"],
        "last_drafted_ticket_ids": ticket_ids,
        "last_status": row["last_status"],
        "updated_at": row["updated_at"],
    }


def write_session(
    session_id: str,
    *,
    message: str,
    response: str,
    drafted_ticket_ids: list[str],
    status: str,
    db_path: str,
) -> None:
    """Upsert the current turn as the last turn for this session."""
    conn = _connect(db_path)
    try:
        conn.execute(
            """
            INSERT INTO session_memory
                (session_id, last_message, last_response,
                 last_drafted_ticket_ids, last_status, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(session_id) DO UPDATE SET
                last_message = excluded.last_message,
                last_response = excluded.last_response,
                last_drafted_ticket_ids = excluded.last_drafted_ticket_ids,
                last_status = excluded.last_status,
                updated_at = excluded.updated_at
            """,
            (
                session_id,
                message,
                response,
                json.dumps(drafted_ticket_ids),
                status,
                _now().isoformat(),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def clear_session(session_id: str, db_path: str) -> None:
    """Delete a single session's memory. Used by tests and by an explicit reset."""
    conn = _connect(db_path)
    try:
        conn.execute("DELETE FROM session_memory WHERE session_id = ?", (session_id,))
        conn.commit()
    finally:
        conn.close()


def purge_expired(db_path: str, ttl_hours: int = 24) -> int:
    """Delete rows older than ttl_hours. Returns the number of rows removed."""
    cutoff = (_now() - timedelta(hours=ttl_hours)).isoformat()
    conn = _connect(db_path)
    try:
        cursor = conn.execute(
            "DELETE FROM session_memory WHERE updated_at < ?", (cutoff,)
        )
        conn.commit()
        return cursor.rowcount
    finally:
        conn.close()
