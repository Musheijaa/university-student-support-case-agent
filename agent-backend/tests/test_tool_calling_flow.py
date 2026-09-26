"""End-to-end tool-calling loop tests.

No real Groq call is made: `GroqClient.create_completion` is monkeypatched
to return a scripted sequence of fake assistant messages (tool-call
requests, then a final answer), so these tests exercise the real
dispatch/authorization/bounded-loop logic without network access.
"""

import json

import pytest

from auth import Actor
from config import Settings
from llm import service as service_module
from llm.client import GroqClient
from tools import tickets


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
    responses = list(responses)

    def fake(self, messages, tools=None, tool_choice=None):
        return responses.pop(0)

    return fake


def _tool_choice_aware_create_completion(tool_request_queue, final_message):
    """Models a compliant provider: once tool_choice='none' is passed, it
    stops requesting tools and returns the final message, regardless of
    how many scripted tool-call responses are left in the queue."""
    queue = list(tool_request_queue)

    def fake(self, messages, tools=None, tool_choice=None):
        if tool_choice == "none":
            return final_message
        return queue.pop(0)

    return fake


def _always_tool_calls_create_completion(make_tool_call):
    """Models a misbehaving/mocked provider that ignores tool_choice='none'
    and keeps requesting a tool call every single turn."""

    def fake(self, messages, tools=None, tool_choice=None):
        return FakeMessage(tool_calls=[make_tool_call()])

    return fake


@pytest.fixture(autouse=True)
def _no_real_retrieval(monkeypatch):
    # Isolate these tests from the real RAG index - not what's under test here.
    monkeypatch.setattr(
        service_module, "_retrieve_evidence", lambda message, settings: ("no evidence", [])
    )


def _settings(tmp_path, max_tool_calls=3) -> Settings:
    return Settings(
        groq_api_key="test-key",
        timetable_data_path=str(tmp_path / "timetable.json"),
        tickets_db_path=str(tmp_path / "tickets.db"),
        max_tool_calls=max_tool_calls,
    )


def _write_timetable(tmp_path, sessions):
    (tmp_path / "timetable.json").write_text(json.dumps({"sessions": sessions}))


STUDENT = Actor(role="student", user_id="s1")


def test_scenario_timetable_tool_call_then_final_answer(tmp_path, monkeypatch):
    _write_timetable(
        tmp_path,
        [{"course_code": "BSE4104", "date": "2026-09-24", "start_time": "10:00", "end_time": "12:00", "venue": "Room 204"}],
    )
    monkeypatch.setattr(
        GroqClient,
        "create_completion",
        _sequenced_create_completion(
            [
                FakeMessage(
                    tool_calls=[
                        FakeToolCall("call_1", "check_timetable", json.dumps({"course_code": "BSE4104"}))
                    ]
                ),
                FakeMessage(content="BSE4104 meets 24 Sept 2026, 10:00-12:00, Room 204."),
            ]
        ),
    )

    result = service_module.get_student_support_response(
        "When is BSE4104 scheduled?", settings=_settings(tmp_path), actor=STUDENT
    )

    assert result.response == "BSE4104 meets 24 Sept 2026, 10:00-12:00, Room 204."
    assert len(result.tool_calls) == 1
    assert result.tool_calls[0].tool == "check_timetable"
    assert result.tool_calls[0].result["success"] is True
    assert result.tool_calls[0].result["sessions"][0]["venue"] == "Room 204"


def test_scenario_support_ticket_creates_a_real_pending_draft(tmp_path, monkeypatch):
    monkeypatch.setattr(
        GroqClient,
        "create_completion",
        _sequenced_create_completion(
            [
                FakeMessage(
                    tool_calls=[
                        FakeToolCall(
                            "call_1",
                            "create_support_ticket",
                            json.dumps(
                                {
                                    "category": "IT Support",
                                    "subject": "Cannot access portal",
                                    "description": "Login is rejected.",
                                }
                            ),
                        )
                    ]
                ),
                FakeMessage(content="I've created a draft ticket, pending staff approval."),
            ]
        ),
    )
    settings = _settings(tmp_path)

    result = service_module.get_student_support_response(
        "I cannot access the student portal.", settings=settings, actor=STUDENT
    )

    assert "pending" in result.response.lower()
    invocation = result.tool_calls[0]
    assert invocation.tool == "create_support_ticket"
    assert invocation.result["status"] == "PENDING_APPROVAL"

    # The draft actually exists in the store, not just in the model's text.
    record = tickets.get_ticket(invocation.result["ticket_id"], db_path=settings.tickets_db_path)
    assert record is not None
    assert record.status == "PENDING_APPROVAL"


