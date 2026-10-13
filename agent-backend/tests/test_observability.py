"""Observability tests: every cognitive step of an agent run is traced, logged, and exported.

Like test_agent_orchestrator.py, no real Groq call is made: the model is
scripted and retrieval is stubbed, so these exercise the real
orchestrator, RunTrace, tool dispatch, exporter, and API.
"""

import json
import logging
from pathlib import Path

import groq
import httpx
import pytest
from fastapi.testclient import TestClient

import main as main_module
from agent import orchestrator
from config import Settings
from llm.client import GroqClient, LLMConfigurationError, LLMRequestError
from observability import error_codes
from observability.export import load_trace, render_markdown
from observability.structured_logging import StructuredFormatter
from rag.retriever import RetrievedChunk, retrieve_with_rejected
from tests.test_agent_orchestrator import FakeMessage, FakeToolCall, _ticket_call, _timetable_call

USAGE = {"prompt_tokens": 100, "completion_tokens": 20, "total_tokens": 120}


def _chunk(score, page=1, text="Students found with unauthorised material shall be..."):
    return RetrievedChunk(
        text=text,
        score=score,
        document_id="DOC007",
        document_name="Examination Malpractice Rules",
        doc_type="Policy",
        version_or_date="2019",
        page=page,
        chunk_id=f"DOC007-p{page}-c0",
    )


def _script(monkeypatch, responses):
    """Scripted model that also fills `last_call` like the real client does."""
    queue = list(responses)

    def fake(self, messages, tools=None, tool_choice=None):
        self.last_call = None
        item = queue.pop(0)
        if isinstance(item, Exception):
            raise item
        self.last_call = {"provider_request_id": "req_test", "finish_reason": "stop", "usage": dict(USAGE)}
        return item

    monkeypatch.setattr(GroqClient, "create_completion", fake)


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
        trace_export_dir=str(tmp_path / "traces"),
        max_tool_calls=3,
        agent_max_iterations=4,
    )


@pytest.fixture(autouse=True)
def _stub_retrieval(monkeypatch):
    monkeypatch.setattr(
        orchestrator, "_retrieve", lambda message, settings: ([_chunk(0.62, 3), _chunk(0.41, 4)], [_chunk(0.21, 9)])
    )


# --- Normal run ------------------------------------------------------------


def test_normal_run_trace_captures_every_cognitive_step(monkeypatch, settings):
    _script(monkeypatch, [FakeMessage(tool_calls=[_timetable_call()]), FakeMessage(content="Monday 10:00.")])

    state = orchestrator.run_agent("When is BSE4104?", settings=settings)
    trace = state.trace

    assert trace["schema_version"] == "trace-v1" and trace["run_id"] == state.run_id
    assert trace["request"] == {"message": "When is BSE4104?", "actor_role": "student", "actor_id": "anonymous"}

    # Model parameters and prompt version/fingerprint.
    model = trace["config"]["model"]
    assert model == {
        "provider": "groq",
        "name": settings.groq_model,
        "temperature": 0.2,
        "max_tokens": 1500,
        "timeout_seconds": 20.0,
        "max_retries": 2,
    }
    assert trace["config"]["prompt"]["version"] == "agent-v1.0"
    assert len(trace["config"]["prompt"]["system_prompt_sha256"]) == 64

    # Retrieved chunks with relevance scores, ranked, including the rejected one.
    retrieval = trace["retrieval"]
    assert [c["relevance_score"] for c in retrieval["chunks"]] == [0.62, 0.41, 0.21]
    assert [c["used_as_evidence"] for c in retrieval["chunks"]] == [True, True, False]
    assert retrieval["kept_count"] == 2 and retrieval["rejected_count"] == 1
    assert retrieval["latency_ms"] >= 0

    # Per-iteration latency, LLM call metadata, tool arguments and response.
    first, second = trace["iterations"]
    assert first["decisions"] == ["tool_call"] and second["decisions"] == ["final_answer"]
    assert all(it["latency_ms"] is not None and "_t0" not in it for it in trace["iterations"])
    assert first["llm_call"]["tools_offered"] == ["check_timetable", "create_support_ticket"]
    assert first["llm_call"]["requested_tools"] == ["check_timetable"]
    assert first["llm_call"]["usage"] == USAGE and first["llm_call"]["provider_request_id"] == "req_test"
    (tool,) = first["tool_calls"]
    assert tool["tool_name"] == "check_timetable" and tool["arguments"] == {"course_code": "BSE4104"}
    assert tool["executed"] and tool["success"] and tool["error_code"] is None
    assert tool["response"]["sessions"][0]["venue"] == "Room 204"
    assert tool["latency_ms"] is not None

    # Terminal status, totals and latency breakdown.
    terminal = trace["terminal"]
    assert terminal["status"] == "completed" and terminal["error_code"] is None
    assert terminal["token_usage"] == {"prompt_tokens": 200, "completion_tokens": 40, "total_tokens": 240}
    assert set(terminal["latency_breakdown_ms"]) == {"retrieval", "llm", "tools", "orchestration_overhead", "total"}
    assert trace["errors"] == []

    # Step latencies are surfaced on AgentState too.
    assert all(step.latency_ms is not None for step in state.steps)


