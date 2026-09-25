"""Tool Registry for tool registration, cataloging, and execution.

Provides centralized management of all active tools and exposes function schemas
for LLM tool/function calling in Week 4 & Week 5.
"""

from typing import Any
from pydantic import BaseModel

from tools.appeal_tool import SubmitGradeAppealTool
from tools.base import BaseTool
from tools.case_tool import GetCaseStatusTool
from tools.ticket_tool import CreateSupportTicketTool
from tools.timetable_tool import CheckTimetableTool


class ToolRegistry:
    """Registry managing available application tools."""

    def __init__(self) -> None:
        self._tools: dict[str, BaseTool[Any, Any]] = {}
        # Register standard Week 4 tools
        self.register(CreateSupportTicketTool())
        self.register(GetCaseStatusTool())
        self.register(CheckTimetableTool())
        self.register(SubmitGradeAppealTool())


    def register(self, tool: BaseTool[Any, Any]) -> None:
        """Register a new tool instance."""
        self._tools[tool.name] = tool

    def get_tool(self, name: str) -> BaseTool[Any, Any] | None:
        """Retrieve registered tool by name."""
        return self._tools.get(name)

    def list_tools(self) -> list[BaseTool[Any, Any]]:
        """Return list of all registered tools."""
        return list(self._tools.values())

    def get_all_json_schemas(self) -> list[dict[str, Any]]:
        """Export JSON schemas for OpenAI/Groq function calling."""
        return [tool.get_json_schema() for tool in self._tools.values()]

    def execute_tool(self, tool_name: str, raw_input: dict[str, Any]) -> BaseModel:
        """Find tool by name and execute it safely with failure containment."""
        tool = self.get_tool(tool_name)
        if not tool:
            raise KeyError(f"Tool '{tool_name}' is not registered in the tool registry.")
        return tool.execute(raw_input)


# Global singleton instance
_registry_instance = ToolRegistry()


def get_tool_registry() -> ToolRegistry:
    return _registry_instance
