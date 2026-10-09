"""Observability traces for memory and state store operations.

Every memory read, write, and deletion across session state and case history
is recorded as a structured trace record and persisted to SQLite and application logs.
"""

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import json
import logging
from pathlib import Path
import sqlite3
from typing import Literal
import uuid

from config import get_settings

logger = logging.getLogger("agent.memory.traces")

MemoryOperation = Literal["READ", "WRITE", "DELETE"]
MemoryStoreType = Literal["session_state", "case_history"]
TraceStatus = Literal["SUCCESS", "REJECTED", "ERROR"]

_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS memory_traces (
    trace_id TEXT PRIMARY KEY,
    timestamp TEXT NOT NULL,
    operation TEXT NOT NULL,
    store TEXT NOT NULL,
    key TEXT NOT NULL,
    details_json TEXT NOT NULL,
    status TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_traces_store_key ON memory_traces(store, key);
CREATE INDEX IF NOT EXISTS idx_traces_timestamp ON memory_traces(timestamp);
"""

# In-memory buffer for fast retrieval during testing and active process inspection
_IN_MEMORY_TRACES: list["MemoryTraceRecord"] = []


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class MemoryTraceRecord:
    trace_id: str
    timestamp: str
    operation: MemoryOperation
    store: MemoryStoreType
    key: str
    details: dict = field(default_factory=dict)
    status: TraceStatus = "SUCCESS"

    def to_dict(self) -> dict:
        return asdict(self)


def _get_db_path(db_path: str | None = None) -> str:
    if db_path is not None:
        return db_path
    try:
        return get_settings().traces_db_path
    except Exception:
        return "data/traces.db"


def _connect(db_path: str) -> sqlite3.Connection:
    path = Path(db_path)
    if str(db_path) != ":memory:":
        path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.executescript(_CREATE_TABLE_SQL)
    return conn


def log_memory_trace(
    operation: MemoryOperation,
    store: MemoryStoreType,
    key: str,
    details: dict | None = None,
    status: TraceStatus = "SUCCESS",
    db_path: str | None = None,
) -> MemoryTraceRecord:
    """Record an audit trace for a memory/state read, write, or delete operation."""
    resolved_path = _get_db_path(db_path)
    details = details or {}
    record = MemoryTraceRecord(
        trace_id=str(uuid.uuid4()),
        timestamp=_now_iso(),
        operation=operation,
        store=store,
        key=key,
        details=details,
        status=status,
    )

    logger.info(
        "MemoryTrace [%s] %s store=%s key=%s status=%s details=%s",
        record.timestamp,
        record.operation,
        record.store,
        record.key,
        record.status,
        record.details,
    )

    _IN_MEMORY_TRACES.append(record)

    try:
        conn = _connect(resolved_path)
        with conn:
            conn.execute(
                "INSERT INTO memory_traces (trace_id, timestamp, operation, store, key, details_json, status) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    record.trace_id,
                    record.timestamp,
                    record.operation,
                    record.store,
                    record.key,
                    json.dumps(record.details),
                    record.status,
                ),
            )
        conn.close()
    except Exception as exc:
        logger.warning("Failed to persist memory trace to SQLite: %s", exc)

    return record


def get_memory_traces(
    store: MemoryStoreType | str | None = None,
    key: str | None = None,
    operation: MemoryOperation | str | None = None,
    db_path: str | None = None,
) -> list[MemoryTraceRecord]:
    """Retrieve filtered memory traces from SQLite (or fallback to in-memory)."""
    resolved_path = _get_db_path(db_path)
    try:
        conn = _connect(resolved_path)
        query = "SELECT trace_id, timestamp, operation, store, key, details_json, status FROM memory_traces WHERE 1=1"
        params: list[str] = []
        if store:
            query += " AND store = ?"
            params.append(str(store))
        if key:
            query += " AND key = ?"
            params.append(key)
        if operation:
            query += " AND operation = ?"
            params.append(str(operation))
        query += " ORDER BY timestamp ASC"

        cursor = conn.execute(query, params)
        records: list[MemoryTraceRecord] = []
        for row in cursor.fetchall():
            records.append(
                MemoryTraceRecord(
                    trace_id=row["trace_id"],
                    timestamp=row["timestamp"],
                    operation=row["operation"],
                    store=row["store"],
                    key=row["key"],
                    details=json.loads(row["details_json"]),
                    status=row["status"],
                )
            )
        conn.close()
        return records
    except Exception as exc:
        logger.warning("Failed to query memory traces from SQLite, using in-memory: %s", exc)
        results = _IN_MEMORY_TRACES
        if store:
            results = [r for r in results if r.store == store]
        if key:
            results = [r for r in results if r.key == key]
        if operation:
            results = [r for r in results if r.operation == operation]
        return list(results)


def clear_memory_traces(db_path: str | None = None) -> None:
    """Clear memory traces (useful for test isolation)."""
    global _IN_MEMORY_TRACES
    _IN_MEMORY_TRACES = []
    resolved_path = _get_db_path(db_path)
    try:
        conn = _connect(resolved_path)
        with conn:
            conn.execute("DELETE FROM memory_traces")
        conn.close()
    except Exception as exc:
        logger.warning("Failed to clear memory traces from SQLite: %s", exc)
