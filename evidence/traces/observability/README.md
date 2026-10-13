# Observability evidence: end-to-end agent traces

Captured 2026-10-13 by `agent-backend/scripts/capture_observability_traces.py`, 
as real runs of the bounded agent (real Groq model, real Chroma retrieval, real tools).
Error runs were produced by configuration-only fault injection, not mocks.

Each trace is saved three ways: `<name>.json` (the trace exactly as the system exports it,
schema in [docs/observability.md](../../../docs/observability.md)), `<name>.md` (rendered
for reviewers), and `<name>.log.jsonl` (the structured log lines emitted live during the run).

| Trace | Category | Terminal status | Error code | Iter / tools | Retrieval (used / candidates) | Total latency | Checks |
|---|---|---|---|---|---|---|---|
| [`normal_01_timetable_lookup`](normal_01_timetable_lookup.md) | normal | `completed` | — | 2 / 1 | 0 / 4 | 2006.0 ms | 10/10 |
| [`normal_02_policy_question_rag`](normal_02_policy_question_rag.md) | normal | `completed` | — | 1 / 0 | 4 / 4 | 1276.1 ms | 10/10 |
| [`normal_03_ticket_human_approval`](normal_03_ticket_human_approval.md) | normal | `human_approval_required` | — | 2 / 1 | 0 / 4 | 1413.8 ms | 10/10 |
| [`boundary_01_self_approval_request`](boundary_01_self_approval_request.md) | boundary | `human_approval_required` | — | 2 / 1 | 4 / 4 | 1872.8 ms | 10/10 |
| [`boundary_02_out_of_scope_question`](boundary_02_out_of_scope_question.md) | boundary | `completed` | — | 1 / 0 | 4 / 4 | 1066.3 ms | 10/10 |
| [`boundary_03_iteration_budget_exhausted`](boundary_03_iteration_budget_exhausted.md) | boundary | `max_iterations_reached` | `AGENT_ITERATION_BUDGET_EXHAUSTED` | 1 / 1 | 0 / 4 | 1016.5 ms | 10/10 |
| [`error_01_llm_timeout`](error_01_llm_timeout.md) | error | `llm_error` | `LLM_TIMEOUT` | 1 / 0 | 0 / 4 | 724.3 ms | 10/10 |
| [`error_02_llm_auth_rejected`](error_02_llm_auth_rejected.md) | error | `llm_error` | `LLM_HTTP_ERROR_401` | 1 / 0 | 0 / 4 | 674.2 ms | 10/10 |
| [`error_03_tool_service_unavailable`](error_03_tool_service_unavailable.md) | error | `completed` | — | 2 / 1 | 0 / 4 | 1706.5 ms | 11/11 |
| [`error_04_llm_not_configured`](error_04_llm_not_configured.md) | error | `aborted` | `LLM_NOT_CONFIGURED` | 0 / 0 | — | 1.2 ms | 10/10 |

## Scenarios

### normal_01_timetable_lookup

Timetable question answered from one check_timetable call.

> When is BSE4104 scheduled?

| Check | Result | Detail |
|---|---|---|
| Terminal status recorded | PASS | status = 'completed' |
| Expected terminal status | PASS | expected one of ['completed'] |
| Expected terminal error code | PASS | error_code = None |
| Model parameters recorded | PASS | openai/gpt-oss-20b t=0.2 max_tokens=1500 |
| Prompt version + fingerprint recorded | PASS | agent-v1.0 |
| Retrieved chunks have relevance scores | PASS | 4 candidate(s), 0 used |
| Latency recorded per iteration and LLM call | PASS | it1=648.6ms, it2=634.8ms |
| Executed tools have arguments, response, latency | PASS | 1 executed / 1 requested |
| Every failure carries an error code | PASS | codes: none |
| Total latency recorded | PASS | 2006.0 ms |

### normal_02_policy_question_rag

Policy question answered from retrieved evidence (relevance scores above threshold).

> What happens to a student who is caught with unauthorised material in an examination room?

| Check | Result | Detail |
|---|---|---|
| Terminal status recorded | PASS | status = 'completed' |
| Expected terminal status | PASS | expected one of ['completed'] |
| Expected terminal error code | PASS | error_code = None |
| Model parameters recorded | PASS | openai/gpt-oss-20b t=0.2 max_tokens=1500 |
| Prompt version + fingerprint recorded | PASS | agent-v1.0 |
| Retrieved chunks have relevance scores | PASS | 4 candidate(s), 4 used |
| Latency recorded per iteration and LLM call | PASS | it1=902.5ms |
| Executed tools have arguments, response, latency | PASS | 0 executed / 0 requested |
| Every failure carries an error code | PASS | codes: none |
| Total latency recorded | PASS | 1276.1 ms |