def test_trace_is_exported_as_json_and_markdown(monkeypatch, settings):
    _script(monkeypatch, [FakeMessage(content="Answer.")])

    state = orchestrator.run_agent("Hello", settings=settings)

    assert load_trace(settings.trace_export_dir, state.run_id) == json.loads(json.dumps(state.trace))
    markdown = (Path(settings.trace_export_dir) / f"{state.run_id}.md").read_text()
    for heading in ("## Context: retrieval", "## Iterations", "## Errors", "## Latency breakdown (ms)", "## Final response"):
        assert heading in markdown
    assert "0.6200" in markdown and "agent-v1.0" in markdown


def test_export_disabled_writes_nothing(monkeypatch, settings, tmp_path):
    _script(monkeypatch, [FakeMessage(content="Answer.")])
    settings = settings.model_copy(update={"trace_export_dir": ""})

    state = orchestrator.run_agent("Hello", settings=settings)

    assert state.trace["terminal"]["status"] == "completed"
    assert not (tmp_path / "traces").exists()


# --- Boundary runs -----------------------------------------------------------


def test_human_approval_boundary_records_drafted_ticket(monkeypatch, settings):
    _script(monkeypatch, [FakeMessage(tool_calls=[_ticket_call()]), FakeMessage(content="Pending approval.")])

    trace = orchestrator.run_agent("Portal locked", settings=settings).trace

    assert trace["terminal"]["status"] == "human_approval_required"
    assert trace["terminal"]["drafted_ticket_ids"] == ["DRAFT-001"]
    assert trace["iterations"][1]["decisions"] == ["final_answer", "stop"]


def test_unapproved_tool_is_traced_as_not_executed(monkeypatch, settings):
    approve = FakeToolCall("x1", "approve_ticket", json.dumps({"ticket_id": "DRAFT-001"}))
    _script(monkeypatch, [FakeMessage(tool_calls=[approve])])

    trace = orchestrator.run_agent("Approve it", settings=settings).trace

    (tool,) = trace["iterations"][0]["tool_calls"]
    assert tool["approved"] is False and tool["executed"] is False and tool["response"] is None
    assert tool["error_code"] == error_codes.AGENT_TOOL_NOT_APPROVED
    assert trace["terminal"] == trace["terminal"] | {
        "status": "tool_not_approved",
        "error_code": error_codes.AGENT_TOOL_NOT_APPROVED,
    }


def test_iteration_budget_boundary_has_error_code(monkeypatch, settings):
    settings = settings.model_copy(update={"agent_max_iterations": 1})
    _script(monkeypatch, [FakeMessage(tool_calls=[_timetable_call()])])

    trace = orchestrator.run_agent("When is BSE4104?", settings=settings).trace

    assert trace["terminal"]["status"] == "max_iterations_reached"
    assert trace["terminal"]["error_code"] == error_codes.AGENT_ITERATION_BUDGET_EXHAUSTED
    assert [e["stage"] for e in trace["errors"]] == ["contract"]


