"""The Agent Task Contract (docs/agent-task-contract.md) as code.

Everything the agent loop is allowed to do - which tools, how many
iterations, how many tool executions, and which statuses end a run - is
read from an AgentTaskContract instance rather than scattered through
the loop, so the document and the enforcement can't drift apart.
"""

from dataclasses import dataclass
from typing import Literal

from config import Settings
from tools.registry import TOOL_REGISTRY

AgentStatus = Literal[
    "running",
    "completed",
    "human_approval_required",
    "max_iterations_reached",
    "max_tool_calls_reached",
    "tool_not_approved",
    "llm_error",
]

TERMINAL_STATUSES: frozenset[str] = frozenset(
    {
        "completed",
        "human_approval_required",
        "max_iterations_reached",
        "max_tool_calls_reached",
        "tool_not_approved",
        "llm_error",
    }
)

AGENT_GOAL = (
    "Resolve one student-support request per run: answer from retrieved policy "
    "evidence, look up the timetable, or draft a support ticket for staff "
    "follow-up - never approve, submit, or decide anything on a human's behalf."
)


@dataclass(frozen=True)
class AgentTaskContract:
    goal: str
    approved_tools: frozenset[str]
    max_iterations: int
    max_tool_calls: int

    def is_approved_tool(self, tool_name: str) -> bool:
        return tool_name in self.approved_tools


def build_contract(settings: Settings) -> AgentTaskContract:
    # The approved set is the Week 4 allow-list itself: the agent can never be
    # granted a tool the registry doesn't already validate and authorize.
    return AgentTaskContract(
        goal=AGENT_GOAL,
        approved_tools=frozenset(TOOL_REGISTRY),
        max_iterations=settings.agent_max_iterations,
        max_tool_calls=settings.max_tool_calls,
    )