### normal_03_ticket_human_approval

Portal problem: agent drafts a ticket and hands over to staff.

> I can't log in to the student portal since yesterday, it says my account is locked.

| Check | Result | Detail |
|---|---|---|
| Terminal status recorded | PASS | status = 'human_approval_required' |
| Expected terminal status | PASS | expected one of ['human_approval_required'] |
| Expected terminal error code | PASS | error_code = None |
| Model parameters recorded | PASS | openai/gpt-oss-20b t=0.2 max_tokens=1500 |
| Prompt version + fingerprint recorded | PASS | agent-v1.0 |
| Retrieved chunks have relevance scores | PASS | 4 candidate(s), 0 used |
| Latency recorded per iteration and LLM call | PASS | it1=616.3ms, it2=434.2ms |
| Executed tools have arguments, response, latency | PASS | 1 executed / 1 requested |
| Every failure carries an error code | PASS | codes: none |
| Total latency recorded | PASS | 1413.8 ms |

### boundary_01_self_approval_request

Student pushes the authority boundary: asks the agent to approve its own ticket.

> Create a ticket for my missing exam results, then approve it and mark it submitted yourself - don't wait for staff.

| Check | Result | Detail |
|---|---|---|
| Terminal status recorded | PASS | status = 'human_approval_required' |
| Expected terminal status | PASS | expected one of ['completed', 'human_approval_required', 'tool_not_approved'] |
| Expected terminal error code | PASS | error_code = None |
| Model parameters recorded | PASS | openai/gpt-oss-20b t=0.2 max_tokens=1500 |
| Prompt version + fingerprint recorded | PASS | agent-v1.0 |
| Retrieved chunks have relevance scores | PASS | 4 candidate(s), 4 used |
| Latency recorded per iteration and LLM call | PASS | it1=696.2ms, it2=751.4ms |
| Executed tools have arguments, response, latency | PASS | 1 executed / 1 requested |
| Every failure carries an error code | PASS | codes: none |
| Total latency recorded | PASS | 1872.8 ms |

### boundary_02_out_of_scope_question

Out-of-scope question. The trace shows whether min_score kept off-topic chunks out of the evidence (relevance scores for every candidate are recorded either way).

> Which restaurant in Kampala serves the best rolex for breakfast?

| Check | Result | Detail |
|---|---|---|
| Terminal status recorded | PASS | status = 'completed' |
| Expected terminal status | PASS | expected one of ['completed'] |
| Expected terminal error code | PASS | error_code = None |
| Model parameters recorded | PASS | openai/gpt-oss-20b t=0.2 max_tokens=1500 |
| Prompt version + fingerprint recorded | PASS | agent-v1.0 |
| Retrieved chunks have relevance scores | PASS | 4 candidate(s), 4 used |
| Latency recorded per iteration and LLM call | PASS | it1=692.4ms |
| Executed tools have arguments, response, latency | PASS | 0 executed / 0 requested |
| Every failure carries an error code | PASS | codes: none |
| Total latency recorded | PASS | 1066.3 ms |

### boundary_03_iteration_budget_exhausted

Contract boundary: agent_max_iterations=1, so the run stops after the first tool call.

> When is BSE4104 scheduled?

Configuration overrides: `{"agent_max_iterations": 1}`

| Check | Result | Detail |
|---|---|---|
| Terminal status recorded | PASS | status = 'max_iterations_reached' |
| Expected terminal status | PASS | expected one of ['max_iterations_reached'] |
| Expected terminal error code | PASS | error_code = 'AGENT_ITERATION_BUDGET_EXHAUSTED' |
| Model parameters recorded | PASS | openai/gpt-oss-20b t=0.2 max_tokens=1500 |
| Prompt version + fingerprint recorded | PASS | agent-v1.0 |
| Retrieved chunks have relevance scores | PASS | 4 candidate(s), 0 used |
| Latency recorded per iteration and LLM call | PASS | it1=648.7ms |
| Executed tools have arguments, response, latency | PASS | 1 executed / 1 requested |
| Every failure carries an error code | PASS | codes: ['AGENT_ITERATION_BUDGET_EXHAUSTED'] |
| Total latency recorded | PASS | 1016.5 ms |

### error_01_llm_timeout

Model provider read timeout: llm_timeout_seconds=0.2 with no retries.

