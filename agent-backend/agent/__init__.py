"""Agent package exports."""

from agent.case_history import (
    CaseSummary,
    PrivacyViolationError,
    delete_case_history,
    get_case_history,
    save_case_summary,
)
from agent.contract import (
    AGENT_GOAL,
    TERMINAL_STATUSES,
    AgentStatus,
    AgentTaskContract,
    build_contract,
)
from agent.orchestrator import run_agent
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
from agent.traces import (
    MemoryTraceRecord,
    clear_memory_traces,
    get_memory_traces,
    log_memory_trace,
)

__all__ = [
    "run_agent",
    "AgentTaskContract",
    "AgentStatus",
    "TERMINAL_STATUSES",
    "AGENT_GOAL",
    "build_contract",
    "AgentState",
    "AgentStep",
    "AgentStage",
    "InvalidStateTransitionError",
    "validate_status_transition",
    "validate_stage_transition",
    "save_session_state",
    "get_session_state",
    "delete_session_state",
    "list_session_states",
    "save_case_summary",
    "get_case_history",
    "delete_case_history",
    "CaseSummary",
    "PrivacyViolationError",
    "log_memory_trace",
    "get_memory_traces",
    "clear_memory_traces",
    "MemoryTraceRecord",
]
