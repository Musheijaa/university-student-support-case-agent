# Trace: error_04_llm_not_configured

| Field | Value |
|---|---|
| Run ID | `0b0f2207-4eeb-4ec1-a2eb-a6e4bc88c275` |
| Terminal status | **`aborted`** |
| Error code | `LLM_NOT_CONFIGURED` |
| Started / ended | 2026-10-13T10:13:20.733+00:00 → 2026-10-13T10:13:20.734+00:00 |
| Total latency | 1.2 ms |
| Iterations / tool calls | 0 / 0 |
| Model | `openai/gpt-oss-20b` via groq |
| Model parameters | temperature=0.2, max_tokens=1500, timeout=20.0s, max_retries=2 |
| Prompt version | `agent-v1.0` (system prompt sha256 `ad291169d2e2…`) |
| Tool definitions sha256 | `3b7ddb7be4e6…` |
| Contract budget | 4 iteration(s), 3 tool call(s); approved: check_timetable, create_support_ticket |
| Tokens (prompt / completion / total) | 0 / 0 / 0 |

## Request

**Actor:** `student` / `trace-capture`

> When is BSE4104 scheduled?

## Context: retrieval

_Retrieval did not run._

## Iterations

_No iterations ran._

## Errors

| Code | Stage | Iteration | Message |
|---|---|---|---|
| `LLM_NOT_CONFIGURED` | setup | — | LLMConfigurationError: GROQ_API_KEY is not configured. |

## Latency breakdown (ms)

| Retrieval | LLM | Tools | Orchestration overhead | Total |
|---|---|---|---|---|
| 0.0 | 0 | 0 | 1.2 | 1.2 |

## Final response

_(empty)_
