"""Tests for memory and state store observability traces.

Verifies that EVERY memory read, write, and deletion operation across
both session_state and case_history is recorded in structured audit traces.
"""

from agent.case_history import (
    PrivacyViolationError,
    delete_case_history,
    get_case_history,
    save_case_summary,
)
from agent.state import AgentState, AgentStep
from agent.state_store import delete_session_state, get_session_state, save_session_state
from agent.traces import clear_memory_traces, get_memory_traces


def test_session_state_read_and_write_logged_to_traces(tmp_path):
    """Verify that saving and reading session state logs WRITE and READ traces."""
    state_db = str(tmp_path / "session_state.db")
    traces_db = str(tmp_path / "traces.db")
    clear_memory_traces(db_path=traces_db)

    state = AgentState(
        message="Help with fees",
        student_id="STD-TRACE-1",
        status="running",
    )
    state.add_step(AgentStep(iteration=1, decision="final_answer", observation="Done"))

    # WRITE operation
    save_session_state(state, db_path=state_db, traces_db_path=traces_db)

    traces = get_memory_traces(store="session_state", key=state.run_id, db_path=traces_db)
    write_traces = [t for t in traces if t.operation == "WRITE"]
    assert len(write_traces) >= 1
    assert write_traces[0].status == "SUCCESS"
    assert write_traces[0].details["student_id"] == "STD-TRACE-1"

    # READ operation
    loaded = get_session_state(state.run_id, db_path=state_db, traces_db_path=traces_db)
    assert loaded is not None

    traces_after_read = get_memory_traces(store="session_state", key=state.run_id, db_path=traces_db)
    read_traces = [t for t in traces_after_read if t.operation == "READ"]
    assert len(read_traces) >= 1
    assert read_traces[0].status == "SUCCESS"
    assert read_traces[0].details["found"] is True

    # DELETE operation
    delete_session_state(state.run_id, db_path=state_db, traces_db_path=traces_db)
    traces_after_delete = get_memory_traces(store="session_state", key=state.run_id, db_path=traces_db)
    delete_traces = [t for t in traces_after_delete if t.operation == "DELETE"]
    assert len(delete_traces) >= 1
    assert delete_traces[0].details["deleted"] is True


def test_case_history_read_and_write_logged_to_traces(tmp_path):
    """Verify that saving, reading, and deleting case history logs WRITE, READ, and DELETE traces."""
    case_db = str(tmp_path / "case_history.db")
    traces_db = str(tmp_path / "traces.db")
    clear_memory_traces(db_path=traces_db)

    student_id = "STD-TRACE-CASE"

    # WRITE operation
    save_case_summary(
        {
            "case_id": "CASE-TR-1",
            "student_id": student_id,
            "category": "Timetable",
            "summary": "Check timetable query",
            "status": "completed",
            "action_taken": "Sent schedule",
        },
        db_path=case_db,
        traces_db_path=traces_db,
    )

    traces = get_memory_traces(store="case_history", key=student_id, db_path=traces_db)
    write_traces = [t for t in traces if t.operation == "WRITE"]
    assert len(write_traces) >= 1
    assert write_traces[0].status == "SUCCESS"
    assert write_traces[0].details["case_id"] == "CASE-TR-1"

    # READ operation
    history = get_case_history(student_id, db_path=case_db, traces_db_path=traces_db)
    assert len(history) == 1

    traces_after_read = get_memory_traces(store="case_history", key=student_id, db_path=traces_db)
    read_traces = [t for t in traces_after_read if t.operation == "READ"]
    assert len(read_traces) >= 1
    assert read_traces[0].status == "SUCCESS"
    assert read_traces[0].details["records_retrieved"] == 1

    # DELETE operation
    delete_case_history(student_id, db_path=case_db, traces_db_path=traces_db)
    traces_after_delete = get_memory_traces(store="case_history", key=student_id, db_path=traces_db)
    del_traces = [t for t in traces_after_delete if t.operation == "DELETE"]
    assert len(del_traces) >= 1
    assert del_traces[0].status == "SUCCESS"
    assert del_traces[0].details["deleted_records"] == 1


def test_privacy_violation_logs_rejected_trace(tmp_path):
    """Verify that an illegal memory write with transcripts or unapproved PII logs a REJECTED trace."""
    case_db = str(tmp_path / "case_history.db")
    traces_db = str(tmp_path / "traces.db")
    student_id = "STD-REJECT"

    try:
        save_case_summary(
            {
                "case_id": "CASE-BAD",
                "student_id": student_id,
                "category": "Admissions",
                "summary": "Application query",
                "status": "completed",
                "action_taken": "Provided info",
                "raw_transcript": "User: confidential words",
            },
            db_path=case_db,
            traces_db_path=traces_db,
        )
    except PrivacyViolationError:
        pass

    traces = get_memory_traces(store="case_history", key=student_id, db_path=traces_db)
    rejected = [t for t in traces if t.status == "REJECTED"]
    assert len(rejected) >= 1
    assert rejected[0].details["error"] == "privacy_violation"
    assert rejected[0].details["offending_field"] == "raw_transcript"
