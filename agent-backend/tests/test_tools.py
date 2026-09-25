"""Unit and integration tests for Week 4 tools.

Tests cover:
- Purpose, input schema, output schema for all 3 tools
- Authorization verification and unauthorized rejection
- Failure behavior: missing/invalid parameters, non-existent cases, service handling
- Tool Registry cataloging and JSON schema export
- FastAPI endpoint endpoints (/api/v1/tools and /api/v1/tools/execute)
"""

from fastapi.testclient import TestClient
import pytest

from main import app
from tools import (
    CheckTimetableInput,
    CheckTimetableOutput,
    CheckTimetableTool,
    CreateSupportTicketTool,
    CreateTicketInput,
    CreateTicketOutput,
    GetCaseStatusInput,
    GetCaseStatusOutput,
    GetCaseStatusTool,
    TicketCategory,
    TicketPriority,
    get_tool_registry,
)

client = TestClient(app)


# ---------------------------------------------------------------------------
# Tool 1: CreateSupportTicketTool Tests
# ---------------------------------------------------------------------------
def test_create_ticket_tool_success() -> None:
    tool = CreateSupportTicketTool()
    raw_input = {
        "student_id": "2100701234",
        "category": TicketCategory.ACADEMIC_REGISTRAR.value,
        "subject": "Missing Exam Grade for BSE4104",
        "description": "I sat for the BSE4104 final examination but my grade is missing on the portal.",
        "priority": TicketPriority.HIGH.value,
        "auth_token": "valid-student-token-123",
    }
    result = tool.execute(raw_input)

    assert isinstance(result, CreateTicketOutput)
    assert result.success is True
    assert result.status == "CREATED"
    assert result.ticket_id is not None
    assert result.ticket_id.startswith("TICK-2026-")
    assert result.assigned_department == "Academic Registrar Department"
    assert result.error is None


def test_create_ticket_tool_missing_or_blank_parameter() -> None:
    tool = CreateSupportTicketTool()
    raw_input = {
        "student_id": "  ",  # Blank
        "category": TicketCategory.ACADEMIC_REGISTRAR.value,
        "subject": "Missing Grade",
        "description": "Short description for test",
        "auth_token": "valid-token",
    }
    result = tool.execute(raw_input)

    assert result.success is False
    assert result.status == "INVALID_INPUT"
    assert "VALIDATION_ERROR" in result.error


def test_create_ticket_tool_unauthorized() -> None:
    tool = CreateSupportTicketTool()
    raw_input = {
        "student_id": "2100701234",
        "category": TicketCategory.FINANCIAL_AID.value,
        "subject": "Tuition Verification Issue",
        "description": "Tuition receipt has not cleared on student portal after 3 days.",
        "auth_token": "unauthorized",
    }
    result = tool.execute(raw_input)

    assert result.success is False
    assert result.status == "UNAUTHORIZED"
    assert "AUTH_DENIED" in result.error


# ---------------------------------------------------------------------------
# Tool 2: GetCaseStatusTool Tests
# ---------------------------------------------------------------------------
def test_get_case_status_tool_success() -> None:
    tool = GetCaseStatusTool()
    raw_input = {
        "case_id": "TICK-2026-1001",
        "student_id": "2100701234",
        "auth_token": "valid-student-token",
    }
    result = tool.execute(raw_input)

    assert isinstance(result, GetCaseStatusOutput)
    assert result.success is True
    assert result.case_id == "TICK-2026-1001"
    assert result.status == "UNDER_REVIEW"
    assert result.assigned_officer is not None
    assert len(result.notes) > 0


def test_get_case_status_tool_not_found() -> None:
    tool = GetCaseStatusTool()
    raw_input = {
        "case_id": "TICK-2026-9999",  # Non-existent
        "student_id": "2100701234",
        "auth_token": "valid-token",
    }
    result = tool.execute(raw_input)

    assert result.success is False
    assert result.status == "NOT_FOUND"
    assert result.error == "CASE_NOT_FOUND"


