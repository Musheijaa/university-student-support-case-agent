# Week 5 Progress Report

**Group L — UniSupport AI: A Bounded Agentic Student Support Case System**
**Week ending:** 3rd October 2026
**Submitted by:** Akakikunda Benita

## 1. Work Completed

Week 5's objective, per the brief, was to implement **one goal-directed,
multi-step workflow in which the system chooses among approved next actions
and stops safely** — building on Week 2 (foundation model), Week 3 (RAG), and
Week 4 (tools).

Delivered this week:

- **Bounded agent workflow** (`agent-backend/agent/orchestrator.py`): a
  plan→act→observe loop that offers only the Week 4 approved tools
  (`check_timetable`, `create_support_ticket`) and stops at one of six
  terminal statuses.
- **Agent Task Contract** (`docs/agent-task-contract.md`): formal
  specification of goal, tools, state, limits, stop conditions, and
  human hand-off conditions.
- **Agent state model** (`agent-backend/agent/state.py`): per-run state
  including iteration count, tool-call count, ordered step trace, plan
  summary, retrieved sources, and drafted ticket IDs.
- **New endpoint** `POST /api/v1/agent/student-support`, plus frontend
  rendering of agent steps (`frontend/src/AgentStepsCard.jsx`).
- **Tests** (`agent-backend/tests/test_agent_orchestrator.py`, 248 lines):
  12 tests — one per stop condition, plus contract verification. **All 12
  pass locally** (`pytest tests/test_agent_orchestrator.py -v`).
- **Trace capture tool** (`agent-backend/scripts/capture_agent_trace.py`):
  runs a real Groq request and validates the response against the contract.
- **Three execution traces** (`evidence/traces/week5/`), including one
  failure/boundary case, captured against the live Groq API and saved as
  JSON, markdown, and screenshots.

## 2. Key Engineering Decisions

- **Limits enforced by code, not prompts.** `MAX_TOOL_CALLS` and the
  iteration cap are checked in `orchestrator.py`, not requested from the
  model. A misbehaving provider cannot cause an unbounded loop.
- **Approval is architecturally separate.** `approve_ticket` and
  `reject_ticket` are not registered in `TOOL_REGISTRY` — the model
  cannot name them, so it cannot reach them.
- **Six terminal statuses, no hanging runs.** Every run ends in exactly
  one of `completed`, `human_approval_required`, `max_iterations_reached`,
  `max_tool_calls_reached`, `tool_not_approved`, or `llm_error`.
- **Failed tools are observations, not terminations.** A tool that fails
  (unauthorized role, invalid args, no data) is fed back to the agent
  as an observation so it can re-plan — only contract-level failures
  end the run.

## 3. Failures / Challenges

- **Known limitation:** the high-impact-topic guard (H5 in the contract)
  relies on prompt instruction, not a code-level topic filter. Documented
  in `docs/agent-task-contract.md` Section 8 as an explicit limitation.
- All 12 Week 5 agent tests pass on the current branch (`main` at
  `38833f9`).

## 4. Links

- **Commits:** `bef70d9` (agent workflow + contract + traces),
  `8b4a1be` (trace screenshots), `e2a2c92` (frontend integration),
  `38833f9` (merge to main)
- **Pull Requests:** #9 (Week 5 task contract), #10 (Week 5 agent)
- **Files:** `agent-backend/agent/`, `docs/agent-task-contract.md`,
  `evidence/traces/week5/`, `evidence/screenshots/week5/`
- **Tests:** `agent-backend/tests/test_agent_orchestrator.py` (12 passing)

## 5. Individual Contributions

| Member | Task owned | Evidence |
|---|---|---|
| Okema Paul Mark | Week 5 bounded agent workflow, Task Contract, execution traces | commits `bef70d9`, `8b4a1be`, `e2a2c92`; files in `agent-backend/agent/`, `docs/agent-task-contract.md` |
| Akakikunda Benita | Week 5 integration verification; Week 5 progress report | This document; local verification run of `pytest tests/test_agent_orchestrator.py` (12 passed) |

*Other team members' contributions (review, planning, documentation) should be
added by the team before final submission.*

## 6. Plan for Week 6

Per the brief, Week 6 is **Memory, State and Interoperability**:

- Implement one justified persistent-memory use case (e.g., an active
  case remembered across turns).
- Document what is stored, why, who can access it, retention and deletion.
- Demonstrate that memory improves a legitimate task without silently
  controlling critical decisions.
- Add one external integration OR an MCP-style interface specification.
- Run a with/without-memory comparison on the same scenario to show the
  effect.