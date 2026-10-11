"""Week 6 tests for the bounded per-session memory store."""

import time
from pathlib import Path

import pytest

from agent import memory


@pytest.fixture
def db_path(tmp_path: Path) -> str:
    return str(tmp_path / "sessions.db")


def test_read_returns_none_for_unknown_session(db_path: str):
    assert memory.read_session("missing", db_path=db_path) is None


def test_write_then_read_round_trip(db_path: str):
    memory.write_session(
        "s1",
        message="I lost my student ID.",
        response="I drafted a ticket for you.",
        drafted_ticket_ids=["DRAFT-001"],
        status="human_approval_required",
        db_path=db_path,
    )
    result = memory.read_session("s1", db_path=db_path)
    assert result is not None
    assert result["last_message"] == "I lost my student ID."
    assert result["last_drafted_ticket_ids"] == ["DRAFT-001"]
    assert result["last_status"] == "human_approval_required"


def test_write_is_upsert_not_append(db_path: str):
    memory.write_session(
        "s1", message="first", response="r1",
        drafted_ticket_ids=[], status="completed", db_path=db_path,
    )
    memory.write_session(
        "s1", message="second", response="r2",
        drafted_ticket_ids=["DRAFT-002"], status="completed", db_path=db_path,
    )
    result = memory.read_session("s1", db_path=db_path)
    assert result["last_message"] == "second"
    assert result["last_drafted_ticket_ids"] == ["DRAFT-002"]


def test_sessions_are_isolated(db_path: str):
    memory.write_session(
        "alice", message="a", response="ra",
        drafted_ticket_ids=[], status="completed", db_path=db_path,
    )
    memory.write_session(
        "bob", message="b", response="rb",
        drafted_ticket_ids=[], status="completed", db_path=db_path,
    )
    assert memory.read_session("alice", db_path=db_path)["last_message"] == "a"
    assert memory.read_session("bob", db_path=db_path)["last_message"] == "b"


def test_expired_session_returns_none(db_path: str):
    memory.write_session(
        "s1", message="old", response="r",
        drafted_ticket_ids=[], status="completed", db_path=db_path,
    )
    # ttl of 0 hours means anything already written is expired
    time.sleep(0.01)
    assert memory.read_session("s1", db_path=db_path, ttl_hours=0) is None


def test_clear_session_removes_only_that_session(db_path: str):
    memory.write_session(
        "s1", message="a", response="r",
        drafted_ticket_ids=[], status="completed", db_path=db_path,
    )
    memory.write_session(
        "s2", message="b", response="r",
        drafted_ticket_ids=[], status="completed", db_path=db_path,
    )
    memory.clear_session("s1", db_path=db_path)
    assert memory.read_session("s1", db_path=db_path) is None
    assert memory.read_session("s2", db_path=db_path) is not None


def test_purge_expired(db_path: str):
    memory.write_session(
        "s1", message="a", response="r",
        drafted_ticket_ids=[], status="completed", db_path=db_path,
    )
    time.sleep(0.01)
    removed = memory.purge_expired(db_path, ttl_hours=0)
    assert removed == 1
