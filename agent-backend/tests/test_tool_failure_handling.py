"""Failure-handling tests for Week 4 tools.

Covers the four required failure scenarios required by the Week 4 brief:
  1. Missing required parameters          → TestMissingRequiredParameters
  2. Unavailable services / dependencies   → TestUnavailableServices
  3. Unexpected tool responses            → TestUnexpectedToolResponses
  4. Unauthorized requests                → TestUnauthorizedRequests

These tests exercise the dispatch layer (``tools/registry.py``), the
individual tool executors (``tools/tickets.py``, ``tools/timetable.py``),
the bounded tool-calling loop / API layer (``llm/service.py``, ``main.py``)
— never the real Groq API.  The LLM is mocked with scripted fake responses.
"""

import json
import sqlite3

import pytest
from fastapi.testclient import TestClient

from auth import Actor
from config import Settings
from llm import service as service_module
from llm.client import GroqClient, LLMConfigurationError, LLMRequestError
from tools import tickets
from tools.registry import TOOL_REGISTRY, ToolContext, ToolSpec, dispatch_tool_call
from tools.schemas import (
    CheckTimetableInput,
    CheckTimetableOutput,
    CreateSupportTicketInput,
    CreateSupportTicketOutput,
)

import main as main_module


STUDENT = Actor(role="student", user_id="s1")
STAFF = Actor(role="staff", user_id="staff1")
GUEST = Actor(role="guest", user_id="anon")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ctx(tmp_path, sessions=None):
    """Build a ToolContext with a valid (possibly empty) timetable file."""
    data_path = tmp_path / "timetable.json"
    data_path.write_text(json.dumps({"sessions": sessions or []}))
    return ToolContext(
        timetable_data_path=str(data_path),
        tickets_db_path=str(tmp_path / "tickets.db"),
    )


def _settings(tmp_path, max_tool_calls=3):
    return Settings(
        groq_api_key="test-key",
        timetable_data_path=str(tmp_path / "timetable.json"),
        tickets_db_path=str(tmp_path / "tickets.db"),
        max_tool_calls=max_tool_calls,
    )


def _write_timetable(tmp_path, sessions):
    (tmp_path / "timetable.json").write_text(json.dumps({"sessions": sessions}))


# Fake message classes — mirrors test_tool_calling_flow.py
class FakeFunction:
    def __init__(self, name, arguments):
        self.name = name
        self.arguments = arguments


class FakeToolCall:
    def __init__(self, call_id, name, arguments):
        self.id = call_id
        self.function = FakeFunction(name, arguments)


class FakeMessage:
    def __init__(self, content=None, tool_calls=None):
        self.content = content
        self.tool_calls = tool_calls or []


def _sequenced_create_completion(responses):
    """Return a fake create_completion that yields responses in order."""
    responses = list(responses)

    def fake(self, messages, tools=None, tool_choice=None):
        return responses.pop(0)

    return fake


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _no_real_retrieval(monkeypatch):
    """Isolate all tests from the real RAG index."""
    monkeypatch.setattr(
        service_module, "_retrieve_evidence", lambda message, settings: ("no evidence", [])
    )


api_client = TestClient(main_module.app)


# ===========================================================================
# Category 1: Missing required parameters
#   Tests that missing, empty, malformed, or oversized parameters are
#   rejected safely at the dispatch layer with clear validation errors.
# ===========================================================================

