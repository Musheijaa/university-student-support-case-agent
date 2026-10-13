"""Per-run trace recorder for the bounded agent.

A RunTrace is built up alongside AgentState as the orchestrator moves
through Sense -> Context -> Plan/Decide -> Act/Tool -> Observe -> Stop.
It records what AgentState doesn't: the model parameters and prompt
fingerprint used, every retrieval candidate with its relevance score
(including the ones dropped below the threshold), per-call and
per-iteration latency, token usage, provider request ids, and a stable
error code for every failure.

Every `record_*` call also emits one structured log line (see
observability/structured_logging.py), so the same facts are available
live in the logs and afterwards in the exported trace file.

Schema: docs/observability.md. Bump SCHEMA_VERSION on breaking changes.
"""

import hashlib
import logging
from datetime import datetime, timezone
from time import perf_counter
from typing import Any

logger = logging.getLogger("agent.trace")

SCHEMA_VERSION = "trace-v1"
TEXT_PREVIEW_CHARS = 200

# Status recorded when a run raises before reaching a contract terminal
# status (e.g. Groq not configured, vector store down). Not an AgentStatus:
# the API turns these into 5xx responses, but the trace still closes.
ABORTED = "aborted"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def elapsed_ms(start: float) -> float:
    return round((perf_counter() - start) * 1000, 1)


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def preview(text: str | None, limit: int = TEXT_PREVIEW_CHARS) -> str | None:
    if text is None:
        return None
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


