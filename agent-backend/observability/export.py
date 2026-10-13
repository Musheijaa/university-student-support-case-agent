"""Export a run trace as JSON (machine-readable) and Markdown (for reviewers)."""

import json
import re
from pathlib import Path
from typing import Any

_RUN_ID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")


def is_valid_run_id(run_id: str) -> bool:
    """Run ids are UUID4s; checking the shape also keeps them safe to use as file names."""
    return bool(_RUN_ID.match(run_id))


def write_trace(trace: dict[str, Any], directory: str | Path, stem: str | None = None) -> tuple[Path, Path]:
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    stem = stem or trace["run_id"]
    json_path = directory / f"{stem}.json"
    md_path = directory / f"{stem}.md"
    json_path.write_text(json.dumps(trace, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(trace, title=stem), encoding="utf-8")
    return json_path, md_path


def load_trace(directory: str | Path, run_id: str) -> dict[str, Any] | None:
    if not is_valid_run_id(run_id):
        return None
    path = Path(directory) / f"{run_id}.json"
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _cell(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, (dict, list)):
        value = json.dumps(value, ensure_ascii=False)
    return str(value).replace("|", "\\|").replace("\n", " ")


def _code(value: Any) -> str:
    return "—" if value is None else f"`{_cell(value)}`"


def render_markdown(trace: dict[str, Any], title: str | None = None) -> str:
    config = trace.get("config") or {}
    model = config.get("model") or {}
    prompt = config.get("prompt") or {}
    contract = config.get("contract") or {}
    terminal = trace.get("terminal") or {}
    request = trace.get("request") or {}
    breakdown = terminal.get("latency_breakdown_ms") or {}
    tokens = terminal.get("token_usage") or {}

    lines = [
        f"# Trace: {title or trace.get('run_id')}",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Run ID | {_code(trace.get('run_id'))} |",
        f"| Terminal status | **{_code(terminal.get('status'))}** |",
        f"| Error code | {_code(terminal.get('error_code'))} |",
        f"| Started / ended | {_cell(trace.get('started_at'))} → {_cell(trace.get('ended_at'))} |",
        f"| Total latency | {_cell(trace.get('total_latency_ms'))} ms |",
        f"| Iterations / tool calls | {_cell(terminal.get('iteration_count'))} / {_cell(terminal.get('tool_call_count'))} |",
        f"| Model | {_code(model.get('name'))} via {_cell(model.get('provider'))} |",
        f"| Model parameters | temperature={_cell(model.get('temperature'))}, max_tokens={_cell(model.get('max_tokens'))}, "
        f"timeout={_cell(model.get('timeout_seconds'))}s, max_retries={_cell(model.get('max_retries'))} |",
        f"| Prompt version | {_code(prompt.get('version'))} (system prompt sha256 `{(prompt.get('system_prompt_sha256') or '')[:12]}…`) |",
        f"| Tool definitions sha256 | `{((config.get('tools') or {}).get('definitions_sha256') or '')[:12]}…` |",
        f"| Contract budget | {_cell(contract.get('max_iterations'))} iteration(s), {_cell(contract.get('max_tool_calls'))} tool call(s); "
        f"approved: {_cell(', '.join(contract.get('approved_tools') or []))} |",
        f"| Tokens (prompt / completion / total) | {tokens.get('prompt_tokens', 0)} / {tokens.get('completion_tokens', 0)} / {tokens.get('total_tokens', 0)} |",
        "",
        "## Request",
        "",
        f"**Actor:** `{_cell(request.get('actor_role'))}` / `{_cell(request.get('actor_id'))}`",
        "",
        f"> {_cell(request.get('message'))}",
        "",
        "## Context: retrieval",
        "",
    ]

    retrieval = trace.get("retrieval")
    if retrieval is None:
        lines += ["_Retrieval did not run._", ""]
    else:
        lines += [
            f"top_k={retrieval['top_k']}, min_score={retrieval['min_score']}, latency={retrieval['latency_ms']} ms — "
            f"**{retrieval['kept_count']} used as evidence, {retrieval['rejected_count']} below threshold**",
            "",
        ]
        if retrieval["chunks"]:
            lines += [
                "| Rank | Score | Used | Document | Page | Text preview |",
                "|---|---|---|---|---|---|",
            ]
            for c in retrieval["chunks"]:
                lines.append(
                    f"| {c['rank']} | {c['relevance_score']:.4f} | {'✓' if c['used_as_evidence'] else '✗'} | "
                    f"{_cell(c['document'])} | {c['page']} | {_cell(c['text_preview'])} |"
                )
            lines.append("")
        else:
            lines += ["_The vector store returned no candidates._", ""]

    lines += ["## Iterations", ""]
    if not trace.get("iterations"):
        lines += ["_No iterations ran._", ""]
    for it in trace.get("iterations") or []:
        llm = it.get("llm_call") or {}
        usage = llm.get("usage") or {}
        lines += [
            f"### Iteration {it['iteration']} — {_cell(', '.join(it.get('decisions') or []))} ({_cell(it.get('latency_ms'))} ms)",
            "",
            "| LLM call | Value |",
            "|---|---|",
            f"| Latency | {_cell(llm.get('latency_ms'))} ms |",
            f"| Tools offered / tool_choice | {_cell(', '.join(llm.get('tools_offered') or []) or 'none')} / `{_cell(llm.get('tool_choice'))}` |",
            f"| Input messages | {_cell(llm.get('input_message_count'))} |",
            f"| Finish reason | {_code(llm.get('finish_reason'))} |",
            f"| Tokens (prompt / completion) | {_cell(usage.get('prompt_tokens'))} / {_cell(usage.get('completion_tokens'))} |",
            f"| Provider request id | {_code(llm.get('provider_request_id'))} |",
            f"| Requested tools | {_cell(', '.join(llm.get('requested_tools') or []) or 'none')} |",
            f"| Error code | {_code(llm.get('error_code'))} |",
        ]
        if llm.get("error"):
            lines.append(f"| Error | {_cell(llm['error'])} |")
        if llm.get("content_preview"):
            lines.append(f"| Content preview | {_cell(llm['content_preview'])} |")
        lines.append("")
        for tc in it.get("tool_calls") or []:
            status = "not executed" if not tc["executed"] else ("✓ success" if tc["success"] else "✗ failed")
            lines += [
                f"**Tool `{tc['tool_name']}`** — {status}"
                + (f" in {tc['latency_ms']} ms" if tc.get("latency_ms") is not None else "")
                + f" · approved={tc['approved']} · error_code={_code(tc.get('error_code'))}",
                "",
                f"- Arguments: `{_cell(tc['arguments'])}`",
            ]
            if "arguments_raw" in tc:
                lines.append(f"- Raw arguments (unparseable): `{_cell(tc['arguments_raw'])}`")
            if tc.get("response") is not None:
                lines.append(f"- Response: `{_cell(tc['response'])}`")
            if tc.get("observation"):
                lines.append(f"- Observation: {_cell(tc['observation'])}")
            lines.append("")

    lines += ["## Errors", ""]
    if trace.get("errors"):
        lines += ["| Code | Stage | Iteration | Message |", "|---|---|---|---|"]
        for e in trace["errors"]:
            lines.append(f"| `{e['code']}` | {e['stage']} | {_cell(e.get('iteration'))} | {_cell(e['message'])} |")
    else:
        lines.append("_None._")
    lines += [
        "",
        "## Latency breakdown (ms)",
        "",
        "| Retrieval | LLM | Tools | Orchestration overhead | Total |",
        "|---|---|---|---|---|",
        f"| {_cell(breakdown.get('retrieval'))} | {_cell(breakdown.get('llm'))} | {_cell(breakdown.get('tools'))} | "
        f"{_cell(breakdown.get('orchestration_overhead'))} | {_cell(breakdown.get('total'))} |",
        "",
        "## Final response",
        "",
        terminal.get("response") or "_(empty)_",
        "",
    ]
    if terminal.get("drafted_ticket_ids"):
        lines += [f"**Drafted tickets (awaiting staff approval):** {', '.join(terminal['drafted_ticket_ids'])}", ""]
    return "\n".join(lines)