class TestMissingRequiredParameters:

    # -- check_timetable through dispatch_tool_call -------------------------

    def test_missing_param_001_check_timetable_empty_args(self, tmp_path):
        """MISSING-PARAM-001: check_timetable called with empty JSON object."""
        result = dispatch_tool_call("check_timetable", "{}", STUDENT, _ctx(tmp_path))
        assert result["success"] is False
        assert "Invalid input" in result["error"]
        assert "field required" in result["error"].lower()

    def test_missing_param_002_check_timetable_empty_course_code(self, tmp_path):
        """MISSING-PARAM-002: check_timetable with empty-string course_code."""
        result = dispatch_tool_call(
            "check_timetable",
            json.dumps({"course_code": ""}),
            STUDENT,
            _ctx(tmp_path),
        )
        assert result["success"] is False
        assert "Invalid input" in result["error"]

    def test_missing_param_003_check_timetable_whitespace_course_code(self, tmp_path):
        """MISSING-PARAM-003: check_timetable with whitespace-only course_code."""
        result = dispatch_tool_call(
            "check_timetable",
            json.dumps({"course_code": "   "}),
            STUDENT,
            _ctx(tmp_path),
        )
        assert result["success"] is False
        assert "Invalid input" in result["error"]

    def test_missing_param_004_check_timetable_malformed_course_code(self, tmp_path):
        """MISSING-PARAM-004: check_timetable with non-conforming course_code."""
        result = dispatch_tool_call(
            "check_timetable",
            json.dumps({"course_code": "B@r3!"}),
            STUDENT,
            _ctx(tmp_path),
        )
        assert result["success"] is False
        assert "Invalid input" in result["error"]

    def test_missing_param_005_check_timetable_invalid_date(self, tmp_path):
        """MISSING-PARAM-005: check_timetable with malformed ISO date."""
        result = dispatch_tool_call(
            "check_timetable",
            json.dumps({"course_code": "BSE4104", "date": "not-a-date"}),
            STUDENT,
            _ctx(tmp_path),
        )
        assert result["success"] is False
        assert "Invalid input" in result["error"]

    def test_missing_param_006_check_timetable_extra_unknown_fields(self, tmp_path):
        """MISSING-PARAM-006: unknown fields ignored (extra='ignore'), valid call succeeds."""
        result = dispatch_tool_call(
            "check_timetable",
            json.dumps({"course_code": "BSE4104", "drop_table": "yes"}),
            STUDENT,
            _ctx(tmp_path, sessions=[
                {"course_code": "BSE4104", "date": "2026-09-24",
                 "start_time": "10:00", "end_time": "12:00", "venue": "Room 204"},
            ]),
        )
        assert result["success"] is True
        assert "drop_table" not in result

    # -- create_support_ticket through dispatch_tool_call -------------------

    def test_missing_param_007_create_ticket_missing_category(self, tmp_path):
        """MISSING-PARAM-007: create_support_ticket with missing category."""
        args = json.dumps({"subject": "Portal issue", "description": "Can't log in"})
        result = dispatch_tool_call("create_support_ticket", args, STUDENT, _ctx(tmp_path))
        assert result["success"] is False
        assert "Invalid input" in result["error"]
        assert "field required" in result["error"].lower()

    def test_missing_param_008_create_ticket_missing_subject(self, tmp_path):
        """MISSING-PARAM-008: create_support_ticket with missing subject."""
        args = json.dumps({"category": "IT Support", "description": "Can't log in"})
        result = dispatch_tool_call("create_support_ticket", args, STUDENT, _ctx(tmp_path))
        assert result["success"] is False
        assert "Invalid input" in result["error"]

    def test_missing_param_009_create_ticket_missing_description(self, tmp_path):
        """MISSING-PARAM-009: create_support_ticket with missing description."""
        args = json.dumps({"category": "IT Support", "subject": "Portal issue"})
        result = dispatch_tool_call("create_support_ticket", args, STUDENT, _ctx(tmp_path))
        assert result["success"] is False
        assert "Invalid input" in result["error"]

    def test_missing_param_010_create_ticket_all_fields_missing(self, tmp_path):
        """MISSING-PARAM-010: create_support_ticket with completely empty arguments."""
        result = dispatch_tool_call("create_support_ticket", "{}", STUDENT, _ctx(tmp_path))
        assert result["success"] is False
        assert "Invalid input" in result["error"]

    def test_missing_param_011_create_ticket_invalid_category(self, tmp_path):
        """MISSING-PARAM-011: create_support_ticket with unrecognized category."""
        args = json.dumps({"category": "Bogus Category", "subject": "s", "description": "d"})
        result = dispatch_tool_call("create_support_ticket", args, STUDENT, _ctx(tmp_path))
        assert result["success"] is False
        assert "Invalid input" in result["error"]

    def test_missing_param_012_create_ticket_blank_subject(self, tmp_path):
        """MISSING-PARAM-012: create_support_ticket with whitespace-only subject."""
        args = json.dumps({"category": "IT Support", "subject": "   ", "description": "d"})
        result = dispatch_tool_call("create_support_ticket", args, STUDENT, _ctx(tmp_path))
        assert result["success"] is False
        assert "Invalid input" in result["error"]

    def test_missing_param_013_create_ticket_oversized_subject(self, tmp_path):
        """MISSING-PARAM-013: create_support_ticket with subject > 200 chars."""
        args = json.dumps({"category": "IT Support", "subject": "A" * 201, "description": "d"})
        result = dispatch_tool_call("create_support_ticket", args, STUDENT, _ctx(tmp_path))
        assert result["success"] is False
        assert "Invalid input" in result["error"]

    def test_missing_param_014_create_ticket_oversized_description(self, tmp_path):
        """MISSING-PARAM--014: create_support_ticket with description > 2000 chars."""
        args = json.dumps({
            "category": "IT Support",
            "subject": "s",
            "description": "D" * 2001,
        })
        result = dispatch_tool_call("create_support_ticket", args, STUDENT, _ctx(tmp_path))
        assert result["success"] is False
        assert "Invalid input" in result["error"]

    # -- End-to-end: missing params reported back through the tool loop -----

    def test_missing_param_015_end_to_end_missing_arg_reported_to_model(self, tmp_path):
        """MISSING-PARAM-015: tool-call flow surfaces validation error to the model."""
        _write_timetable(tmp_path, [])
        monkeypatch = pytest.MonkeyPatch()
        monkeypatch.setattr(
            GroqClient,
            "create_completion",
            _sequenced_create_completion([
                FakeMessage(
                    tool_calls=[FakeToolCall("call_1", "check_timetable", json.dumps({}))]
                ),
                FakeMessage(content="I need a course code to look that up."),
            ]),
        )
        try:
            result = service_module.get_student_support_response(
                "When is my class?", settings=_settings(tmp_path), actor=STUDENT
            )
            assert result.tool_calls[0].result["success"] is False
            assert "Invalid input" in result.tool_calls[0].result["error"]
            assert result.response == "I need a course code to look that up."
        finally:
            monkeypatch.undo()


