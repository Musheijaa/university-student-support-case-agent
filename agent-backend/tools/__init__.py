"""Tools package for University Student Support Case Agent.

Provides deterministic, authorized tools with strict input/output schemas
and explicit failure handling for Week 4 requirements.
"""

from tools.appeal_tool import SubmitGradeAppealTool
from tools.approval import ApprovalManager, get_approval_manager
from tools.base import BaseTool
from tools.case_tool import GetCaseStatusTool
from tools.registry import ToolRegistry, get_tool_registry
from tools.schemas import (
    AppealType,
    ApprovalDecision,
    ApprovalDecisionInput,
    ApprovalExecutionResult,
    ApprovalRequest,
    ApprovalStatus,
    CheckTimetableInput,
    CheckTimetableOutput,
    CreateApprovalInput,
    CreateTicketInput,
    CreateTicketOutput,
    GetCaseStatusInput,
    GetCaseStatusOutput,
    SubmitGradeAppealInput,
    SubmitGradeAppealOutput,
    TicketCategory,
    TicketPriority,
    TimetableEntry,
)
from tools.ticket_tool import CreateSupportTicketTool
from tools.timetable_tool import CheckTimetableTool

__all__ = [
    "BaseTool",
    "CreateSupportTicketTool",
    "GetCaseStatusTool",
    "CheckTimetableTool",
    "SubmitGradeAppealTool",
    "CreateTicketInput",
    "CreateTicketOutput",
    "GetCaseStatusInput",
    "GetCaseStatusOutput",
    "CheckTimetableInput",
    "CheckTimetableOutput",
    "SubmitGradeAppealInput",
    "SubmitGradeAppealOutput",
    "AppealType",
    "TicketCategory",
    "TicketPriority",
    "TimetableEntry",
    "ToolRegistry",
    "get_tool_registry",
    "ApprovalManager",
    "get_approval_manager",
    "ApprovalStatus",
    "ApprovalDecision",
    "ApprovalRequest",
    "CreateApprovalInput",
    "ApprovalDecisionInput",
    "ApprovalExecutionResult",
]

