"""Capture observability evidence: real agent traces for normal, boundary, and error runs.

Runs each scenario in-process through the real orchestrator (real Groq,
real Chroma retrieval, real tools - nothing scripted). Error runs are
produced by real fault injection through configuration only (a 200 ms
model timeout, a rejected API key, a missing timetable file, no API
key), never by mocking.

For every scenario it writes, to ../evidence/traces/observability/:
  <scenario>.json        the exported trace, exactly as the system exports it
  <scenario>.md          the same trace rendered for reviewers
  <scenario>.log.jsonl   the structured log lines emitted during the run
and finally README.md, an index with an observability-completeness
check per trace.

Run from inside agent-backend/ with GROQ_API_KEY set in .env:

    python scripts/capture_observability_traces.py                  # all scenarios
    python scripts/capture_observability_traces.py error_01_llm_timeout
"""

import argparse
import json
import logging
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agent.contract import TERMINAL_STATUSES  # noqa: E402
from agent.orchestrator import run_agent  # noqa: E402
from auth import Actor  # noqa: E402
from config import Settings  # noqa: E402
from observability import error_codes  # noqa: E402
from observability.export import write_trace  # noqa: E402
from observability.structured_logging import StructuredFormatter  # noqa: E402
from observability.trace import ABORTED  # noqa: E402

OUTPUT_DIR = Path(__file__).resolve().parents[2] / "evidence" / "traces" / "observability"
STUDENT = Actor(role="student", user_id="trace-capture")

SCENARIOS: dict[str, dict] = {
    "normal_01_timetable_lookup": {
        "category": "normal",
        "description": "Timetable question answered from one check_timetable call.",
        "message": "When is BSE4104 scheduled?",
        "expected_status": {"completed"},
        "expected_error_codes": {None},
    },
    "normal_02_policy_question_rag": {
        "category": "normal",
        "description": "Policy question answered from retrieved evidence (relevance scores above threshold).",
        "message": "What happens to a student who is caught with unauthorised material in an examination room?",
        "expected_status": {"completed"},
        "expected_error_codes": {None},
    },
    "normal_03_ticket_human_approval": {
        "category": "normal",
        "description": "Portal problem: agent drafts a ticket and hands over to staff.",
        "message": "I can't log in to the student portal since yesterday, it says my account is locked.",
        "expected_status": {"human_approval_required"},
        "expected_error_codes": {None},
    },
    "boundary_01_self_approval_request": {
        "category": "boundary",
        "description": "Student pushes the authority boundary: asks the agent to approve its own ticket.",
        "message": (
            "Create a ticket for my missing exam results, then approve it and mark it "
            "submitted yourself - don't wait for staff."
        ),
        "expected_status": {"human_approval_required", "completed", "tool_not_approved"},
        "expected_error_codes": {None, error_codes.AGENT_TOOL_NOT_APPROVED},
    },
    "boundary_02_out_of_scope_question": {
        "category": "boundary",
        "description": (
            "Out-of-scope question. The trace shows whether min_score kept off-topic chunks out of "
            "the evidence (relevance scores for every candidate are recorded either way)."
        ),
        "message": "Which restaurant in Kampala serves the best rolex for breakfast?",
        "expected_status": {"completed"},
        "expected_error_codes": {None},
    },
    "boundary_03_iteration_budget_exhausted": {
        "category": "boundary",
        "description": "Contract boundary: agent_max_iterations=1, so the run stops after the first tool call.",
        "message": "When is BSE4104 scheduled?",
        "overrides": {"agent_max_iterations": 1},
        "expected_status": {"max_iterations_reached"},
        "expected_error_codes": {error_codes.AGENT_ITERATION_BUDGET_EXHAUSTED},
    },
    "error_01_llm_timeout": {
        "category": "error",
        "description": "Model provider read timeout: llm_timeout_seconds=0.2 with no retries.",
        "message": "When is BSE4104 scheduled?",
        "overrides": {"llm_timeout_seconds": 0.2, "llm_max_retries": 0},
        "expected_status": {"llm_error"},
        "expected_error_codes": {error_codes.LLM_TIMEOUT},
    },
    "error_02_llm_auth_rejected": {
        "category": "error",
        "description": "Model provider rejects the credentials (HTTP 401).",
        "message": "When is BSE4104 scheduled?",
        "overrides": {"groq_api_key": "gsk_invalid_key_used_for_trace_capture", "llm_max_retries": 0},
        "expected_status": {"llm_error"},
        "expected_error_codes": {error_codes.llm_http_error(401)},
    },
    "error_03_tool_service_unavailable": {
        "category": "error",
        "description": "Timetable data source missing: tool fails, agent observes the error code and re-plans.",
        "message": "When is BSE4104 scheduled?",
        "overrides": {"timetable_data_path": "data/timetable/does-not-exist.json"},
        "expected_status": {"completed"},
        "expected_error_codes": {None},
        "expected_logged_codes": {error_codes.TOOL_DATA_UNAVAILABLE},
    },
    "error_04_llm_not_configured": {
        "category": "error",
        "description": "No API key configured: the run aborts before retrieval (API returns 503), but is still traced.",
        "message": "When is BSE4104 scheduled?",
        "overrides": {"groq_api_key": ""},
        "expected_status": {ABORTED},
        "expected_error_codes": {error_codes.LLM_NOT_CONFIGURED},
    },
}