def test_scenario_missing_tool_parameter_is_reported_back_to_the_model(tmp_path, monkeypatch):
    _write_timetable(tmp_path, [])
    monkeypatch.setattr(
        GroqClient,
        "create_completion",
        _sequenced_create_completion(
            [
                FakeMessage(
                    tool_calls=[FakeToolCall("call_1", "check_timetable", json.dumps({}))]
                ),
                FakeMessage(content="I need a course code to look that up."),
            ]
        ),
    )

    result = service_module.get_student_support_response(
        "When's my class?", settings=_settings(tmp_path), actor=STUDENT
    )

    assert result.tool_calls[0].result["success"] is False
    assert "Invalid input" in result.tool_calls[0].result["error"]
    assert result.response == "I need a course code to look that up."


def test_scenario_unauthorized_actor_tool_call_fails_safely(tmp_path, monkeypatch):
    _write_timetable(tmp_path, [])
    monkeypatch.setattr(
        GroqClient,
        "create_completion",
        _sequenced_create_completion(
            [
                FakeMessage(
                    tool_calls=[
                        FakeToolCall("call_1", "check_timetable", json.dumps({"course_code": "BSE4104"}))
                    ]
                ),
                FakeMessage(content="I couldn't check that for you."),
            ]
        ),
    )
    guest = Actor(role="guest", user_id="anon")

    result = service_module.get_student_support_response(
        "When is BSE4104?", settings=_settings(tmp_path), actor=guest
    )

    assert result.tool_calls[0].result["success"] is False
    assert "not authorized" in result.tool_calls[0].result["error"]


def test_tool_calls_are_bounded_by_max_tool_calls(tmp_path, monkeypatch):
    """Compliant-provider case: the model stops requesting tools once
    tool_choice='none' is passed, exactly as a real Groq call would."""
    _write_timetable(tmp_path, [])
    tool_requests = [
        FakeMessage(
            tool_calls=[FakeToolCall(f"call_{i}", "check_timetable", json.dumps({"course_code": "BSE4104"}))]
        )
        for i in range(10)
    ]
    monkeypatch.setattr(
        GroqClient,
        "create_completion",
        _tool_choice_aware_create_completion(tool_requests, FakeMessage(content="Final answer.")),
    )

    result = service_module.get_student_support_response(
        "When is BSE4104?", settings=_settings(tmp_path, max_tool_calls=3), actor=STUDENT
    )

    assert len(result.tool_calls) == 3
    assert result.response == "Final answer."


def test_tool_execution_is_hard_capped_even_if_provider_ignores_tool_choice(tmp_path, monkeypatch):
    """Defensive case: even if the provider keeps returning tool_calls after
    tool_choice='none', no more than max_tool_calls are ever executed, and
    the loop still terminates instead of running forever."""
    _write_timetable(tmp_path, [])
    monkeypatch.setattr(
        GroqClient,
        "create_completion",
        _always_tool_calls_create_completion(
            lambda: FakeToolCall("call_x", "check_timetable", json.dumps({"course_code": "BSE4104"}))
        ),
    )

    result = service_module.get_student_support_response(
        "When is BSE4104?", settings=_settings(tmp_path, max_tool_calls=3), actor=STUDENT
    )

    executed_results = [tc for tc in result.tool_calls if "Tool call limit reached" not in tc.result.get("error", "")]
    assert len(executed_results) == 3
    assert result.response  # the loop terminated and returned something, rather than hanging
