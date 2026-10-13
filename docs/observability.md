# Observability & End-to-End Tracing

## 1. Purpose

Every run of the bounded agent (`POST /api/v1/agent/student-support`) has
to be **transparent** (you can see what it did while it runs),
**inspectable** (you can open one run and see why it did it), and
**auditable** (you can show afterwards exactly which model, prompt,
evidence and tool results produced an answer, and how the run ended).

This is done with three mechanisms, all in `agent-backend/observability/`:

| Mechanism | Where | What it gives you |
|---|---|---|
| **Run trace** | `trace.py` (`RunTrace`) | One structured document per run covering every cognitive step |
| **Structured logging** | `structured_logging.py` | One log line per step, live, as JSON (`LOG_FORMAT=json`) or readable text |
| **Trace export** | `export.py` | Each finished trace written as `<run_id>.json` + `<run_id>.md` |

Stable error codes (`error_codes.py`) tie the three together: the same
code appears in the log line, the trace, the API response, and the
evidence files.

## 2. What is captured at each cognitive step

The agent loop is Sense → Context → Plan/Decide → Act/Tool → Observe →
Stop (see [agent-task-contract.md](agent-task-contract.md)). Each step
records the following:

| Step | Requirement | Trace field | Log event |
|---|---|---|---|
| Sense | request, actor | `request.message`, `request.actor_role`, `request.actor_id` | `agent.run.started` |
| Sense | model parameters | `config.model` (provider, name, temperature, max_tokens, timeout_seconds, max_retries) | `agent.run.config` |
| Sense | prompt version | `config.prompt.version`, `config.prompt.system_prompt_sha256` | `agent.run.config` |
| Sense | tool schema version | `config.tools.definitions_sha256` | `agent.run.config` |
| Context | retrieved RAG chunks + relevance scores | `retrieval.chunks[]`: rank, document, page, chunk_id, `relevance_score`, `used_as_evidence`, text preview. Candidates **below `min_score` are kept too**, flagged `used_as_evidence: false` | `agent.retrieval` |
| Context | retrieval latency | `retrieval.latency_ms` | `agent.retrieval` |
| Plan/Decide | model call | `iterations[].llm_call`: tools offered, tool_choice, input message count, latency, finish reason, token usage, provider request id, requested tools, content preview | `agent.llm_call` |
| Act/Tool | tool arguments | `iterations[].tool_calls[].arguments` (plus `arguments_raw` if they weren't valid JSON) | `agent.tool_call` |
| Act/Tool | tool responses | `iterations[].tool_calls[].response`, `success`, `approved`, `executed` | `agent.tool_call` |
| Act/Tool | tool latency | `iterations[].tool_calls[].latency_ms` | `agent.tool_call` |
| Observe | observation fed back to the model | `iterations[].tool_calls[].observation` | `agent.tool_call` |
| (every iteration) | latency per iteration | `iterations[].latency_ms`, `iterations[].decisions` | `agent.iteration` |
| (any) | error codes | `errors[]` (code, stage, iteration, message, timestamp), and `error_code` on the failing LLM/tool call | `agent.error` |
| Stop | final terminal status | `terminal.status`, `terminal.error_code`, counts, drafted tickets, response, `latency_breakdown_ms`, `token_usage` | `agent.run.finished` |

Human actions outside the agent are audit-logged too. Every staff
approve/reject call, and every refused attempt by a non-staff caller,
emits `ticket.approve`, `ticket.reject`, `ticket.approve.denied` or
`ticket.reject.denied` on the `audit` logger, with actor and ticket id.

### Why a hash of the prompt, not just a version

`agent-v1.0` is a label someone has to remember to bump. The SHA-256 of
the system prompt (and of the tool definitions) changes automatically
when the text changes, so two traces with the same version but different
hashes show at once that the prompt was edited without a version bump.

### Why rejected chunks are recorded

The model only ever sees chunks at or above `rag_min_score`. To audit
*why* an answer had no evidence, or had the wrong evidence, you need
the candidates that were filtered out as well. They are recorded in the
trace only and never added to the prompt (see
`rag/retriever.py: retrieve_with_rejected`).

## 3. Every run ends in exactly one terminal status

`terminal.status` is always one of the contract's terminal statuses,
or `aborted`:

| Status | Error code | Meaning |
|---|---|---|
| `completed` | — | Final answer, no ticket drafted |
| `human_approval_required` | — | Final answer after drafting a ticket; staff take over |
| `tool_not_approved` | `AGENT_TOOL_NOT_APPROVED` | Model asked for a tool outside the contract; not executed |
| `max_tool_calls_reached` | `AGENT_TOOL_BUDGET_EXHAUSTED` | Tool budget spent |
| `max_iterations_reached` | `AGENT_ITERATION_BUDGET_EXHAUSTED` | Iteration budget spent |
| `llm_error` | `LLM_*` | Model provider failed; safe message returned |
| `aborted` | `LLM_NOT_CONFIGURED`, `RETRIEVAL_ERROR`, `AGENT_UNHANDLED_EXCEPTION` | The run raised before reaching a contract status. The API returns 503/500, but the trace is still closed, logged and exported **before** the exception propagates |

`aborted` exists only in traces. It is not an `AgentStatus`: a run that
raises never returns a state, but it must not disappear from the audit
trail either.

## 4. Error code catalogue

Defined in `agent-backend/observability/error_codes.py`. Messages can be
reworded; codes cannot.

| Code | Stage | Raised when |
|---|---|---|
| `LLM_NOT_CONFIGURED` | config | `GROQ_API_KEY` empty |
| `LLM_TIMEOUT` | llm | Groq request exceeded `llm_timeout_seconds` |
| `LLM_CONNECTION_ERROR` | llm | Groq unreachable (DNS, network) |
| `LLM_RATE_LIMITED` | llm | Groq returned 429 |
| `LLM_HTTP_ERROR_<status>` | llm | Any other Groq error status (e.g. `LLM_HTTP_ERROR_401` for a rejected key) |
| `LLM_API_ERROR` | llm | Any other Groq SDK error |
| `LLM_EMPTY_RESPONSE` | llm | Groq returned no choices / empty content |
| `RETRIEVAL_ERROR` | retrieval | Vector store raised |
| `TOOL_UNKNOWN` | tool | Tool name not in the registry |
| `TOOL_INVALID_JSON` | tool | Tool arguments not valid JSON |
| `TOOL_UNAUTHORIZED` | tool | Actor's role may not use the tool |
| `TOOL_INVALID_INPUT` | tool | Arguments failed schema validation |
| `TOOL_DATA_UNAVAILABLE` | tool | Timetable file missing/unreadable |
| `TOOL_STORE_UNAVAILABLE` | tool | Ticket database error |
| `TOOL_UNEXPECTED_ERROR` | tool | Any other exception inside a tool |
| `TOOL_OUTPUT_INVALID` | tool | Tool output failed schema validation |
| `TOOL_NO_RESULT` | tool | Tool ran but reported `success: false` (e.g. unknown course code) |
| `AGENT_TOOL_NOT_APPROVED` | contract | See §3 |
| `AGENT_TOOL_BUDGET_EXHAUSTED` | contract | See §3 |
| `AGENT_ITERATION_BUDGET_EXHAUSTED` | contract | See §3 |
| `AGENT_UNHANDLED_EXCEPTION` | any | Unexpected exception anywhere else in the run |

Tool failures (`TOOL_*`) don't end the run. The agent observes them and
re-plans, so a run can end `completed` with tool errors in `errors[]`.
`error_03_tool_service_unavailable` in the evidence shows this.

## 5. Trace schema (`trace-v1`)

```text
schema_version       "trace-v1"
run_id               UUID4, same as the API response's run_id
started_at/ended_at  ISO-8601 UTC, millisecond precision
total_latency_ms
request              {message, actor_role, actor_id}
config               {model{...}, prompt{version, system_prompt_sha256, system_prompt_chars},
                      tools{defined, definitions_sha256}, contract{max_iterations, max_tool_calls,
                      approved_tools}, rag{collection, embedding_model, top_k, min_score}, app{name, env}}
retrieval            null if the run aborted first, else
                     {query, top_k, min_score, latency_ms, kept_count, rejected_count,
                      chunks[{rank, chunk_id, document_id, document, page, relevance_score,
                              used_as_evidence, text_preview}]}
iterations[]         {iteration, started_at, latency_ms, decisions[],
                      llm_call{tools_offered, tool_choice, latency_ms, input_message_count,
                               provider_request_id, finish_reason, usage{prompt_tokens,
                               completion_tokens, total_tokens}, requested_tools, content_preview,
                               error_code, error},
                      tool_calls[{tool_call_id, tool_name, arguments, [arguments_raw], approved,
                                  executed, latency_ms, success, response, error_code, observation}]}
errors[]             {code, stage, iteration, message, at}
terminal             {status, error_code, iteration_count, tool_call_count, drafted_ticket_ids,
                      response, latency_breakdown_ms{retrieval, llm, tools,
                      orchestration_overhead, total}, token_usage{prompt_tokens,
                      completion_tokens, total_tokens}}
```

Bump `SCHEMA_VERSION` in `trace.py` for any breaking change.

## 6. Using it

**Configuration** (`.env` / environment):

| Setting | Default | Effect |
|---|---|---|
| `LOG_FORMAT` | `text` | `json` writes one JSON object per log line, ready for `jq` or a log stack |
| `TRACE_EXPORT_DIR` | `data/traces` | Where `<run_id>.json` / `.md` are written. Empty disables file export; log lines are still emitted |
| `LLM_TEMPERATURE`, `LLM_MAX_TOKENS`, `LLM_TIMEOUT_SECONDS`, `LLM_MAX_RETRIES` | `0.2`, `1500`, `20`, `2` | Model parameters. They used to be hard-coded in `llm/client.py`; now they are config, so the trace can record what was actually used |

**Live**: `LOG_FORMAT=json uvicorn main:app`, then for example
`... | jq 'select(.event=="agent.tool_call") | {run_id, tool_name, latency_ms, error_code}'`.

**One run, after the fact**: the agent response includes `run_id`,
`error_code`, `total_latency_ms` and a per-step `latency_ms`. A staff
caller can fetch the full trace:

```bash
curl -H "X-User-Role: staff" http://127.0.0.1:8000/api/v1/agent/traces/<run_id>
```

Students get `403`: a trace holds the student's message and tool
arguments, so only the people auditing runs can read it. The run id is
validated as a UUID before it touches the filesystem.

## 7. Evidence

[`evidence/traces/observability/`](../evidence/traces/observability/README.md)
holds 10 representative traces: 3 normal, 3 boundary and 4 error. Each
was captured as a real run (real Groq, real Chroma, real tools) by
`agent-backend/scripts/capture_observability_traces.py`. The error runs
use configuration-only fault injection: a 200 ms timeout, a rejected
key, a missing timetable file, and no key. Each trace is saved as JSON,
as Markdown, and as the JSONL log stream emitted during the run. The
index runs an observability-completeness checklist against every trace,
and all pass.

`agent-backend/tests/test_observability.py` (25 tests) covers the same
paths deterministically with a scripted model.

## 8. What the traces have already shown

The first capture surfaced issues that the Week 5 step list could not
show:

1. **`rag_min_score = 0.35` is too permissive.** The out-of-scope
   question *"Which restaurant in Kampala serves the best rolex?"*
   (`boundary_02`) kept **4 chunks from the JAB admissions booklet**
   (scores 0.397–0.448) as evidence, apparently on the strength of the
   word "Kampala". The model correctly declined to answer, but it was
   handed irrelevant evidence. On-topic policy questions score 0.58–0.70
   (`normal_02`), and timetable questions top out around 0.31, so a
   threshold of roughly 0.5 looks better supported. This should be
   re-evaluated against `docs/rag-evaluation.md` before changing it.
2. **Retrieval missed the chunk the answer needed.** In `normal_02`, all
   four chunks came from the right document (pages 2, 3, 5, 6 of the
   malpractice rules, scores 0.58–0.70). Even so, the model reported that
   the penalty for Rule 4 wasn't in the evidence. The trace makes this
   checkable: either the page holding Rule 4's penalty ranked below
   top-k 4, or chunking split the rule from its penalty.
3. **Latency is almost entirely the model.** Across the successful runs,
   retrieval took about 300–650 ms, tools under 7 ms, and orchestration
   about 50 ms. LLM calls took 1.3–22.7 s: 94–98% of total time in
   every run except the fastest (`normal_01`, 64%). Speed
   work should target the model call (smaller prompts, fewer iterations,
   streaming), not retrieval or tools.
4. **The 1 ms timeout was really a connection error.** Our first fault
   injection of a 1 ms timeout came back as `LLM_CONNECTION_ERROR`, not
   `LLM_TIMEOUT`, because the socket never connected. A back-to-back
   re-run then hit `LLM_RATE_LIMITED`. The completeness check failed both
   times, as it should have. The evidence uses a 200 ms read timeout,
   which produces a genuine `LLM_TIMEOUT`. The capture script now pauses
   between scenarios.

## 9. Limitations / not done

- **Only the agent endpoint is traced.** The Week 4
  `/api/v1/student-support` path (`llm/service.py`) still logs only what
  it did before. It is the legacy mode; instrumenting it would reuse
  `RunTrace` the same way.
- **No distributed tracing.** Traces are per-process JSON files plus log
  lines, not OpenTelemetry spans. `run_id` and the provider request id
  are the correlation keys. Mapping `RunTrace` onto OTel spans would be
  the next step if the backend is ever split into services.
- **No retention policy.** `data/traces/` grows without bound and holds
  student messages in plain text. Before any real deployment it needs
  rotation and a retention period, and probably redaction of
  `request.message` and tool arguments.
- **Token usage is as reported by Groq.** It is not recomputed locally.
  SDK-internal retries (`LLM_MAX_RETRIES`) happen inside one recorded LLM
  call, so a retried call shows as one longer call.