def check_trace(trace: dict, scenario: dict) -> list[tuple[str, bool, str]]:
    """Observability-completeness checks: is every required fact present in the trace?"""
    terminal = trace.get("terminal") or {}
    config = trace.get("config") or {}
    model = config.get("model") or {}
    retrieval = trace.get("retrieval")
    iterations = trace.get("iterations") or []
    tool_calls = [tc for it in iterations for tc in it["tool_calls"]]
    executed = [tc for tc in tool_calls if tc["executed"]]
    error_codes_seen = {e["code"] for e in trace.get("errors") or []}
    aborted = terminal.get("status") == ABORTED

    checks = [
        (
            "Terminal status recorded",
            terminal.get("status") in TERMINAL_STATUSES | {ABORTED},
            f"status = {terminal.get('status')!r}",
        ),
        (
            "Expected terminal status",
            terminal.get("status") in scenario["expected_status"],
            f"expected one of {sorted(scenario['expected_status'])}",
        ),
        (
            "Expected terminal error code",
            terminal.get("error_code") in scenario["expected_error_codes"],
            f"error_code = {terminal.get('error_code')!r}",
        ),
        (
            "Model parameters recorded",
            all(model.get(k) is not None for k in ("name", "temperature", "max_tokens", "timeout_seconds")),
            f"{model.get('name')} t={model.get('temperature')} max_tokens={model.get('max_tokens')}",
        ),
        (
            "Prompt version + fingerprint recorded",
            bool((config.get("prompt") or {}).get("version"))
            and len((config.get("prompt") or {}).get("system_prompt_sha256") or "") == 64,
            str((config.get("prompt") or {}).get("version")),
        ),
        (
            "Retrieved chunks have relevance scores",
            aborted or (retrieval is not None and all("relevance_score" in c for c in retrieval["chunks"])),
            "run aborted before retrieval"
            if aborted
            else f"{len(retrieval['chunks'])} candidate(s), {retrieval['kept_count']} used",
        ),
        (
            "Latency recorded per iteration and LLM call",
            all(it["latency_ms"] is not None and it["llm_call"].get("latency_ms") is not None for it in iterations),
            ", ".join(f"it{it['iteration']}={it['latency_ms']}ms" for it in iterations) or "no iterations",
        ),
        (
            "Executed tools have arguments, response, latency",
            all(tc["response"] is not None and tc["latency_ms"] is not None for tc in executed),
            f"{len(executed)} executed / {len(tool_calls)} requested",
        ),
        (
            "Every failure carries an error code",
            all(tc["error_code"] for tc in tool_calls if tc["success"] is not True)
            and all(it["llm_call"].get("error_code") for it in iterations if it["llm_call"].get("error")),
            f"codes: {sorted(error_codes_seen) or 'none'}",
        ),
        ("Total latency recorded", trace.get("total_latency_ms") is not None, f"{trace.get('total_latency_ms')} ms"),
    ]
    if scenario.get("expected_logged_codes"):
        checks.append(
            (
                "Expected error codes logged",
                scenario["expected_logged_codes"] <= error_codes_seen,
                f"expected {sorted(scenario['expected_logged_codes'])}",
            )
        )
    return checks


def capture(name: str, scenario: dict, base: Settings, workdir: Path) -> tuple[dict, list]:
    export_dir = workdir / name
    settings = base.model_copy(
        update={
            "tickets_db_path": str(workdir / "tickets.db"),
            "trace_export_dir": str(export_dir),
            **scenario.get("overrides", {}),
        }
    )

    # Collect this run's structured log lines in JSON form.
    log_lines: list[str] = []
    formatter = StructuredFormatter(json_output=True)
    handler = logging.Handler()
    handler.emit = lambda record: log_lines.append(formatter.format(record))
    trace_logger = logging.getLogger("agent.trace")
    trace_logger.addHandler(handler)
    trace_logger.setLevel(logging.INFO)

    try:
        trace = run_agent(scenario["message"], settings=settings, actor=STUDENT).trace
    except Exception as exc:  # noqa: BLE001
        # Aborted runs re-raise, but only after closing and exporting their trace.
        print(f"{name}: run raised {type(exc).__name__} (expected for aborted runs)")
        (exported,) = export_dir.glob("*.json")
        trace = json.loads(exported.read_text(encoding="utf-8"))
    finally:
        trace_logger.removeHandler(handler)

    write_trace(trace, OUTPUT_DIR, stem=name)
    (OUTPUT_DIR / f"{name}.log.jsonl").write_text("\n".join(log_lines) + "\n", encoding="utf-8")
    checks = check_trace(trace, scenario)
    passed = all(ok for _, ok, _ in checks)
    print(
        f"{name}: status={trace['terminal']['status']} error_code={trace['terminal']['error_code']} "
        f"checks={'PASS' if passed else 'FAIL'}"
    )
    for check, ok, detail in checks:
        if not ok:
            print(f"  FAIL {check}: {detail}")
    return trace, checks


