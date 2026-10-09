# Week 5 - Agent Architecture

This document describes the bounded agent workflow implemented in
Week 5, with the Week 6 addition of bounded per-session memory.

The agent follows the cycle: Sense -> Context -> Plan/Decide ->
Act/Tool -> Observe -> Stop/Re-plan. Steps 3-5 repeat until one of the
six terminal statuses fires (see docs/agent-task-contract.md,
Section 7).

## Diagram
              Student message  (X-User-Role)
                               │
                               ▼
              ╭────────────────────────────────╮
              │ 1. SENSE                       │
              │ schemas.py + auth.py           │
              │ validate message, read role    │
              ╰────────────────────────────────╯
                               │
                               ▼
              ╭────────────────────────────────╮
              │ 2. CONTEXT                     │
              │ rag/retriever.py               │
              │ top-K evidence chunks          │
              │ plan recorded (budget)         │
              ╰────────────────────────────────╯
                               │
                               ▼
              ╭────────────────────────────────╮
              │ 3. PLAN / DECIDE               │
              │ Groq (agent-v1.0 prompt)       │◄─────╮
              │ chooses ONE next action:       │      │
    ╭─ answer ┤ - answer                       │      │
    │         │ - check_timetable              │      │ re-plan, bounded by
    │         │ - create_support_ticket        │      │ MAX_TOOL_CALLS=3
    │         ╰────────────────────────────────╯      │ AGENT_MAX_ITERATIONS=4
    │                          │ tool call            │
    │                          ▼                      │
    │         ╭────────────────────────────────╮      │
    │         │ 4. ACT / TOOL                  │      │
    │         │ tools/registry.py              │      │
    │         │ allow-list → auth →            │      │
    │         │ validate → execute             │      │
    │         ╰────────────────────────────────╯      │
    │                          │                      │
    │                          ▼                      │
    │         ╭────────────────────────────────╮      │
    │         │ 5. OBSERVE                     │      │
    │         │ record tool result             ├──────╯
    │         │ feed back to model             │
    │         ╰────────────────────────────────╯
    │                          │ limit hit / error
    ▼                          ▼
╭──────────────────────────────────────────────────────────╮
│ 6. STOP  -  exactly one of:                              │
│ completed                 max_iterations_reached         │
│ human_approval_required   max_tool_calls_reached         │
│ tool_not_approved         llm_error                      │
╰──────────────────────────────────────────────────────────╯
                               │
                               ▼
              Response to student
              (sources, tool_calls, steps)

## Component map

| Phase | Component | File |
|---|---|---|
| Sense | Request validation, role extraction | schemas.py, auth.py |
| Context | RAG retrieval, plan summary | rag/retriever.py, agent/orchestrator.py |
| Plan/Decide | Model call with tool definitions | llm/prompts.py, agent/orchestrator.py |
| Act/Tool | Tool dispatch (allow-list, auth, validation, execution) | tools/registry.py |
| Observe | Result recorded and fed back | agent/orchestrator.py |
| Stop | Terminal status determination | agent/orchestrator.py, agent/contract.py |
| State | Per-run state | agent/state.py |

## Week 6 addition - bounded per-session memory

Week 6 adds one bounded memory mechanism that sits beside the loop,
not inside it. Before the loop runs, main.py reads the previous turn
for the request's session ID (if X-Memory: on), and passes it to
run_agent as prior_turn. _prefix_prior_context prepends a short
summary to the user prompt. After the loop, main.py writes the
current turn back to the session store.

          HTTP request (session ID, X-Memory)
                 │
                 ▼
╭──────────────────────────────────╮   read   ╭──────────────────╮
│ main.py: read prior_turn         │◄─────────┤                  │
│ (only if X-Memory: on)           │          │                  │
╰──────────────────────────────────╯          │                  │
                 │                            │                  │
                 ▼                            │                  │
╭──────────────────────────────────╮          │                  │
│ orchestrator:                    │          │                  │
│ _prefix_prior_context            │          │                  │
│ prior summary → user prompt      │          │                  │
╰──────────────────────────────────╯          │                  │
                 │                            │                  │
                 ▼                            │ SESSION STORE    │
╔══════════════════════════════════╗          │ (per session ID) │
║ [ existing agent loop ]          ║          │                  │
║ unchanged: same tools, limits,   ║          │                  │
║ stop conditions                  ║          │                  │
╚══════════════════════════════════╝          │                  │
                 │                            │                  │
                 ▼                            │                  │
╭──────────────────────────────────╮   write  │                  │
│ main.py: write_session()         ├─────────►│                  │
│ (only if X-Memory: on)           │          │                  │
╰──────────────────────────────────╯          ╰──────────────────╯
                 │
                 ▼
          Response to student


What memory does not do: it does not trigger tool calls, does not
change limits, does not alter stop conditions, and does not reach any
endpoint the agent could not already reach. It supplies context only.

See docs/memory-design.md for the full design and data handling note.

## What is intentionally outside the loop

Ticket approval and rejection are not tools and not part of the agent
cycle. They exist only as staff-only HTTP endpoints. The agent's
authority ends at a PENDING_APPROVAL draft. See
docs/agent-task-contract.md, Section 8, for the hand-off conditions.

## References

- Agent Task Contract: docs/agent-task-contract.md
- Memory design: docs/memory-design.md
- Agent loop implementation: agent-backend/agent/orchestrator.py
- Traces: evidence/traces/week5/, evidence/traces/week6/
- Tests: agent-backend/tests/test_agent_orchestrator.py,
  tests/test_agent_memory.py