# ===========================================================================
# Category 2: Unavailable services / dependencies
#   Tests that service failures (missing files, DB errors, timeouts,
#   malformed data) are caught and return controlled error messages.
# ===========================================================================

class TestUnavailableServices:

    # -- check_timetable service failures -----------------------------------

    def test_service_fail_001_timetable_file_missing(self, tmp_path):
        """SERVICE-FAIL-001: timetable file does not exist."""
        ctx = ToolContext(
            timetable_data_path=str(tmp_path / "missing.json"),
            tickets_db_path=str(tmp_path / "t.db"),
        )
        result = dispatch_tool_call(
            "check_timetable", json.dumps({"course_code": "BSE4104"}), STUDENT, ctx
        )
        assert result["success"] is False
        assert "temporarily unavailable" in result["error"]

    def test_service_fail_002_timetable_file_malformed_json(self, tmp_path):
        """SERVICE-FAIL-002: timetable file contains invalid JSON."""
        data_path = tmp_path / "timetable.json"
        data_path.write_text("{not valid json}")
        ctx = ToolContext(
            timetable_data_path=str(data_path),
            tickets_db_path=str(tmp_path / "t.db"),
        )
        result = dispatch_tool_call(
            "check_timetable", json.dumps({"course_code": "BSE4104"}), STUDENT, ctx
        )
        assert result["success"] is False
        assert "temporarily unavailable" in result["error"]

    def test_service_fail_003_timetable_file_missing_sessions_key(self, tmp_path):
        """SERVICE-FAIL-003: timetable JSON missing the 'sessions' key → KeyError caught."""
        data_path = tmp_path / "timetable.json"
        data_path.write_text(json.dumps({"unrelated_key": []}))
        ctx = ToolContext(
            timetable_data_path=str(data_path),
            tickets_db_path=str(tmp_path / "t.db"),
        )
        result = dispatch_tool_call(
            "check_timetable", json.dumps({"course_code": "BSE4104"}), STUDENT, ctx
        )
        assert result["success"] is False
        assert "temporarily unavailable" in result["error"]

    # -- create_support_ticket service failures -----------------------------

    def test_service_fail_004_ticket_db_path_nonexistent_dir(self, tmp_path):
        """SERVICE-FAIL-004: SQLite database in a non-existent directory."""
        ctx = ToolContext(
            timetable_data_path=str(tmp_path / "timetable.json"),
            tickets_db_path=str(tmp_path / "nonexistent" / "tickets.db"),
        )
        (tmp_path / "timetable.json").write_text(json.dumps({"sessions": []}))
        result = dispatch_tool_call(
            "create_support_ticket",
            json.dumps({"category": "IT Support", "subject": "s", "description": "d"}),
            STUDENT,
            ctx,
        )
        assert result["success"] is False
        assert "temporarily unavailable" in result["error"]

    def test_service_fail_005_ticket_db_sqlite_error(self, tmp_path, monkeypatch):
        """SERVICE-FAIL-005: SQLite OperationalError during ticket creation."""
        def broken_connect(_db_path):
            raise sqlite3.OperationalError("database is locked")

        monkeypatch.setattr(tickets, "_connect", broken_connect)

        result = dispatch_tool_call(
            "create_support_ticket",
            json.dumps({"category": "IT Support", "subject": "s", "description": "d"}),
            STUDENT,
            _ctx(tmp_path),
        )
        assert result["success"] is False
        assert "temporarily unavailable" in result["error"]

    def test_service_fail_006_executor_raises_generic_exception(self, tmp_path, monkeypatch):
        """SERVICE-FAIL-006: executor raises a non-standard Exception → caught, safe message."""
        def exploding_executor(input_data, ctx):
            raise RuntimeError("disk full — cannot write to disk")

        monkeypatch.setitem(
            TOOL_REGISTRY,
            "check_timetable",
            ToolSpec(
                input_model=CheckTimetableInput,
                output_model=CheckTimetableOutput,
                allowed_roles=frozenset({"student", "staff"}),
                executor=exploding_executor,
            ),
        )

        result = dispatch_tool_call(
            "check_timetable",
            json.dumps({"course_code": "BSE4104"}),
            STUDENT,
            _ctx(tmp_path),
        )
        assert result["success"] is False
        assert "unexpected error" in result["error"]

    # -- Provider / service-level failures in the tool-calling loop ----------

    def test_service_fail_007_provider_timeout_propagates_as_502(self, tmp_path, monkeypatch):
        """SERVICE-FAIL-007: Groq timeout during a tool-calling loop → HTTP 502."""
        _write_timetable(tmp_path, [])

        def fake_create(self, messages, tools=None, tool_choice=None):
            raise LLMRequestError("The model provider timed out. Please try again.")

        monkeypatch.setattr(GroqClient, "create_completion", fake_create)
        monkeypatch.setattr(service_module, "get_settings", lambda: _settings(tmp_path))

        response = api_client.post(
            "/api/v1/student-support",
            json={"message": "When is BSE4104?"},
            headers={"X-User-Role": "student"},
        )
        assert response.status_code == 502

    def test_service_fail_008_provider_config_error_propagates_as_503(self, tmp_path, monkeypatch):
        """SERVICE-FAIL-008: missing API key during tool-calling → HTTP 503."""
        def fake_init(self, api_key, model, timeout_seconds=20.0):
            raise LLMConfigurationError("GROQ_API_KEY is not configured.")

        monkeypatch.setattr(GroqClient, "__init__", fake_init)
        monkeypatch.setattr(service_module, "get_settings", lambda: _settings(tmp_path))

        response = api_client.post(
            "/api/v1/student-support",
            json={"message": "When is BSE4104?"},
            headers={"X-User-Role": "student"},
        )
        assert response.status_code == 503
        assert "GROQ_API_KEY" not in response.text


