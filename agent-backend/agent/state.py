"""Per-run agent state. Lives for one request only - no memory across runs."""

import uuid
from dataclasses import dataclass, field
from typing import Literal

from agent.contract import AgentStatus
from rag.context_builder import Source

Decision = Literal["tool_call", "final_answer", "stop", "error"]


@dataclass
class AgentStep:
    iteration: int
    decision: Decision
    tool_name: str | None = None
    tool_arguments: dict | None = None
    tool_result: dict | None = None
    observation: str | None = None
    error: str | None = None


@dataclass
class AgentState:
    message: str
    run_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: AgentStatus = "running"
    plan: str = ""
    iteration_count: int = 0
    tool_call_count: int = 0
    steps: list[AgentStep] = field(default_factory=list)
    sources: list[Source] = field(default_factory=list)
    drafted_ticket_ids: list[str] = field(default_factory=list)
    response: str = ""

    def stop(self, status: AgentStatus, response: str) -> "AgentState":
        self.status = status
        self.response = response
        return self