def test_tool_budget_boundary_offers_no_tools_once_spent(monkeypatch, settings):
    settings = settings.model_copy(update={"max_tool_calls": 1})
    _script(
        monkeypatch,
        [FakeMessage(tool_calls=[_timetable_call("c1")]), FakeMessage(tool_calls=[_timetable_call("c2")])],
    )

    trace = orchestrator.run_agent("When is BSE4104?", settings=settings).trace

    assert trace["iterations"][1]["llm_call"]["tools_offered"] == []
    assert trace["iterations"][1]["llm_call"]["tool_choice"] == "none"
    assert trace["terminal"]["error_code"] == error_codes.AGENT_TOOL_BUDGET_EXHAUSTED


# --- Error runs ----------------------------------------------------------------


def test_llm_error_code_reaches_trace_and_state(monkeypatch, settings):
    _script(monkeypatch, [LLMRequestError("The model provider timed out.", code=error_codes.LLM_TIMEOUT)])

    state = orchestrator.run_agent("Hello", settings=settings)

    assert state.status == "llm_error" and state.error_code == error_codes.LLM_TIMEOUT
    assert state.steps[0].error_code == error_codes.LLM_TIMEOUT
    llm_call = state.trace["iterations"][0]["llm_call"]
    assert llm_call["error_code"] == error_codes.LLM_TIMEOUT and llm_call["usage"] is None
    assert state.trace["errors"][0] | {"at": None} == {
        "code": error_codes.LLM_TIMEOUT,
        "stage": "llm",
        "iteration": 1,
        "message": "The model provider timed out.",
        "at": None,
    }


def test_tool_failure_error_code_and_replan(monkeypatch, settings):
    settings = settings.model_copy(update={"timetable_data_path": "/nonexistent/timetable.json"})
    _script(monkeypatch, [FakeMessage(tool_calls=[_timetable_call()]), FakeMessage(content="Service is down.")])

    trace = orchestrator.run_agent("When is BSE4104?", settings=settings).trace

    tool = trace["iterations"][0]["tool_calls"][0]
    assert tool["success"] is False and tool["error_code"] == error_codes.TOOL_DATA_UNAVAILABLE
    assert trace["terminal"]["status"] == "completed"  # the agent observed the failure and re-planned
    assert [e["code"] for e in trace["errors"]] == [error_codes.TOOL_DATA_UNAVAILABLE]


def test_tool_with_no_result_gets_no_result_code(monkeypatch, settings):
    _script(monkeypatch, [FakeMessage(tool_calls=[_timetable_call(course="XYZ9999")]), FakeMessage(content="None.")])

    trace = orchestrator.run_agent("When is XYZ9999?", settings=settings).trace

    assert trace["iterations"][0]["tool_calls"][0]["error_code"] == error_codes.TOOL_NO_RESULT


def test_malformed_tool_arguments_keep_raw_text(monkeypatch, settings):
    bad = FakeToolCall("b1", "check_timetable", "{not json")
    _script(monkeypatch, [FakeMessage(tool_calls=[bad]), FakeMessage(content="Sorry.")])

    trace = orchestrator.run_agent("When?", settings=settings).trace

    tool = trace["iterations"][0]["tool_calls"][0]
    assert tool["arguments"] == {} and tool["arguments_raw"] == "{not json"
    assert tool["error_code"] == error_codes.TOOL_INVALID_JSON


def test_not_configured_run_is_aborted_but_traced(settings):
    settings = settings.model_copy(update={"groq_api_key": ""})

    with pytest.raises(LLMConfigurationError):
        orchestrator.run_agent("Hello", settings=settings)

    (path,) = Path(settings.trace_export_dir).glob("*.json")
    trace = json.loads(path.read_text())
    assert trace["terminal"]["status"] == "aborted"
    assert trace["terminal"]["error_code"] == error_codes.LLM_NOT_CONFIGURED
    assert trace["retrieval"] is None and trace["iterations"] == []