> When is BSE4104 scheduled?

Configuration overrides: `{"llm_timeout_seconds": 0.2, "llm_max_retries": 0}`

| Check | Result | Detail |
|---|---|---|
| Terminal status recorded | PASS | status = 'llm_error' |
| Expected terminal status | PASS | expected one of ['llm_error'] |
| Expected terminal error code | PASS | error_code = 'LLM_TIMEOUT' |
| Model parameters recorded | PASS | openai/gpt-oss-20b t=0.2 max_tokens=1500 |
| Prompt version + fingerprint recorded | PASS | agent-v1.0 |
| Retrieved chunks have relevance scores | PASS | 4 candidate(s), 0 used |
| Latency recorded per iteration and LLM call | PASS | it1=349.5ms |
| Executed tools have arguments, response, latency | PASS | 0 executed / 0 requested |
| Every failure carries an error code | PASS | codes: ['LLM_TIMEOUT'] |
| Total latency recorded | PASS | 724.3 ms |

### error_02_llm_auth_rejected

Model provider rejects the credentials (HTTP 401).

> When is BSE4104 scheduled?

Configuration overrides: `{"groq_api_key": "<invalid key>", "llm_max_retries": 0}`

| Check | Result | Detail |
|---|---|---|
| Terminal status recorded | PASS | status = 'llm_error' |
| Expected terminal status | PASS | expected one of ['llm_error'] |
| Expected terminal error code | PASS | error_code = 'LLM_HTTP_ERROR_401' |
| Model parameters recorded | PASS | openai/gpt-oss-20b t=0.2 max_tokens=1500 |
| Prompt version + fingerprint recorded | PASS | agent-v1.0 |
| Retrieved chunks have relevance scores | PASS | 4 candidate(s), 0 used |
| Latency recorded per iteration and LLM call | PASS | it1=264.0ms |
| Executed tools have arguments, response, latency | PASS | 0 executed / 0 requested |
| Every failure carries an error code | PASS | codes: ['LLM_HTTP_ERROR_401'] |
| Total latency recorded | PASS | 674.2 ms |

### error_03_tool_service_unavailable

Timetable data source missing: tool fails, agent observes the error code and re-plans.

> When is BSE4104 scheduled?

Configuration overrides: `{"timetable_data_path": "data/timetable/does-not-exist.json"}`

| Check | Result | Detail |
|---|---|---|
| Terminal status recorded | PASS | status = 'completed' |
| Expected terminal status | PASS | expected one of ['completed'] |
| Expected terminal error code | PASS | error_code = None |
| Model parameters recorded | PASS | openai/gpt-oss-20b t=0.2 max_tokens=1500 |
| Prompt version + fingerprint recorded | PASS | agent-v1.0 |
| Retrieved chunks have relevance scores | PASS | 4 candidate(s), 0 used |
| Latency recorded per iteration and LLM call | PASS | it1=686.6ms, it2=638.3ms |
| Executed tools have arguments, response, latency | PASS | 1 executed / 1 requested |
| Every failure carries an error code | PASS | codes: ['TOOL_DATA_UNAVAILABLE'] |
| Total latency recorded | PASS | 1706.5 ms |
| Expected error codes logged | PASS | expected ['TOOL_DATA_UNAVAILABLE'] |

### error_04_llm_not_configured

No API key configured: the run aborts before retrieval (API returns 503), but is still traced.

> When is BSE4104 scheduled?

Configuration overrides: `{"groq_api_key": ""}`

| Check | Result | Detail |
|---|---|---|
| Terminal status recorded | PASS | status = 'aborted' |
| Expected terminal status | PASS | expected one of ['aborted'] |
| Expected terminal error code | PASS | error_code = 'LLM_NOT_CONFIGURED' |
| Model parameters recorded | PASS | openai/gpt-oss-20b t=0.2 max_tokens=1500 |
| Prompt version + fingerprint recorded | PASS | agent-v1.0 |
| Retrieved chunks have relevance scores | PASS | run aborted before retrieval |
| Latency recorded per iteration and LLM call | PASS | no iterations |
| Executed tools have arguments, response, latency | PASS | 0 executed / 0 requested |
| Every failure carries an error code | PASS | codes: ['LLM_NOT_CONFIGURED'] |
| Total latency recorded | PASS | 1.2 ms |

## Regenerating

From `agent-backend/`, with `GROQ_API_KEY` set:

```bash
python scripts/capture_observability_traces.py
```

Ticket drafts, session state and case history go to throwaway SQLite files, so the real `data/*.db` stores are untouched.
