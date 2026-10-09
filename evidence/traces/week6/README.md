# Week 6 — Memory With/Without Comparison

Four traces demonstrate the bounded per-session memory added in Week 6.
Two turns are sent to the same session: the first drafts a support ticket,
the second asks about "that ticket". The pair is run twice — once with
memory disabled, once with memory enabled — to isolate the effect.

All runs use the live Groq API (`openai/gpt-oss-20b`) against the running
backend at `http://127.0.0.1:8000`.

## How the two runs differ

| | Memory OFF | Memory ON |
|---|---|---|
| `X-Memory` header | `off` | `on` |
| `X-Session-Id` | `week6-demo-off` | `week6-demo-on` |
| Turn 1 reads prior memory | no | no (first turn) |
| Turn 1 writes memory | no | yes |
| Turn 2 reads prior memory | no | yes |
| Turn 2 knows a ticket exists | no | yes |

## Run A — Memory OFF

**Turn 1** — `trace_without_memory_turn1.json`
- Message: *"I lost my student ID and need a replacement."*
- Result: `status=human_approval_required`, `iterations=2`, `tool_calls=1`
- The agent retrieved evidence, requested `create_support_ticket`, and
  stopped for human approval. A ticket was drafted.

**Turn 2** — `trace_without_memory_turn2.json`
- Message: *"What is the status of that ticket?"*
- Result: `status=completed`, `iterations=1`, `tool_calls=0`
- Agent response (excerpt):
  > *"I'm sorry, but I don't have any information about the status of
  > that ticket. I don't have access to the ticketing system ..."*
- The agent has **no context** about the earlier turn. It correctly
  refuses to invent a ticket state.

## Run B — Memory ON

**Turn 1** — `trace_with_memory_turn1.json`
- Same message as Run A, same outcome (ticket drafted, `human_approval_required`).
- Memory is written for this session after the run.

**Turn 2** — `trace_with_memory_turn2.json`
- Same message as Run A.
- Agent response (excerpt):
  > *"I'm sorry, but I don't have access to the current status of the
  > support ticket. **The ticket is still awaiting approval by a staff
  > member**, and I can't check or update its status ..."*
- The agent **recalls that a ticket exists** and states its known status
  — without fabricating a ticket ID, without claiming it was submitted,
  and without taking any action.

## What this demonstrates

- **Memory improves a legitimate task**: turn 2 in Run B is coherent;
  turn 2 in Run A is not.
- **Memory does not control decisions**: in Run B, the agent does not
  approve the ticket, does not claim to have checked it, and does not
  invent details. It only knows the ticket exists and is pending.
- **The bound still holds**: both runs stopped at
  `human_approval_required` on turn 1. Memory does not widen what the
  agent is allowed to do.

## Reproducing these traces

With the backend running (`uvicorn main:app --reload` from
`agent-backend/`):

```bash
mkdir -p evidence/traces/week6

curl -s -X POST http://127.0.0.1:8000/api/v1/agent/student-support \
  -H "Content-Type: application/json" -H "X-User-Role: student" \
  -H "X-Session-Id: week6-demo-off" -H "X-Memory: off" \
  -d '{"message": "I lost my student ID and need a replacement."}' \
  -o evidence/traces/week6/trace_without_memory_turn1.json

curl -s -X POST http://127.0.0.1:8000/api/v1/agent/student-support \
  -H "Content-Type: application/json" -H "X-User-Role: student" \
  -H "X-Session-Id: week6-demo-off" -H "X-Memory: off" \
  -d '{"message": "What is the status of that ticket?"}' \
  -o evidence/traces/week6/trace_without_memory_turn2.json

curl -s -X POST http://127.0.0.1:8000/api/v1/agent/student-support \
  -H "Content-Type: application/json" -H "X-User-Role: student" \
  -H "X-Session-Id: week6-demo-on" -H "X-Memory: on" \
  -d '{"message": "I lost my student ID and need a replacement."}' \
  -o evidence/traces/week6/trace_with_memory_turn1.json

curl -s -X POST http://127.0.0.1:8000/api/v1/agent/student-support \
  -H "Content-Type: application/json" -H "X-User-Role: student" \
  -H "X-Session-Id: week6-demo-on" -H "X-Memory: on" \
  -d '{"message": "What is the status of that ticket?"}' \
  -o evidence/traces/week6/trace_with_memory_turn2.json
