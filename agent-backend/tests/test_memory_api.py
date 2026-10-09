"""Tests for memory, session-state, and trace HTTP endpoints in main.py."""

from fastapi.testclient import TestClient

from agent.case_history import save_case_summary
from agent.state import AgentState, AgentStep
from agent.state_store import save_session_state
from config import get_settings
from main import app

client = TestClient(app)


def test_get_and_delete_case_history_api(tmp_path):
    """Test GET and DELETE /api/v1/cases/{student_id}."""
    settings = get_settings()
    settings.case_history_db_path = str(tmp_path / "case_api.db")

    student_id = "STD-API-1"
    save_case_summary(
        {
            "case_id": "CASE-API-1",
            "student_id": student_id,
            "category": "Timetable",
            "summary": "Where is BSE4104 class?",
            "status": "completed",
            "action_taken": "Provided room 204",
        },
        db_path=settings.case_history_db_path,
    )

    # GET case history
    resp = client.get(f"/api/v1/cases/{student_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["case_id"] == "CASE-API-1"
    assert data[0]["student_id"] == student_id
    assert "raw_transcript" not in data[0]

    # DELETE case history
    del_resp = client.delete(f"/api/v1/cases/{student_id}")
    assert del_resp.status_code == 200
    assert del_resp.json()["deleted_count"] == 1

    # Verify history is now empty
    empty_resp = client.get(f"/api/v1/cases/{student_id}")
    assert empty_resp.status_code == 200
    assert len(empty_resp.json()) == 0


def test_get_session_state_api(tmp_path):
    """Test GET /api/v1/sessions/{session_id}."""
    settings = get_settings()
    settings.state_db_path = str(tmp_path / "sessions_api.db")

    state = AgentState(
        message="I lost my password",
        student_id="STD-API-2",
        status="completed",
        response="Ticket drafted",
    )
    state.add_step(AgentStep(iteration=1, decision="final_answer", observation="Produced answer"))
    save_session_state(state, db_path=settings.state_db_path)

    # Found session
    resp = client.get(f"/api/v1/sessions/{state.run_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["run_id"] == state.run_id
    assert body["student_id"] == "STD-API-2"
    assert body["status"] == "completed"
    assert len(body["steps"]) == 1

    # Not found session
    nf_resp = client.get("/api/v1/sessions/non-existent-session-id")
    assert nf_resp.status_code == 404


def test_get_memory_traces_api(tmp_path):
    """Test GET /api/v1/memory/traces."""
    settings = get_settings()
    settings.traces_db_path = str(tmp_path / "traces_api.db")

    state = AgentState(
        message="Test trace logging",
        student_id="STD-API-3",
        status="running",
    )
    save_session_state(state, db_path=str(tmp_path / "dummy_state.db"))

    resp = client.get("/api/v1/memory/traces")
    assert resp.status_code == 200
    traces = resp.json()
    assert isinstance(traces, list)
    assert len(traces) > 0
    assert any(t["key"] == state.run_id for t in traces)