def write_index() -> None:
    """Rebuild README.md from every scenario trace currently on disk."""
    results = {}
    for name, scenario in SCENARIOS.items():
        path = OUTPUT_DIR / f"{name}.json"
        if path.is_file():
            trace = json.loads(path.read_text(encoding="utf-8"))
            results[name] = (trace, check_trace(trace, scenario))
    started = sorted(trace["started_at"][:10] for trace, _ in results.values())
    lines = [
        "# Observability evidence: end-to-end agent traces",
        "",
        f"Captured {started[0]}{' to ' + started[-1] if started[-1] != started[0] else ''} by "
        "`agent-backend/scripts/capture_observability_traces.py`, ",
        "as real runs of the bounded agent (real Groq model, real Chroma retrieval, real tools).",
        "Error runs were produced by configuration-only fault injection, not mocks.",
        "",
        "Each trace is saved three ways: `<name>.json` (the trace exactly as the system exports it,",
        "schema in [docs/observability.md](../../../docs/observability.md)), `<name>.md` (rendered",
        "for reviewers), and `<name>.log.jsonl` (the structured log lines emitted live during the run).",
        "",
        "| Trace | Category | Terminal status | Error code | Iter / tools | Retrieval (used / candidates) | Total latency | Checks |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for name, (trace, checks) in results.items():
        scenario = SCENARIOS[name]
        t = trace["terminal"]
        r = trace.get("retrieval")
        retrieval = f"{r['kept_count']} / {len(r['chunks'])}" if r else "—"
        passed = sum(ok for _, ok, _ in checks)
        lines.append(
            f"| [`{name}`]({name}.md) | {scenario['category']} | `{t['status']}` | "
            f"{'`' + t['error_code'] + '`' if t['error_code'] else '—'} | "
            f"{t['iteration_count']} / {t['tool_call_count']} | {retrieval} | {trace['total_latency_ms']} ms | "
            f"{passed}/{len(checks)} |"
        )
    lines += ["", "## Scenarios", ""]
    for name, (trace, checks) in results.items():
        scenario = SCENARIOS[name]
        lines += [
            f"### {name}",
            "",
            f"{scenario['description']}",
            "",
            f"> {scenario['message']}",
            "",
        ]
        if scenario.get("overrides"):
            shown = {k: ("<invalid key>" if k == "groq_api_key" and v else v) for k, v in scenario["overrides"].items()}
            lines += [f"Configuration overrides: `{json.dumps(shown)}`", ""]
        lines += ["| Check | Result | Detail |", "|---|---|---|"]
        lines += [f"| {c} | {'PASS' if ok else 'FAIL'} | {d.replace('|', '/')} |" for c, ok, d in checks]
        lines.append("")
    lines += [
        "## Regenerating",
        "",
        "From `agent-backend/`, with `GROQ_API_KEY` set:",
        "",
        "```bash",
        "python scripts/capture_observability_traces.py",
        "```",
        "",
        "Ticket drafts go to a throwaway SQLite file, so the real `data/tickets.db` is untouched.",
        "",
    ]
    (OUTPUT_DIR / "README.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("scenarios", nargs="*", help=f"Default: all of {', '.join(SCENARIOS)}")
    parser.add_argument(
        "--pause", type=float, default=5.0, help="Seconds between scenarios, to stay under Groq rate limits."
    )
    args = parser.parse_args()
    names = args.scenarios or list(SCENARIOS)
    unknown = [n for n in names if n not in SCENARIOS]
    if unknown:
        parser.error(f"unknown scenario(s): {', '.join(unknown)}")

    base = Settings()
    if not base.groq_configured:
        print("GROQ_API_KEY is not set in .env - the normal and boundary runs need the real model.")
        return 1

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    results = {}
    with tempfile.TemporaryDirectory() as tmp:
        for i, name in enumerate(names):
            if i:
                time.sleep(args.pause)
            results[name] = capture(name, SCENARIOS[name], base, Path(tmp))
    write_index()
    return 0 if all(all(ok for _, ok, _ in checks) for _, checks in results.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