# ===========================================================================
# Category 3: Unexpected tool responses
#   Tests that malformed, incomplete, or invalid outputs from a tool
#   executor are validated and handled safely via output-schema validation.
# ===========================================================================

class TestUnexpectedToolResponses:

    def test_unexpected_resp_001_executor_returns_string(self, tmp_path, monkeypatch):
        """UNEXPECTED-RESP-001: executor returns a bare string, not a dict/model."""
        def bad_executor(input_data, ctx):
            return "I am not a valid output object"

        monkeypatch.setitem(
            TOOL_REGISTRY,
            "check_timetable",
            ToolSpec(
                input_model=CheckTimetableInput,
                output_model=CheckTimetableOutput,
                allowed_roles=frozenset({"student", "staff"}),
                executor=bad_executor,
            ),
        )

        result = dispatch_tool_call(
            "check_timetable",
            json.dumps({"course_code": "BSE4104"}),
            STUDENT,
            _ctx(tmp_path),
        )
        assert result["success"] is False
        assert "unexpected response" in result["error"]

    def test_unexpected_resp_002_executor_returns_dict_missing_required_field(self, tmp_path, monkeypatch):
        """UNEXPECTED-RESP-002: executor returns dict missing the 'success' field."""
        def bad_executor(input_data, ctx):
            return {"course_code": "BSE4104", "sessions": []}

        monkeypatch.setitem(
            TOOL_REGISTRY,
            "check_timetable",
            ToolSpec(
                input_model=CheckTimetableInput,
                output_model=CheckTimetableOutput,
                allowed_roles=frozenset({"student", "staff"}),
                executor=bad_executor,
            ),
        )

        result = dispatch_tool_call(
            "check_timetable",
            json.dumps({"course_code": "BSE4104"}),
            STUDENT,
            _ctx(tmp_path),
        )
        assert result["success"] is False
        assert "unexpected response" in result["error"]

    def test_unexpected_resp_003_executor_returns_none(self, tmp_path, monkeypatch):
        """UNEXPECTED-RESP-003: executor returns None."""
        def bad_executor(input_data, ctx):
            return None

        monkeypatch.setitem(
            TOOL_REGISTRY,
            "check_timetable",
            ToolSpec(
                input_model=CheckTimetableInput,
                output_model=CheckTimetableOutput,
                allowed_roles=frozenset({"student", "staff"}),
                executor=bad_executor,
            ),
        )

        result = dispatch_tool_call(
            "check_timetable",
            json.dumps({"course_code": "BSE4104"}),
            STUDENT,
            _ctx(tmp_path),
        )
        assert result["success"] is False
        assert "unexpected response" in result["error"]

    def test_unexpected_resp_004_executor_returns_dict_with_wrong_types(self, tmp_path, monkeypatch):
        """UNEXPECTED-RESP-004: executor returns dict with wrong field types."""
        def bad_executor(input_data, ctx):
            return {
                "success": "maybe",
                "ticket_id": 12345,
                "status": "UNKNOWN_STATE",
                "category": 999,
                "subject": 0,
                "error": None,
            }

        monkeypatch.setitem(
            TOOL_REGISTRY,
            "create_support_ticket",
            ToolSpec(
                input_model=CreateSupportTicketInput,
                output_model=CreateSupportTicketOutput,
                allowed_roles=frozenset({"student", "staff"}),
                executor=bad_executor,
            ),
        )

        result = dispatch_tool_call(
            "create_support_ticket",
            json.dumps({"category": "IT Support", "subject": "s", "description": "d"}),
            STUDENT,
            _ctx(tmp_path),
        )
        assert result["success"] is False
        assert "unexpected response" in result["error"]

    def test_unexpected_resp_005_executor_returns_malformed_json_string(self, tmp_path, monkeypatch):
        """UNEXPECTED-RESP-005: executor returns a non-JSON-parseable string."""
        def bad_executor(input_data, ctx):
            return '{"success": true, broken json}'

        monkeypatch.setitem(
            TOOL_REGISTRY,
            "create_support_ticket",
            ToolSpec(
                input_model=CreateSupportTicketInput,
                output_model=CreateSupportTicketOutput,
                allowed_roles=frozenset({"student", "staff"}),
                executor=bad_executor,
            ),
        )

        result = dispatch_tool_call(
            "create_support_ticket",
            json.dumps({"category": "IT Support", "subject": "s", "description": "d"}),
            STUDENT,
            _ctx(tmp_path),
        )
        assert result["success"] is False
        assert "unexpected response" in result["error"]