def test_retrieval_failure_is_aborted_with_retrieval_code(monkeypatch, settings):
    def broken(message, settings):
        raise RuntimeError("chroma unavailable")

    monkeypatch.setattr(orchestrator, "_retrieve", broken)
    _script(monkeypatch, [])

    with pytest.raises(RuntimeError):
        orchestrator.run_agent("Hello", settings=settings)

    (path,) = Path(settings.trace_export_dir).glob("*.json")
    trace = json.loads(path.read_text())
    assert trace["terminal"]["error_code"] == error_codes.RETRIEVAL_ERROR
    assert trace["errors"][0]["stage"] == "retrieval"


# --- Client error codes ---------------------------------------------------------


@pytest.mark.parametrize(
    "exc, code",
    [
        (groq.APITimeoutError(request=httpx.Request("POST", "https://x")), error_codes.LLM_TIMEOUT),
        (groq.APIConnectionError(request=httpx.Request("POST", "https://x")), error_codes.LLM_CONNECTION_ERROR),
        (
            groq.AuthenticationError(
                "bad key", response=httpx.Response(401, request=httpx.Request("POST", "https://x")), body=None
            ),
            "LLM_HTTP_ERROR_401",
        ),
        (
            groq.RateLimitError(
                "slow down", response=httpx.Response(429, request=httpx.Request("POST", "https://x")), body=None
            ),
            error_codes.LLM_RATE_LIMITED,
        ),
    ],
)
def test_client_maps_provider_failures_to_error_codes(monkeypatch, exc, code):
    client = GroqClient(api_key="k", model="m")

    def raise_exc(**kwargs):
        raise exc

    monkeypatch.setattr(client._client.chat.completions, "create", raise_exc)

    with pytest.raises(LLMRequestError) as info:
        client.create_completion(messages=[])
    assert info.value.code == code
    assert client.last_call is None


# --- Structured logging -----------------------------------------------------------


def test_every_cognitive_step_is_logged_as_a_structured_event(monkeypatch, settings, caplog):
    _script(monkeypatch, [FakeMessage(tool_calls=[_timetable_call()]), FakeMessage(content="Monday.")])

    with caplog.at_level(logging.INFO, logger="agent.trace"):
        state = orchestrator.run_agent("When is BSE4104?", settings=settings)

    events = [r.getMessage() for r in caplog.records if r.name == "agent.trace"]
    assert events == [
        "agent.run.started",
        "agent.run.config",
        "agent.retrieval",
        "agent.llm_call",
        "agent.tool_call",
        "agent.iteration",
        "agent.llm_call",
        "agent.iteration",
        "agent.run.finished",
    ]
    assert all(r.trace_event["run_id"] == state.run_id for r in caplog.records if r.name == "agent.trace")


def test_json_formatter_emits_one_object_per_line():
    record = logging.LogRecord("agent.trace", logging.INFO, __file__, 1, "agent.tool_call", None, None)
    record.trace_event = {"run_id": "r1", "tool_name": "check_timetable", "latency_ms": 1.5, "event": "spoof"}

    line = StructuredFormatter(json_output=True).format(record)

    payload = json.loads(line)
    assert payload["event"] == "agent.tool_call"  # reserved keys can't be overwritten by fields
    assert payload["tool_name"] == "check_timetable" and payload["latency_ms"] == 1.5
    assert "\n" not in line


def test_text_formatter_appends_fields():
    record = logging.LogRecord("agent.trace", logging.INFO, __file__, 1, "agent.iteration", None, None)
    record.trace_event = {"iteration": 1}
    assert StructuredFormatter(json_output=False).format(record).endswith('agent.iteration {"iteration": 1}')


# --- Retrieval and export helpers -----------------------------------------------------


