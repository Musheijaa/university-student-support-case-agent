"""Demo script showing the State Store, State Model, Case History, and Traces in action."""

import json
from pathlib import Path
import sys

# Ensure agent-backend is on path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from agent.case_history import (
    PrivacyViolationError,
    get_case_history,
    save_case_summary,
)
from agent.state import (
    AgentStage,
    AgentState,
    AgentStep,
    InvalidStateTransitionError,
)
from agent.state_store import get_session_state, save_session_state
from agent.traces import get_memory_traces


def run_demo():
    print("=" * 70)
    print("DEMO: Agent State Store & Case-History Memory System")
    print("=" * 70)

    # 1. Create a session-state object and update it at each step
    print("\n[Step 1] Creating session-state and advancing lifecycle stages...")
    state = AgentState(
        message="When is the BSE4104 class scheduled?",
        student_id="2200701999",
        status="running",
    )
    print(f"  Initialized session: run_id={state.run_id}, student_id={state.student_id}")

    # Stage: Sense
    state.transition_stage(AgentStage.SENSE)
    save_session_state(state)
    print(f"  -> Stage {state.stage.value.upper()}: saved to SQLite state store.")

    # Stage: Context
    state.transition_stage(AgentStage.CONTEXT)
    state.plan = "1 source retrieved; approved tools: check_timetable, create_support_ticket; budget: 4 iterations"
    save_session_state(state)
    print(f"  -> Stage {state.stage.value.upper()}: plan recorded and saved.")

    # Stage: Plan -> Act -> Observe
    state.transition_stage(AgentStage.PLAN)
    state.transition_stage(AgentStage.ACT)
    state.add_step(
        AgentStep(
            iteration=1,
            decision="tool_call",
            tool_name="check_timetable",
            tool_arguments={"course_code": "BSE4104"},
            tool_result={"success": True, "course_code": "BSE4104"},
            observation="Found 3 timetable sessions for BSE4104.",
        )
    )
    state.transition_stage(AgentStage.OBSERVE)
    save_session_state(state)
    print(f"  -> Stage {state.stage.value.upper()}: recorded tool step and saved.")

    # Stage: Terminal Stop
    state.stop("completed", "BSE4104 meets Mondays 10:00 - 12:00 in Room 204.")
    save_session_state(state)
    print(f"  -> Stage {state.stage.value.upper()}: run completed and saved.")

    # 2. Demonstrate rejection of invalid transitions (Task 1)
    print("\n[Step 2] Testing Task 1 transition validation...")
    try:
        print("  Attempting forbidden transition: 'completed' -> 'running'...")
        state.transition_to("running")
    except InvalidStateTransitionError as exc:
        print(f"  [REJECTED AS EXPECTED] {exc}")

    # 3. Retrieve session state from SQLite
    print("\n[Step 3] Loading persisted session state from SQLite...")
    loaded_state = get_session_state(state.run_id)
    if loaded_state:
        print(f"  Loaded session: run_id={loaded_state.run_id}")
        print(f"  Status: {loaded_state.status}, Stage: {loaded_state.stage.value}")
        print(f"  Recorded steps: {len(loaded_state.steps)}")
        print(f"  Final response: {loaded_state.response}")

    # 4. Save approved case summary to case history (Task 4)
    print("\n[Step 4] Saving approved case summary (Task 4 Privacy Rules)...")
    summary = save_case_summary(
        {
            "case_id": loaded_state.run_id,
            "student_id": loaded_state.student_id,
            "category": "Timetable Query",
            "summary": "Student asked for BSE4104 timetable schedule.",
            "status": "completed",
            "action_taken": "Provided lecture room and hours.",
            "ticket_id": None,
        }
    )
    print(f"  Case summary saved: case_id={summary.case_id}, category={summary.category}")

    # Test rejection of raw chat transcripts / PII
    print("\n  Testing privacy enforcement: attempting to store raw chat transcript...")
    try:
        save_case_summary(
            {
                "case_id": "ILLEGAL-01",
                "student_id": "2200701999",
                "category": "Admissions",
                "summary": "Illegal data attempt",
                "status": "completed",
                "action_taken": "None",
                "raw_transcript": [{"role": "user", "content": "My private raw chat..."}],
            }
        )
    except PrivacyViolationError as exc:
        print(f"  [REJECTED AS EXPECTED] {exc}")

    # 5. Retrieve student case history
    print(f"\n[Step 5] Querying case history for student {state.student_id}...")
    history = get_case_history(state.student_id)
    print(f"  Found {len(history)} past case(s):")
    for case in history:
        print(f"   - Case {case.case_id}: {case.category} [{case.status}] - {case.summary}")

    # 6. Verify audit traces
    print("\n[Step 6] Inspecting memory audit traces...")
    traces = get_memory_traces(key=state.run_id)
    print(f"  Captured {len(traces)} memory trace(s) for run_id {state.run_id}:")
    for t in traces[:5]:
        print(f"   [{t.timestamp}] {t.operation:<6} {t.store:<14} status={t.status:<7} details={t.details}")

    print("\n" + "=" * 70)
    print("ALL STATE STORE & MEMORY CHECKS COMPLETED SUCCESSFULLY")
    print("=" * 70)


if __name__ == "__main__":
    run_demo()
