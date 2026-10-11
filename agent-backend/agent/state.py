"""Task 1: Agent State Model and Transition Validation.

Defines the explicit session-state object, the 6-stage cognitive agent lifecycle
(Sense -> Context -> Plan -> Act -> Observe -> Re-plan), the run terminal statuses,
and transition validation rules that strictly reject disallowed transitions.
"""

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Literal
import uuid

from agent.contract import TERMINAL_STATUSES, AgentStatus
from rag.context_builder import Source

Decision = Literal["tool_call", "final_answer", "stop", "error"]


class AgentStage(str, Enum):
    """The 6-stage cognitive loop phases plus initialized and terminal states."""

    INITIALIZED = "initialized"
    SENSE = "sense"
    CONTEXT = "context"
    PLAN = "plan"
    ACT = "act"
    OBSERVE = "observe"
    REPLAN = "replan"
    TERMINAL = "terminal"


class InvalidStateTransitionError(ValueError):
    """Raised when an attempted transition is rejected by the Task 1 state model."""

    def __init__(self, current_state: str, target_state: str, reason: str | None = None) -> None:
        msg = f"Invalid state transition: cannot transition from '{current_state}' to '{target_state}'."
        if reason:
            msg += f" Reason: {reason}"
        super().__init__(msg)
        self.current_state = current_state
        self.target_state = target_state
        self.reason = reason


# Task 1: Explicit mapping of allowed high-level status transitions.
# Terminal states are immutable sinks: once reached, no further transitions are allowed.
ALLOWED_STATUS_TRANSITIONS: dict[str, frozenset[str]] = {
    "initialized": frozenset({"running"}),
    "running": frozenset(
        {
            "running",
            "completed",
            "human_approval_required",
            "max_iterations_reached",
            "max_tool_calls_reached",
            "tool_not_approved",
            "llm_error",
        }
    ),
    "completed": frozenset(),
    "human_approval_required": frozenset(),
    "max_iterations_reached": frozenset(),
    "max_tool_calls_reached": frozenset(),
    "tool_not_approved": frozenset(),
    "llm_error": frozenset(),
}

# Task 1: Explicit mapping of allowed cognitive lifecycle stage transitions.
ALLOWED_STAGE_TRANSITIONS: dict[AgentStage, frozenset[AgentStage]] = {
    AgentStage.INITIALIZED: frozenset({AgentStage.SENSE, AgentStage.TERMINAL}),
    AgentStage.SENSE: frozenset({AgentStage.CONTEXT, AgentStage.TERMINAL}),
    AgentStage.CONTEXT: frozenset({AgentStage.PLAN, AgentStage.TERMINAL}),
    AgentStage.PLAN: frozenset({AgentStage.ACT, AgentStage.TERMINAL}),
    AgentStage.ACT: frozenset({AgentStage.OBSERVE, AgentStage.TERMINAL}),
    AgentStage.OBSERVE: frozenset({AgentStage.REPLAN, AgentStage.TERMINAL}),
    AgentStage.REPLAN: frozenset({AgentStage.PLAN, AgentStage.TERMINAL}),
    AgentStage.TERMINAL: frozenset(),
}


def validate_status_transition(current_status: str, target_status: str) -> None:
    """Validate status transition against Task 1 rules; raise InvalidStateTransitionError if rejected."""
    if current_status not in ALLOWED_STATUS_TRANSITIONS:
        raise InvalidStateTransitionError(
            current_status, target_status, f"Current status '{current_status}' is not a recognized state."
        )

    allowed = ALLOWED_STATUS_TRANSITIONS[current_status]
    if target_status not in allowed:
        if current_status in TERMINAL_STATUSES:
            reason = f"State '{current_status}' is terminal and cannot transition to any other state."
        elif target_status not in ALLOWED_STATUS_TRANSITIONS and target_status not in TERMINAL_STATUSES:
            reason = f"Target status '{target_status}' is an unknown status."
        else:
            reason = f"Transition not allowed by state contract. Allowed from '{current_status}': {sorted(list(allowed))}."
        raise InvalidStateTransitionError(current_status, target_status, reason)