def test_retrieve_with_rejected_splits_on_min_score():
    class Store:
        def query(self, query_text, top_k):
            return [
                {"chunk_id": f"D-p{i}", "text": "t", "score": s, "document_id": "D", "document_name": "Doc",
                 "doc_type": "Policy", "version_or_date": "2024", "page": i}
                for i, s in enumerate([0.8, 0.35, 0.2], start=1)
            ]

    kept, rejected = retrieve_with_rejected(Store(), "q", top_k=3, min_score=0.35)
    assert [c.score for c in kept] == [0.8, 0.35] and [c.score for c in rejected] == [0.2]
    assert kept[0].chunk_id == "D-p1"


def test_markdown_escapes_pipes_in_cells():
    trace = {"run_id": "r", "request": {"message": "a | b"}, "terminal": {}, "iterations": [], "errors": []}
    assert "a \\| b" in render_markdown(trace)


# --- API -----------------------------------------------------------------------------


def test_agent_endpoint_returns_error_code_and_latency(monkeypatch, settings):
    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    _script(monkeypatch, [FakeMessage(tool_calls=[_timetable_call()]), FakeMessage(content="Monday.")])

    body = TestClient(main_module.app).post(
        "/api/v1/agent/student-support", json={"message": "When is BSE4104?"}
    ).json()

    assert body["error_code"] is None and body["total_latency_ms"] is not None
    assert body["steps"][0]["latency_ms"] is not None


def test_trace_endpoint_is_staff_only(monkeypatch, settings):
    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    _script(monkeypatch, [FakeMessage(content="Answer.")])
    client = TestClient(main_module.app)
    run_id = client.post("/api/v1/agent/student-support", json={"message": "Hi"}).json()["run_id"]

    student = client.get(f"/api/v1/agent/traces/{run_id}", headers={"X-User-Role": "student"})
    staff = client.get(f"/api/v1/agent/traces/{run_id}", headers={"X-User-Role": "staff"})
    missing = client.get(
        "/api/v1/agent/traces/00000000-0000-4000-8000-000000000000", headers={"X-User-Role": "staff"}
    )
    invalid = client.get("/api/v1/agent/traces/..%2F..%2Fconfig", headers={"X-User-Role": "staff"})

    assert student.status_code == 403
    assert staff.status_code == 200 and staff.json()["run_id"] == run_id
    assert missing.status_code == 404
    assert invalid.status_code in (400, 404)


def test_staff_ticket_decisions_are_audit_logged(monkeypatch, settings, caplog):
    from tools import tickets
    from tools.schemas import CreateSupportTicketInput

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    draft = tickets.create_support_ticket(
        CreateSupportTicketInput(category="IT Support", subject="Locked", description="Portal locked."),
        db_path=settings.tickets_db_path,
    )
    client = TestClient(main_module.app)

    with caplog.at_level(logging.INFO, logger="audit"):
        client.post(f"/api/v1/support-tickets/{draft.ticket_id}/approve", headers={"X-User-Role": "student"})
        client.post(
            f"/api/v1/support-tickets/{draft.ticket_id}/approve",
            headers={"X-User-Role": "staff", "X-User-Id": "staff-7"},
        )

    denied, approved = [r for r in caplog.records if r.name == "audit"]
    assert denied.getMessage() == "ticket.approve.denied" and denied.trace_event["actor_role"] == "student"
    assert approved.getMessage() == "ticket.approve"
    assert {"actor_id": "staff-7", "ticket_id": draft.ticket_id, "success": True, "status": "SUBMITTED"}.items() <= (
        approved.trace_event.items()
    )


def test_two_tool_calls_in_one_reply_follow_the_stage_model(monkeypatch, settings):
    # REPLAN -> ACT is not an allowed stage transition, so the second call in
    # the same reply must go REPLAN -> PLAN -> ACT rather than crash the run.
    _script(
        monkeypatch,
        [FakeMessage(tool_calls=[_timetable_call("c1"), _ticket_call("t1")]), FakeMessage(content="Done.")],
    )

    state = orchestrator.run_agent("When is BSE4104? Also my portal is locked.", settings=settings)

    assert state.status == "human_approval_required"
    assert [tc["tool_name"] for tc in state.trace["iterations"][0]["tool_calls"]] == [
        "check_timetable",
        "create_support_ticket",
    ]
