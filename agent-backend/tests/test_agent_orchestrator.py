"""Week 5 bounded agent tests - one per stop condition in the Agent Task Contract.

No real Groq call is made: `GroqClient.create_completion` is monkeypatched
to return scripted assistant messages, and retrieval is stubbed, so these
exercise the real orchestrator, contract, and Week 4 tool dispatch.
"""

import json

import pytest
from fastapi.testclient import TestClient

import main as main_module
from agent import orchestrator
from agent.contract import TERMINAL_STATUSES, build_contract
from auth import Actor
from config import Settings
from llm.client import GroqClient, LLMRequestError
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


def _script(monkeypatch, responses):
    """Return scripted messages in order; record the tools offered on each call."""
    queue = list(responses)
    offered = []

    def fake(self, messages, tools=None, tool_choice=None):
        offered.append((tools is not None, tool_choice))
        item = queue.pop(0)
        if isinstance(item, Exception):
            raise item
        return item

    monkeypatch.setattr(GroqClient, "create_completion", fake)
    return offered


def _timetable_call(call_id="c1", course="BSE4104"):
    return FakeToolCall(call_id, "check_timetable", json.dumps({"course_code": course}))


def _ticket_call(call_id="t1"):
    return FakeToolCall(
        call_id,
        "create_support_ticket",
        json.dumps({"category": "IT Support", "subject": "Portal locked", "description": "Account locked."}),
    )


@pytest.fixture(autouse=True)
def _no_real_retrieval(monkeypatch):
    monkeypatch.setattr(orchestrator, "_retrieve_evidence", lambda message, settings: ("no evidence", []))


@pytest.fixture
def settings(tmp_path):
    (tmp_path / "timetable.json").write_text(
        json.dumps(
            {
                "sessions": [
                    {
                        "course_code": "BSE4104",
                        "date": "2026-10-05",
                        "start_time": "10:00",
                        "end_time": "12:00",
                        "venue": "Room 204",
                    }
                ]
            }
        )
    )
    return Settings(
        groq_api_key="test-key",
        timetable_data_path=str(tmp_path / "timetable.json"),
        tickets_db_path=str(tmp_path / "tickets.db"),
        max_tool_calls=3,
        agent_max_iterations=4,
    )


def test_contract_approved_tools_are_exactly_the_week4_allow_list(settings):
    contract = build_contract(settings)
    assert contract.approved_tools == {"check_timetable", "create_support_ticket"}
    assert not contract.is_approved_tool("approve_ticket")
    assert contract.max_iterations == 4 and contract.max_tool_calls == 3


def test_direct_answer_completes_without_tools(monkeypatch, settings):
    _script(monkeypatch, [FakeMessage(content="According to the policy...")])

    state = orchestrator.run_agent("What is exam malpractice?", settings=settings)

    assert state.status == "completed"
    assert state.response == "According to the policy..."
    assert state.tool_call_count == 0
    assert [s.decision for s in state.steps] == ["final_answer"]


def test_timetable_tool_then_answer_completes(monkeypatch, settings):
    _script(monkeypatch, [FakeMessage(tool_calls=[_timetable_call()]), FakeMessage(content="Monday 10:00.")])

    state = orchestrator.run_agent("When is BSE4104?", settings=settings)

    assert state.status == "completed"
    assert state.iteration_count == 2
    assert state.tool_call_count == 1
    tool_step = state.steps[0]
    assert tool_step.decision == "tool_call" and tool_step.tool_name == "check_timetable"
    assert tool_step.tool_result["success"] is True
    assert "1 timetable session(s)" in tool_step.observation


def test_ticket_draft_stops_for_human_approval(monkeypatch, settings):
    _script(monkeypatch, [FakeMessage(tool_calls=[_ticket_call()]), FakeMessage(content="Draft pending approval.")])

    state = orchestrator.run_agent("I can't log in to the portal.", settings=settings)

    assert state.status == "human_approval_required"
    assert state.drafted_ticket_ids == ["DRAFT-001"]
    assert [s.decision for s in state.steps] == ["tool_call", "final_answer", "stop"]
    record = tickets.get_ticket("DRAFT-001", db_path=settings.tickets_db_path)
    assert record.status == "PENDING_APPROVAL"


