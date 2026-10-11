"""Tests for Task 1: State model, lifecycle stages, and transition validation."""

import pytest

from agent.state import (
    AgentStage,
    AgentState,
    AgentStep,
    InvalidStateTransitionError,
    validate_stage_transition,
    validate_status_transition,
)
from agent.state_store import (
    delete_session_state,
    get_session_state,
    list_session_states,
    save_session_state,
)


def test_valid_status_transitions():
    """Verify that allowed transitions from 'running' succeed without error."""
    valid_terminal_statuses = [
        "completed",
        "human_approval_required",
        "max_iterations_reached",
        "max_tool_calls_reached",
        "tool_not_approved",
        "llm_error",
    ]
    for target in valid_terminal_statuses:
        state = AgentState(message="Test question", status="running")
        state.transition_to(target)
        assert state.status == target
        assert state.stage == AgentStage.TERMINAL


def test_reject_transition_from_terminal_status():
    """Task 1 Rule: Terminal statuses are permanent and cannot transition to any other status."""
    terminal_statuses = [
        "completed",
        "human_approval_required",
        "max_iterations_reached",
        "max_tool_calls_reached",
        "tool_not_approved",
        "llm_error",
    ]
    for term in terminal_statuses:
        state = AgentState(message="Test", status=term)
        # Attempt transition back to running
        with pytest.raises(InvalidStateTransitionError) as exc_info:
            state.transition_to("running")
        assert f"State '{term}' is terminal" in str(exc_info.value)

        # Attempt transition to another terminal status
        with pytest.raises(InvalidStateTransitionError):
            state.transition_to("completed" if term != "completed" else "llm_error")


def test_reject_transition_to_unknown_status():
    """Task 1 Rule: Transitions to unrecognized statuses must be rejected."""
    state = AgentState(message="Test", status="running")
    with pytest.raises(InvalidStateTransitionError):
        state.transition_to("arbitrary_unknown_status")


def test_stop_method_enforces_transition_validation():
    """state.stop() must enforce transition validation and reject repeat calls once terminal."""
    state = AgentState(message="Test", status="running")
    state.stop("completed", "Answer text")
    assert state.status == "completed"
    assert state.response == "Answer text"

    # Attempting to call stop again once terminal must raise InvalidStateTransitionError
    with pytest.raises(InvalidStateTransitionError):
        state.stop("llm_error", "Another answer")


def test_valid_stage_transitions():
    """Test standard 6-stage lifecycle transitions: Sense -> Context -> Plan -> Act -> Observe -> Replan -> Plan."""
    state = AgentState(message="Check schedule")
    assert state.stage == AgentStage.INITIALIZED

    state.transition_stage(AgentStage.SENSE)
    assert state.stage == AgentStage.SENSE

    state.transition_stage(AgentStage.CONTEXT)
    assert state.stage == AgentStage.CONTEXT

    state.transition_stage(AgentStage.PLAN)
    assert state.stage == AgentStage.PLAN

    state.transition_stage(AgentStage.ACT)
    assert state.stage == AgentStage.ACT

    state.transition_stage(AgentStage.OBSERVE)
    assert state.stage == AgentStage.OBSERVE

    state.transition_stage(AgentStage.REPLAN)
    assert state.stage == AgentStage.REPLAN

    # Replan loops back to Plan
    state.transition_stage(AgentStage.PLAN)
    assert state.stage == AgentStage.PLAN

    # Plan terminates
    state.transition_stage(AgentStage.TERMINAL)
    assert state.stage == AgentStage.TERMINAL


def test_reject_invalid_stage_transitions():
    """Task 1 Rule: Disallowed jumps across cognitive loop stages must be rejected."""
    # SENSE directly to ACT without Context/Plan
    with pytest.raises(InvalidStateTransitionError):
        validate_stage_transition(AgentStage.SENSE, AgentStage.ACT)

    # CONTEXT directly to OBSERVE without Plan/Act
    with pytest.raises(InvalidStateTransitionError):
        validate_stage_transition(AgentStage.CONTEXT, AgentStage.OBSERVE)

    # OBSERVE directly to ACT without Replan/Plan
    with pytest.raises(InvalidStateTransitionError):
        validate_stage_transition(AgentStage.OBSERVE, AgentStage.ACT)

    # TERMINAL back to active stage
    with pytest.raises(InvalidStateTransitionError):
        validate_stage_transition(AgentStage.TERMINAL, AgentStage.PLAN)


def test_session_state_serialization():
    """Verify session-state object serializes to and deserializes from dictionary losslessly."""
    state = AgentState(
        message="What is the exam schedule?",
        student_id="2200701234",
        status="running",
        stage=AgentStage.PLAN,
        plan="1 source retrieved",
        iteration_count=1,
        tool_call_count=1,
    )
    state.add_step(
        AgentStep(
            iteration=1,
            decision="tool_call",
            tool_name="check_timetable",
            tool_arguments={"course_code": "BSE4104"},
            tool_result={"success": True},
            observation="Found 3 sessions",
        )
    )

    data = state.to_dict()
    assert data["student_id"] == "2200701234"
    assert data["iteration_count"] == 1
    assert len(data["steps"]) == 1
    assert data["steps"][0]["tool_name"] == "check_timetable"

    restored = AgentState.from_dict(data)
    assert restored.run_id == state.run_id
    assert restored.student_id == "2200701234"
    assert restored.stage == AgentStage.PLAN
    assert len(restored.steps) == 1
    assert restored.steps[0].tool_name == "check_timetable"


def test_state_store_save_get_delete(tmp_path):
    """Verify session-state persistence in SQLite state store."""
    db_path = str(tmp_path / "state_store.db")
    state = AgentState(
        message="My portal is locked",
        student_id="STD-8899",
        status="running",
        stage=AgentStage.SENSE,
    )

    # Save initial state
    save_session_state(state, db_path=db_path)

    # Update state at next step
    state.transition_stage(AgentStage.CONTEXT)
    state.add_step(AgentStep(iteration=1, decision="final_answer", observation="Observed"))
    save_session_state(state, db_path=db_path)

    # Retrieve state
    loaded = get_session_state(state.run_id, db_path=db_path)
    assert loaded is not None
    assert loaded.run_id == state.run_id
    assert loaded.student_id == "STD-8899"
    assert loaded.stage == AgentStage.CONTEXT
    assert len(loaded.steps) == 1

    # List states
    states = list_session_states(student_id="STD-8899", db_path=db_path)
    assert len(states) == 1
    assert states[0].run_id == state.run_id

    # Delete state
    deleted = delete_session_state(state.run_id, db_path=db_path)
    assert deleted is True
    assert get_session_state(state.run_id, db_path=db_path) is None