# ===========================================================================
# Category 4: Unauthorized requests
#   Tests that callers with disallowed roles cannot invoke tools or
#   access endpoints they are not permitted to.
# ===========================================================================

class TestUnauthorizedRequests:

    # -- dispatch-level authorization ---------------------------------------

    def test_unauth_001_unknown_role_rejected_at_dispatch(self, tmp_path):
        """UNAUTH-001: role that is not student/staff/guest → rejected at dispatch."""
        admin = Actor(role="guest", user_id="admin")
        result = dispatch_tool_call(
            "check_timetable",
            json.dumps({"course_code": "BSE4104"}),
            admin,
            _ctx(tmp_path),
        )
        assert result["success"] is False
        assert "not authorized" in result["error"]

    def test_unauth_002_guest_cannot_create_ticket_through_dispatch(self, tmp_path):
        """UNAUTH-002: guest role rejected for create_support_ticket at dispatch."""
        result = dispatch_tool_call(
            "create_support_ticket",
            json.dumps({"category": "IT Support", "subject": "s", "description": "d"}),
            GUEST,
            _ctx(tmp_path),
        )
        assert result["success"] is False
        assert "not authorized" in result["error"]
        # Verify no ticket was actually created
        record = tickets.get_ticket("DRAFT-001", db_path=str(tmp_path / "tickets.db"))
        assert record is None

    def test_unauth_003_guest_rejected_for_both_tools(self, tmp_path):
        """UNAUTH-003: guest is unauthorized for both registered tools at dispatch."""
        for tool_name, args in [
            ("check_timetable", json.dumps({"course_code": "BSE4104"})),
            ("create_support_ticket", json.dumps({"category": "IT Support", "subject": "s", "description": "d"})),
        ]:
            result = dispatch_tool_call(tool_name, args, GUEST, _ctx(tmp_path))
            assert result["success"] is False
            assert "not authorized" in result["error"], f"Failed for {tool_name}"

    # -- end-to-end: unauthorized actor in the tool-calling loop ------------

    def test_unauth_004_guest_actor_in_tool_calling_loop(self, tmp_path, monkeypatch):
        """UNAUTH-004: guest actor triggers a tool call → error reported, no side effects."""
        _write_timetable(tmp_path, [])
        monkeypatch.setattr(
            GroqClient,
            "create_completion",
            _sequenced_create_completion([
                FakeMessage(
                    tool_calls=[FakeToolCall("call_1", "check_timetable", json.dumps({"course_code": "BSE4104"}))]
                ),
                FakeMessage(content="I couldn't check that for you."),
            ]),
        )

        result = service_module.get_student_support_response(
            "When is BSE4104?", settings=_settings(tmp_path), actor=GUEST
        )
        assert result.tool_calls[0].result["success"] is False
        assert "not authorized" in result.tool_calls[0].result["error"]
        assert "couldn't check" in result.response.lower()

    # -- API-level authorization --------------------------------------------

    def test_unauth_005_invalid_role_header_defaults_to_guest(self, tmp_path, monkeypatch):
        """UNAUTH-005: unknown X-User-Role value defaults to 'guest' and is rejected."""
        _write_timetable(tmp_path, [
            {"course_code": "BSE4104", "date": "2026-09-24", "start_time": "10:00",
             "end_time": "12:00", "venue": "Room 204"},
        ])

        monkeypatch.setattr(
            GroqClient,
            "create_completion",
            _sequenced_create_completion([
                FakeMessage(tool_calls=[
                    FakeToolCall("call_1", "check_timetable", json.dumps({"course_code": "BSE4104"}))
                ]),
                FakeMessage(content="I couldn't check that for you."),
            ]),
        )
        monkeypatch.setattr(service_module, "get_settings", lambda: _settings(tmp_path))

        response = api_client.post(
            "/api/v1/student-support",
            json={"message": "When is BSE4104?"},
            headers={"X-User-Role": "admin"},
        )
        assert response.status_code == 200
        tool_calls = response.json()["tool_calls"]
        assert tool_calls[0]["result"]["success"] is False
        assert "not authorized" in tool_calls[0]["result"]["error"]

    def test_unauth_006_student_cannot_approve_ticket(self, tmp_path, monkeypatch):
        """UNAUTH-006: student attempting to approve → HTTP 403, no state change."""
        db_path = str(tmp_path / "tickets.db")
        settings = Settings(tickets_db_path=db_path)
        monkeypatch.setattr(main_module, "get_settings", lambda: settings)
        result = tickets.create_support_ticket(
            CreateSupportTicketInput(category="IT Support", subject="s", description="d"),
            db_path=db_path,
        )

        response = api_client.post(
            f"/api/v1/support-tickets/{result.ticket_id}/approve",
            headers={"X-User-Role": "student"},
        )
        assert response.status_code == 403
        record = tickets.get_ticket(result.ticket_id, db_path=db_path)
        assert record.status == "PENDING_APPROVAL"

    def test_unauth_007_student_cannot_reject_ticket(self, tmp_path, monkeypatch):
        """UNAUTH-007: student attempting to reject → HTTP 403, no state change."""
        db_path = str(tmp_path / "tickets.db")
        settings = Settings(tickets_db_path=db_path)
        monkeypatch.setattr(main_module, "get_settings", lambda: settings)
        result = tickets.create_support_ticket(
            CreateSupportTicketInput(category="IT Support", subject="s", description="d"),
            db_path=db_path,
        )

        response = api_client.post(
            f"/api/v1/support-tickets/{result.ticket_id}/reject",
            headers={"X-User-Role": "student"},
        )
        assert response.status_code == 403
        record = tickets.get_ticket(result.ticket_id, db_path=db_path)
        assert record.status == "PENDING_APPROVAL"

    def test_unauth_008_guest_cannot_approve_or_reject(self, tmp_path, monkeypatch):
        """UNAUTH-008: guest attempting to approve or reject → HTTP 403."""
        db_path = str(tmp_path / "tickets.db")
        settings = Settings(tickets_db_path=db_path)
        monkeypatch.setattr(main_module, "get_settings", lambda: settings)
        result = tickets.create_support_ticket(
            CreateSupportTicketInput(category="IT Support", subject="s", description="d"),
            db_path=db_path,
        )

        approve_resp = api_client.post(
            f"/api/v1/support-tickets/{result.ticket_id}/approve",
            headers={"X-User-Role": "guest"},
        )
        assert approve_resp.status_code == 403

        reject_resp = api_client.post(
            f"/api/v1/support-tickets/{result.ticket_id}/reject",
            headers={"X-User-Role": "guest"},
        )
        assert reject_resp.status_code == 403

        record = tickets.get_ticket(result.ticket_id, db_path=db_path)
        assert record.status == "PENDING_APPROVAL"

    def test_unauth_009_missing_role_header_defaults_to_student_rejected(self, tmp_path, monkeypatch):
        """UNAUTH-009: no X-User-Role header → defaults to 'student' → rejected for approval."""
        db_path = str(tmp_path / "tickets.db")
        settings = Settings(tickets_db_path=db_path)
        monkeypatch.setattr(main_module, "get_settings", lambda: settings)
        result = tickets.create_support_ticket(
            CreateSupportTicketInput(category="IT Support", subject="s", description="d"),
            db_path=db_path,
        )

        response = api_client.post(
            f"/api/v1/support-tickets/{result.ticket_id}/approve",
        )
        assert response.status_code == 403
        record = tickets.get_ticket(result.ticket_id, db_path=db_path)
        assert record.status == "PENDING_APPROVAL"

    # -- Authorized roles still work (contrast tests) -----------------------

    def test_unauth_010_staff_can_approve_ticket_unauthorized_context(self, tmp_path, monkeypatch):
        """UNAUTH-010: staff role IS authorized for approve (contrast/positive test)."""
        db_path = str(tmp_path / "tickets.db")
        settings = Settings(tickets_db_path=db_path)
        monkeypatch.setattr(main_module, "get_settings", lambda: settings)
        result = tickets.create_support_ticket(
            CreateSupportTicketInput(category="IT Support", subject="s", description="d"),
            db_path=db_path,
        )

        response = api_client.post(
            f"/api/v1/support-tickets/{result.ticket_id}/approve",
            headers={"X-User-Role": "staff"},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "SUBMITTED"
