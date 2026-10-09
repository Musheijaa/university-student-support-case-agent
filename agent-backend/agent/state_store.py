"""SQLite-backed session-state store.

Persists the session-state object at each agent step, allowing inspection,
auditability, and recovery of ongoing or completed episodes.
Every state read and write operation is logged to the memory trace log.
"""

from datetime import datetime, timezone
import json
import logging
from pathlib import Path
import sqlite3

from agent.state import AgentState
from agent.traces import log_memory_trace
from config import get_settings

logger = logging.getLogger("agent.state_store")

_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS session_states (
    session_id TEXT PRIMARY KEY,
    student_id TEXT NOT NULL,
    status TEXT NOT NULL,
    stage TEXT NOT NULL,
    iteration_count INTEGER NOT NULL,
    tool_call_count INTEGER NOT NULL,
    plan TEXT NOT NULL,
    response TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_session_student_id ON session_states(student_id);
"""


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _get_db_path(db_path: str | None = None) -> str:
    if db_path is not None:
        return db_path
    try:
        return get_settings().state_db_path
    except Exception:
        return "data/session_state.db"


def _connect(db_path: str) -> sqlite3.Connection:
    path = Path(db_path)
    if str(db_path) != ":memory:":
        path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.executescript(_CREATE_TABLE_SQL)
    return conn


def save_session_state(
    state: AgentState,
    db_path: str | None = None,
    traces_db_path: str | None = None,
) -> None:
    """Save or update the session-state object in SQLite and log a WRITE trace."""
    resolved_path = _get_db_path(db_path)
    now = _now_iso()
    serialized = state.to_dict()
    stage_str = state.stage.value if hasattr(state.stage, "value") else str(state.stage)

    conn = _connect(resolved_path)
    try:
        with conn:
            # Check if record already exists to preserve created_at
            cursor = conn.execute(
                "SELECT created_at FROM session_states WHERE session_id = ?",
                (state.run_id,),
            )
            existing = cursor.fetchone()
            created_at = existing["created_at"] if existing else now

            conn.execute(
                """
                INSERT INTO session_states (
                    session_id, student_id, status, stage, iteration_count,
                    tool_call_count, plan, response, payload_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    student_id = excluded.student_id,
                    status = excluded.status,
                    stage = excluded.stage,
                    iteration_count = excluded.iteration_count,
                    tool_call_count = excluded.tool_call_count,
                    plan = excluded.plan,
                    response = excluded.response,
                    payload_json = excluded.payload_json,
                    updated_at = excluded.updated_at
                """,
                (
                    state.run_id,
                    state.student_id,
                    state.status,
                    stage_str,
                    state.iteration_count,
                    state.tool_call_count,
                    state.plan,
                    state.response,
                    json.dumps(serialized),
                    created_at,
                    now,
                ),
            )
    finally:
        conn.close()

    # Log memory write trace
    log_memory_trace(
        operation="WRITE",
        store="session_state",
        key=state.run_id,
        details={
            "student_id": state.student_id,
            "status": state.status,
            "stage": stage_str,
            "iteration": state.iteration_count,
            "tool_calls": state.tool_call_count,
            "steps_count": len(state.steps),
        },
        status="SUCCESS",
        db_path=traces_db_path,
    )


def get_session_state(
    session_id: str,
    db_path: str | None = None,
    traces_db_path: str | None = None,
) -> AgentState | None:
    """Load a session state by its session_id (run_id) and log a READ trace."""
    resolved_path = _get_db_path(db_path)
    conn = _connect(resolved_path)
    try:
        cursor = conn.execute(
            "SELECT payload_json FROM session_states WHERE session_id = ?",
            (session_id,),
        )
        row = cursor.fetchone()
        if not row:
            log_memory_trace(
                operation="READ",
                store="session_state",
                key=session_id,
                details={"found": False},
                status="SUCCESS",
                db_path=traces_db_path,
            )
            return None

        state_dict = json.loads(row["payload_json"])
        state = AgentState.from_dict(state_dict)

        log_memory_trace(
            operation="READ",
            store="session_state",
            key=session_id,
            details={"found": True, "status": state.status, "steps_count": len(state.steps)},
            status="SUCCESS",
            db_path=traces_db_path,
        )
        return state
    finally:
        conn.close()


def delete_session_state(
    session_id: str,
    db_path: str | None = None,
    traces_db_path: str | None = None,
) -> bool:
    """Delete a session state from SQLite and log a DELETE trace."""
    resolved_path = _get_db_path(db_path)
    conn = _connect(resolved_path)
    try:
        with conn:
            cursor = conn.execute(
                "DELETE FROM session_states WHERE session_id = ?",
                (session_id,),
            )
            deleted = cursor.rowcount > 0

        log_memory_trace(
            operation="DELETE",
            store="session_state",
            key=session_id,
            details={"deleted": deleted},
            status="SUCCESS",
            db_path=traces_db_path,
        )
        return deleted
    finally:
        conn.close()


def list_session_states(
    student_id: str | None = None, db_path: str | None = None
) -> list[AgentState]:
    """List session states, optionally filtered by student_id."""
    resolved_path = _get_db_path(db_path)
    conn = _connect(resolved_path)
    try:
        if student_id:
            cursor = conn.execute(
                "SELECT payload_json FROM session_states WHERE student_id = ? ORDER BY created_at DESC",
                (student_id,),
            )
        else:
            cursor = conn.execute(
                "SELECT payload_json FROM session_states ORDER BY created_at DESC"
            )

        states: list[AgentState] = []
        for row in cursor.fetchall():
            states.append(AgentState.from_dict(json.loads(row["payload_json"])))

        log_memory_trace(
            operation="READ",
            store="session_state",
            key=student_id or "*",
            details={"count": len(states)},
            status="SUCCESS",
        )
        return states
    finally:
        conn.close()