def test_unapproved_tool_is_never_executed(monkeypatch, settings):
    approve = FakeToolCall("x1", "approve_ticket", json.dumps({"ticket_id": "DRAFT-001"}))
    _script(monkeypatch, [FakeMessage(tool_calls=[approve])])

    state = orchestrator.run_agent("Approve my ticket.", settings=settings)

    assert state.status == "tool_not_approved"
    assert state.tool_call_count == 0
    assert state.steps[-1].decision == "stop" and state.steps[-1].tool_name == "approve_ticket"
    assert tickets.get_ticket("DRAFT-001", db_path=settings.tickets_db_path) is None


def test_tool_budget_exhausted_stops_safely(monkeypatch, settings):
    settings = settings.model_copy(update={"max_tool_calls": 1})
    offered = _script(
        monkeypatch,
        [
            FakeMessage(tool_calls=[_timetable_call("c1")]),
            # Provider ignores tool_choice="none" and asks again.
            FakeMessage(tool_calls=[_timetable_call("c2")]),
        ],
    )

    state = orchestrator.run_agent("When is BSE4104?", settings=settings)

    assert state.status == "max_tool_calls_reached"
    assert state.tool_call_count == 1
    assert offered == [(True, "auto"), (False, "none")]


def test_iteration_budget_exhausted_stops_safely(monkeypatch, settings):
    settings = settings.model_copy(update={"agent_max_iterations": 2, "max_tool_calls": 5})
    _script(
        monkeypatch,
        [FakeMessage(tool_calls=[_timetable_call("c1")]), FakeMessage(tool_calls=[_timetable_call("c2")])],
    )

    state = orchestrator.run_agent("When is BSE4104?", settings=settings)

    assert state.status == "max_iterations_reached"
    assert state.iteration_count == 2
    assert state.steps[-1].decision == "stop"


def test_llm_failure_stops_with_safe_message(monkeypatch, settings):
    _script(monkeypatch, [LLMRequestError("The model provider timed out. Please try again.")])

    state = orchestrator.run_agent("Hello", settings=settings)

    assert state.status == "llm_error"
    assert state.steps[-1].decision == "error"
    assert "timed out" not in state.response  # internal detail stays in the trace, not the answer


def test_failed_tool_is_observed_and_agent_replans(monkeypatch, settings):
    _script(
        monkeypatch,
        [
            FakeMessage(tool_calls=[_timetable_call(course="XYZ9999")]),
            FakeMessage(content="I couldn't find that course."),
        ],
    )

    state = orchestrator.run_agent("When is XYZ9999?", settings=settings)

    assert state.status == "completed"
    assert state.steps[0].tool_result["success"] is False
    assert "re-planning" in state.steps[0].observation


def test_guest_role_tool_request_is_refused_by_dispatch(monkeypatch, settings):
    _script(monkeypatch, [FakeMessage(tool_calls=[_ticket_call()]), FakeMessage(content="Please sign in.")])

    state = orchestrator.run_agent("Make a ticket", settings=settings, actor=Actor(role="guest", user_id="g"))

    assert state.status == "completed"
    assert state.drafted_ticket_ids == []
    assert "not authorized" in state.steps[0].tool_result["error"]


def test_agent_endpoint_returns_full_trace(monkeypatch, settings):
    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    _script(monkeypatch, [FakeMessage(tool_calls=[_timetable_call()]), FakeMessage(content="Monday 10:00.")])

    response = TestClient(main_module.app).post(
        "/api/v1/agent/student-support", json={"message": "When is BSE4104?"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] in TERMINAL_STATUSES
    assert body["status"] == "completed"
    assert body["prompt_version"] == "agent-v1.0"
    assert body["tool_call_count"] == 1 and body["iteration_count"] == 2
    assert body["steps"][0]["tool_name"] == "check_timetable"
    assert {"run_id", "plan", "max_iterations", "max_tool_calls", "sources"} <= body.keys()


def test_agent_endpoint_503_when_groq_not_configured(monkeypatch, settings):
    monkeypatch.setattr(main_module, "get_settings", lambda: settings.model_copy(update={"groq_api_key": ""}))

    response = TestClient(main_module.app).post(
        "/api/v1/agent/student-support", json={"message": "Hi"}
    )

    assert response.status_code == 503
