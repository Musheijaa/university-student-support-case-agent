# Week 6 — Memory Design and Data Handling

This document specifies the single persistent-memory mechanism added to
the bounded agent in Week 6, in line with the capstone brief's Week 6
requirement to *"retain only justified memory"* and document *"what is
stored, why, who can access it, retention and deletion."*

## 1. The justified use case

A student-support conversation often spans more than one message. In the
Week 5 agent, each request was treated in isolation: a follow-up like
*"what is the status of that ticket?"* had no referent, and the agent
correctly refused to guess.

**Justification:** remembering the most recent turn in the same session
lets the agent resolve references like "that ticket" or "it". This
improves the task (the student does not have to re-explain) and keeps the
conversation coherent, without widening what the agent is allowed to do.

**The memory is deliberately bounded to one turn per session.** Storing
the full conversation, or all tickets a session ever touched, was
rejected as not justified by the task.

## 2. What is stored

One row per session, in `data/sessions.db` (SQLite, stdlib `sqlite3`):

| Field | Meaning |
|---|---|
| `session_id` | The `X-Session-Id` header value (or a server-generated UUID if absent) |
| `last_message` | The last user message in this session |
| `last_response` | The agent's last response text in this session |
| `last_drafted_ticket_ids` | JSON-encoded list of ticket IDs drafted on the last turn |
| `last_status` | The terminal status of the last run (e.g. `completed`, `human_approval_required`) |
| `updated_at` | ISO-8601 UTC timestamp of the last write |

**Not stored:** retrieved evidence chunks, tool-call arguments, per-step
traces, the actor's identity beyond the session ID, or any data beyond
the current conversation turn.

## 3. Why each field

- `last_message`, `last_response` — needed so the model can interpret a
  follow-up like *"what about that?"*.
- `last_drafted_ticket_ids` — needed to resolve *"that ticket"* to a
  specific draft.
- `last_status` — needed so the agent can say *"the ticket is pending
  approval"* rather than inventing a status.
- `updated_at` — needed for retention (see §5).

No field is included "just in case". Every field supports the single
use case above.

## 4. Who can access it

- **The agent** (via `agent/memory.py`) — reads and writes as part of a
  request, only when the request opted in with `X-Memory: on` (or when
  `MEMORY_ENABLED=true`).
- **The session owner** — the same `X-Session-Id` value is required to
  read a session's memory. Sessions are keyed only by this value; there
  is no cross-session lookup and no enumeration endpoint.
- **No HTTP endpoint exposes memory directly.** There is no way to list
  sessions, dump memory, or read another session's row.

This is a student-project simulation, not real authentication. The same
caveat applies as for `X-User-Role` (see `docs/tool-catalogue.md`).

## 5. Retention and deletion

- **TTL:** default `MEMORY_TTL_HOURS=24`. Reads of sessions older than
  the TTL return `None`, as if the session had never existed.
- **Purge:** `memory.purge_expired(db_path, ttl_hours)` deletes expired
  rows; it is safe to call on a schedule or manually.
- **Explicit clear:** `memory.clear_session(session_id, db_path)` deletes
  one session's memory.
- **Reset:** deleting `data/sessions.db` clears all memory. The tickets
  store (`data/tickets.db`) is unaffected.

The last bullet is the reason memory has its own database: it can be
reset independently of tickets, and a bug in the memory layer cannot
corrupt ticket state.

## 6. What memory is NOT allowed to do

- It cannot trigger a tool call on its own. Only the model's Plan/Decide
  step decides tool calls; memory only supplies context.
- It cannot change limits or stop conditions. `MAX_TOOL_CALLS` and
  `AGENT_MAX_ITERATIONS` are unchanged by memory.
- It cannot approve or submit a ticket. Those endpoints remain staff-only
  and outside the agent loop.
- It cannot bypass authorization. Even with memory on, a `guest` role
  cannot call either tool.

These constraints are enforced in code
(`agent/orchestrator.py::_prefix_prior_context`) and covered by the
Week 5 stop-condition tests, which still pass with memory enabled.

## 7. Privacy note

No real student data is stored. All traffic is synthetic (a demo session
ID, a synthetic message). No credentials, tokens, or personal identifiers
are written to `sessions.db`.

## 8. Implementation map

| Concern | File |
|---|---|
| Store (read/write/clear/purge) | `agent-backend/agent/memory.py` |
| Hook (read before loop, write after) | `agent-backend/main.py::agent_student_support` |
| Prompt prefix | `agent-backend/agent/orchestrator.py::_prefix_prior_context` |
| Settings | `agent-backend/config.py` (`memory_enabled`, `memory_ttl_hours`, `memory_db_path`) |
| Response fields | `agent-backend/schemas.py` (`session_id`, `memory_enabled`) |
| Tests | `agent-backend/tests/test_agent_memory.py` |
| Traces | `evidence/traces/week6/` |