def test_get_case_status_tool_ownership_mismatch_unauthorized() -> None:
    tool = GetCaseStatusTool()
    raw_input = {
        "case_id": "TICK-2026-1001",  # Belongs to 2100701234
        "student_id": "2100709999",  # Different student attempting unauthorized access
        "auth_token": "student-token-9999",
    }
    result = tool.execute(raw_input)

    assert result.success is False
    assert result.status == "UNAUTHORIZED"
    assert "AUTH_DENIED" in result.error


# ---------------------------------------------------------------------------
# Tool 3: CheckTimetableTool Tests
# ---------------------------------------------------------------------------
def test_check_timetable_tool_success() -> None:
    tool = CheckTimetableTool()
    raw_input = {
        "student_id": "2100701234",
        "course_code": "BSE4104",
        "semester": "2026/2027-SEM1",
        "auth_token": "valid-token",
    }
    result = tool.execute(raw_input)

    assert isinstance(result, CheckTimetableOutput)
    assert result.success is True
    assert result.total_found > 0
    assert result.entries[0].course_code == "BSE4104"


def test_check_timetable_tool_no_entries_found() -> None:
    tool = CheckTimetableTool()
    raw_input = {
        "student_id": "2100701234",
        "course_code": "NONEXISTENT999",
        "auth_token": "valid-token",
    }
    result = tool.execute(raw_input)

    assert result.success is True
    assert result.total_found == 0
    assert result.entries == []
    assert "No published timetable entries found" in result.message


def test_check_timetable_tool_unauthorized() -> None:
    tool = CheckTimetableTool()
    raw_input = {
        "student_id": "2100701234",
        "course_code": "BSE4104",
        "auth_token": "expired",
    }
    result = tool.execute(raw_input)

    assert result.success is False
    assert result.status if hasattr(result, "status") else True
    assert "AUTH_DENIED" in result.error


# ---------------------------------------------------------------------------
# Registry and Schema Tests
# ---------------------------------------------------------------------------
def test_tool_registry_and_json_schemas() -> None:
    registry = get_tool_registry()
    tools = registry.list_tools()

    assert len(tools) == 4
    tool_names = {t.name for t in tools}
    assert tool_names == {
        "create_support_ticket",
        "get_case_status",
        "check_timetable",
        "submit_grade_appeal",
    }

    schemas = registry.get_all_json_schemas()
    assert len(schemas) == 4
    for schema in schemas:
        assert schema["type"] == "function"
        assert "name" in schema["function"]
        assert "description" in schema["function"]
        assert "parameters" in schema["function"]


# ---------------------------------------------------------------------------
# FastAPI API Endpoint Tests
# ---------------------------------------------------------------------------
def test_api_list_tools() -> None:
    response = client.get("/api/v1/tools")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 4
    names = [item["name"] for item in data]
    assert "create_support_ticket" in names
    assert "get_case_status" in names
    assert "check_timetable" in names
    assert "submit_grade_appeal" in names



def test_api_execute_tool_endpoint_success() -> None:
    payload = {
        "tool_name": "create_support_ticket",
        "parameters": {
            "student_id": "2100701234",
            "category": TicketCategory.IT_SUPPORT.value,
            "subject": "MUELE Portal Login Failure",
            "description": "Student cannot access MUELE portal despite valid password reset.",
            "auth_token": "valid-token-student",
        },
    }
    response = client.post("/api/v1/tools/execute", json=payload)
    assert response.status_code == 200
    res_json = response.json()
    assert res_json["success"] is True
    assert res_json["status"] == "CREATED"
    assert res_json["assigned_department"] == "DICTS IT Helpdesk"


def test_api_execute_tool_endpoint_not_found() -> None:
    payload = {
        "tool_name": "unknown_tool",
        "parameters": {},
    }
    response = client.post("/api/v1/tools/execute", json=payload)
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]