class RunTrace:
    def __init__(self, run_id: str, request: dict[str, Any]):
        self.run_id = run_id
        # Where the run currently is; used to attribute an unexpected exception.
        self.stage = "setup"
        self._t0 = perf_counter()
        self.data: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "run_id": run_id,
            "started_at": now_iso(),
            "ended_at": None,
            "total_latency_ms": None,
            "request": request,
            "config": {},
            "retrieval": None,
            "iterations": [],
            "errors": [],
            "terminal": None,
        }
        self._emit("agent.run.started", request=request)

    # -- logging -----------------------------------------------------------

    def _emit(self, event: str, level: int = logging.INFO, **fields: Any) -> None:
        logger.log(
            level,
            event,
            extra={"trace_event": {"run_id": self.run_id, "t_ms": elapsed_ms(self._t0), **fields}},
        )

    # -- Sense / Context ---------------------------------------------------

    def record_config(self, config: dict[str, Any]) -> None:
        self.data["config"] = config
        self._emit("agent.run.config", **config)

    def record_retrieval(
        self,
        *,
        query: str,
        top_k: int,
        min_score: float,
        latency_ms: float,
        kept: list,
        rejected: list,
    ) -> None:
        candidates = [(c, True) for c in kept] + [(c, False) for c in rejected]
        candidates.sort(key=lambda pair: pair[0].score, reverse=True)
        self.data["retrieval"] = {
            "query": query,
            "top_k": top_k,
            "min_score": min_score,
            "latency_ms": latency_ms,
            "kept_count": len(kept),
            "rejected_count": len(rejected),
            "chunks": [
                {
                    "rank": rank,
                    "chunk_id": chunk.chunk_id or None,
                    "document_id": chunk.document_id,
                    "document": chunk.document_name,
                    "page": chunk.page,
                    "relevance_score": round(chunk.score, 4),
                    "used_as_evidence": used,
                    "text_preview": preview(chunk.text),
                }
                for rank, (chunk, used) in enumerate(candidates, start=1)
            ],
        }
        self._emit(
            "agent.retrieval",
            latency_ms=latency_ms,
            kept=len(kept),
            rejected=len(rejected),
            scores=[c["relevance_score"] for c in self.data["retrieval"]["chunks"]],
        )

    # -- Plan/Decide, Act/Tool, Observe (one iteration each) ---------------

    def start_iteration(self, iteration: int, *, tools_offered: list[str], tool_choice: str) -> dict:
        record = {
            "iteration": iteration,
            "started_at": now_iso(),
            "latency_ms": None,
            "decisions": [],
            "llm_call": {"tools_offered": tools_offered, "tool_choice": tool_choice},
            "tool_calls": [],
            "_t0": perf_counter(),
        }
        self.data["iterations"].append(record)
        return record

    def record_llm_call(
        self,
        record: dict,
        *,
        latency_ms: float,
        message_count: int,
        call_info: dict | None,
        content: str | None = None,
        requested_tools: list[str] | None = None,
        error_code: str | None = None,
        error: str | None = None,
    ) -> None:
        call_info = call_info or {}
        record["llm_call"].update(
            {
                "latency_ms": latency_ms,
                "input_message_count": message_count,
                "provider_request_id": call_info.get("provider_request_id"),
                "finish_reason": call_info.get("finish_reason"),
                "usage": call_info.get("usage"),
                "requested_tools": requested_tools or [],
                "content_preview": preview(content),
                "error_code": error_code,
                "error": error,
            }
        )
        if error_code:
            self.record_error(error_code, "llm", error or "", iteration=record["iteration"])
        self._emit(
            "agent.llm_call",
            level=logging.WARNING if error_code else logging.INFO,
            iteration=record["iteration"],
            **{k: v for k, v in record["llm_call"].items() if k != "content_preview"},
        )

    def record_tool_call(
        self,
        record: dict,
        *,
        tool_call_id: str | None,
        tool_name: str,
        arguments: dict,
        arguments_raw: str | None,
        approved: bool,
        executed: bool,
        latency_ms: float | None = None,
        response: dict | None = None,
        error_code: str | None = None,
        observation: str | None = None,
    ) -> None:
        entry = {
            "tool_call_id": tool_call_id,
            "tool_name": tool_name,
            "arguments": arguments,
            "approved": approved,
            "executed": executed,
            "latency_ms": latency_ms,
            "success": None if response is None else bool(response.get("success")),
            "response": response,
            "error_code": error_code,
            "observation": observation,
        }
        if arguments_raw is not None:
            entry["arguments_raw"] = arguments_raw  # only kept when it didn't parse as a JSON object
        record["tool_calls"].append(entry)
        self._emit(
            "agent.tool_call",
            level=logging.WARNING if error_code else logging.INFO,
            iteration=record["iteration"],
            **entry,
        )

    def end_iteration(self, record: dict, decisions: list[str]) -> None:
        record["latency_ms"] = elapsed_ms(record.pop("_t0"))
        record["decisions"] = decisions
        self._emit(
            "agent.iteration",
            iteration=record["iteration"],
            latency_ms=record["latency_ms"],
            decisions=decisions,
        )

    # -- Errors and Stop ---------------------------------------------------

    def record_error(self, code: str, stage: str, message: str, iteration: int | None = None) -> None:
        self.data["errors"].append(
            {"code": code, "stage": stage, "iteration": iteration, "message": message, "at": now_iso()}
        )
        self._emit("agent.error", level=logging.WARNING, code=code, stage=stage, iteration=iteration, message=message)

    def finish(
        self,
        status: str,
        *,
        response: str,
        error_code: str | None,
        iteration_count: int,
        tool_call_count: int,
        drafted_ticket_ids: list[str],
    ) -> dict:
        total = elapsed_ms(self._t0)
        retrieval_ms = (self.data["retrieval"] or {}).get("latency_ms") or 0.0
        llm_ms = sum(it["llm_call"].get("latency_ms") or 0.0 for it in self.data["iterations"])
        tool_ms = sum(
            tc["latency_ms"] or 0.0 for it in self.data["iterations"] for tc in it["tool_calls"]
        )
        tokens = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        for it in self.data["iterations"]:
            for key in tokens:
                tokens[key] += ((it["llm_call"].get("usage") or {}).get(key)) or 0

        self.data["ended_at"] = now_iso()
        self.data["total_latency_ms"] = total
        self.data["terminal"] = {
            "status": status,
            "error_code": error_code,
            "iteration_count": iteration_count,
            "tool_call_count": tool_call_count,
            "drafted_ticket_ids": drafted_ticket_ids,
            "response": response,
            "latency_breakdown_ms": {
                "retrieval": retrieval_ms,
                "llm": round(llm_ms, 1),
                "tools": round(tool_ms, 1),
                "orchestration_overhead": round(max(total - retrieval_ms - llm_ms - tool_ms, 0.0), 1),
                "total": total,
            },
            "token_usage": tokens,
        }
        self._emit(
            "agent.run.finished",
            level=logging.INFO if error_code is None else logging.WARNING,
            **{k: v for k, v in self.data["terminal"].items() if k != "response"},
        )
        return self.data