def validate_stage_transition(current_stage: AgentStage, target_stage: AgentStage) -> None:
    """Validate stage transition against Task 1 lifecycle rules; raise InvalidStateTransitionError if rejected."""
    if current_stage not in ALLOWED_STAGE_TRANSITIONS:
        raise InvalidStateTransitionError(
            str(current_stage), str(target_stage), f"Stage '{current_stage}' is not a valid lifecycle stage."
        )

    allowed = ALLOWED_STAGE_TRANSITIONS[current_stage]
    if target_stage not in allowed:
        if current_stage == AgentStage.TERMINAL:
            reason = "Lifecycle is already at 'terminal' and cannot transition back to an active phase."
        else:
            reason = (
                f"Transition not allowed by cognitive loop. "
                f"Expected next stage from '{current_stage.value}' is one of {[s.value for s in allowed]}."
            )
        raise InvalidStateTransitionError(str(current_stage.value), str(target_stage.value), reason)


@dataclass
class AgentStep:
    iteration: int
    decision: Decision
    tool_name: str | None = None
    tool_arguments: dict | None = None
    tool_result: dict | None = None
    observation: str | None = None
    error: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class AgentState:
    """The session-state object for a single agent episode, updated at each step."""

    message: str
    run_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    student_id: str = "anonymous"
    status: AgentStatus = "running"
    stage: AgentStage = AgentStage.INITIALIZED
    plan: str = ""
    iteration_count: int = 0
    tool_call_count: int = 0
    steps: list[AgentStep] = field(default_factory=list)
    sources: list[Source] = field(default_factory=list)
    drafted_ticket_ids: list[str] = field(default_factory=list)
    response: str = ""

    def transition_to(self, new_status: AgentStatus) -> "AgentState":
        """Attempt to transition run status. Rejects invalid transitions per Task 1."""
        validate_status_transition(self.status, new_status)
        self.status = new_status
        if new_status in TERMINAL_STATUSES:
            self.stage = AgentStage.TERMINAL
        return self

    def transition_stage(self, new_stage: AgentStage | str) -> "AgentStage":
        """Attempt to transition cognitive loop stage. Rejects invalid transitions per Task 1."""
        stage_enum = AgentStage(new_stage) if isinstance(new_stage, str) else new_stage
        validate_stage_transition(self.stage, stage_enum)
        self.stage = stage_enum
        return self.stage

    def stop(self, status: AgentStatus, response: str) -> "AgentState":
        """Transition to terminal status and record final response."""
        self.transition_to(status)
        self.response = response
        return self

    def add_step(self, step: AgentStep) -> None:
        """Append an execution step to the run trace."""
        self.steps.append(step)

    def to_dict(self) -> dict:
        """Serialize state object to dictionary."""
        return {
            "run_id": self.run_id,
            "student_id": self.student_id,
            "message": self.message,
            "status": self.status,
            "stage": self.stage.value if isinstance(self.stage, AgentStage) else str(self.stage),
            "plan": self.plan,
            "iteration_count": self.iteration_count,
            "tool_call_count": self.tool_call_count,
            "steps": [s.to_dict() for s in self.steps],
            "sources": [
                {"document_id": s.document_id, "document": s.document, "page": s.page}
                for s in self.sources
            ],
            "drafted_ticket_ids": list(self.drafted_ticket_ids),
            "response": self.response,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "AgentState":
        """Deserialize dictionary back to AgentState object."""
        steps = [
            AgentStep(
                iteration=s["iteration"],
                decision=s["decision"],
                tool_name=s.get("tool_name"),
                tool_arguments=s.get("tool_arguments"),
                tool_result=s.get("tool_result"),
                observation=s.get("observation"),
                error=s.get("error"),
            )
            for s in data.get("steps", [])
        ]
        sources = [
            Source(
                document_id=src["document_id"],
                document=src["document"],
                page=src["page"],
            )
            for src in data.get("sources", [])
        ]
        state = cls(
            message=data.get("message", ""),
            run_id=data.get("run_id", str(uuid.uuid4())),
            student_id=data.get("student_id", "anonymous"),
            status=data.get("status", "running"),
            stage=AgentStage(data.get("stage", AgentStage.INITIALIZED.value)),
            plan=data.get("plan", ""),
            iteration_count=data.get("iteration_count", 0),
            tool_call_count=data.get("tool_call_count", 0),
            steps=steps,
            sources=sources,
            drafted_ticket_ids=data.get("drafted_ticket_ids", []),
            response=data.get("response", ""),
        )
        return state
