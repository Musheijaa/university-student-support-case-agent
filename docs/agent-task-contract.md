# Agent Task Contract — Week 5

This contract defines what the Week 5 bounded agent
(`POST /api/v1/agent/student-support`) is allowed to do, what it
remembers while doing it, and exactly when it must stop. It sits on top
of the Week 3 RAG pipeline and the Week 4 tools — it does not replace
them, and it does not widen anything they are allowed to do.

The agent's workflow follows the cycle
**Sense → Context → Plan/Decide → Act/Tool → Observe → Stop/Re-plan**
(see the Week 5 agent architecture diagram). Every section below says
which phase it governs.

The contract is enforced in code, not just documented:
`agent-backend/agent/contract.py` (goal, approved tools, limits, terminal
statuses), `agent-backend/agent/state.py` (per-run state), and
`agent-backend/agent/orchestrator.py` (the loop). Each stop condition
has a test in `agent-backend/tests/test_agent_orchestrator.py`. The
response shape is the one the Week 5 frontend renders
(`frontend/src/AgentStepsCard.jsx`).

---

## 0. The task: handle one student-support case

**Task name:** Student-support case handling.
**Trigger:** a student sends one free-text message to
`POST /api/v1/agent/student-support`.
**Done when:** the run reaches one of the terminal statuses in Section 7.

The agent performs this as a multi-step task. Each step maps to a
phase of the agent cycle, and steps 3–5 repeat until a stop condition
fires:

| # | Step | Phase | Performed by |
|---|---|---|---|
| 1 | Receive and validate the student's message and role | Sense | Application (`schemas.py`, `auth.py`) |
| 2 | Retrieve relevant policy evidence and record a plan (resources + budget) | Context | Application (`rag/retriever.py`, `orchestrator._plan_summary`) |
| 3 | Decide the next action: answer, check the timetable, or draft a ticket | Plan/Decide | Model (`agent-v1.0` prompt, approved tools only) |
| 4 | Validate, authorize, and execute the chosen tool | Act/Tool | Application (`tools.registry.dispatch_tool_call`) |
| 5 | Record the tool result as an observation and feed it back | Observe | Application (`orchestrator._observe`) |
| 6 | Re-plan (back to step 3) or stop with a terminal status | Stop/Re-plan | Application (limits and stop rules, Sections 6–7) |
| 7 | If a hand-off condition applies, stop and hand over to staff | Hand-off | Application + staff (Section 8) |

**Worked example** (real run, `evidence/traces/week5/trace2_human_approval.md`):
"I can't log in to the student portal… my account is locked."

1. **Sense:** message validated; role `student`.
2. **Context:** policy evidence retrieved; plan recorded with a budget of
   4 iterations / 3 tool calls.
3. **Decide (iteration 1):** the model chose `create_support_ticket`
   (category `IT Support`).
4. **Act:** the application validated the arguments, checked the role,
   and inserted draft `DRAFT-001` as `PENDING_APPROVAL`.
5. **Observe:** "Draft ticket DRAFT-001 created… needs staff approval."
6. **Decide (iteration 2):** the model produced a final answer telling the
   student the ticket is pending approval.
7. **Hand-off:** a ticket was drafted, so the run stopped with
   `human_approval_required`. Only staff can now submit or reject it.

## 1. Goal

**Resolve one student-support request per run** by doing exactly one of
the following, or a bounded combination of them:

1. Answer a policy question, grounded in retrieved evidence from the
   Makerere policy corpus (`docs/makerereUniversityPolicyDocs/`).
2. Look up real (synthetic) timetable sessions with `check_timetable`.
3. Draft a support ticket with `create_support_ticket` for a problem
   that needs staff follow-up — and then hand over to a human.

A run is **successful** when the student receives either a grounded
answer, a tool-backed answer, or a clear statement that the request is
pending human approval or is out of scope.

**Out of the agent's goal** (it must refuse or hand over, never act):
admissions, grading, disciplinary, fee, legal, or medical decisions;
submitting, approving, or rejecting a ticket; inventing schedules,
policies, or case status not present in evidence or tool results.

## 2. Inputs (Sense)

| Input | Source | Validation |
|---|---|---|
| `message` | Request body | 1–2000 chars, not whitespace-only (`schemas.StudentSupportRequest`) |
| `role` | `X-User-Role` header | `student` / `staff` / `guest`; anything else becomes `guest` (`auth.get_actor`) |
| `user_id` | `X-User-Id` header | Free text, default `anonymous` |

The role header is a bounded simulation, not real authentication (see
`docs/tool-catalogue.md`).

## 3. Context

Before the first decision the agent receives:

- The `agent-v1.0` system prompt (`llm/prompts.py`): the Week 4
  `tools-v1.0` prompt plus bounded-agent rules — pick one next action,
  re-plan after each tool result, never retry a failed call blindly,
  draft at most one ticket, and say that only staff can approve.
- Up to `RAG_TOP_K` (default 4) evidence chunks scoring at least
  `RAG_MIN_SCORE` (default 0.35), from `rag/retriever.py`.
- The tool definitions for the approved tools only (Section 4).
- A recorded `plan` summarizing the run's budget and resources, e.g.
  *"4 evidence source(s) retrieved; approved tools: check_timetable,
  create_support_ticket; budget: 4 iteration(s), 3 tool call(s)."*

## 4. Tools (Act/Tool)

The agent may request **only** tools on the Week 4 allow-list. Every
request is executed by the application through
`tools.registry.dispatch_tool_call`, never by the model.

| Tool | Effect | Roles allowed | Risk |
|---|---|---|---|
| `check_timetable` | Read-only lookup in `data/timetable/timetable.json` | student, staff | Low |
| `create_support_ticket` | Inserts a `PENDING_APPROVAL` draft into `data/tickets.db` | student, staff | Low (draft only) |

**Never callable by the agent:** `approve_ticket`, `reject_ticket`.
They are not in `TOOL_REGISTRY` or `TOOL_DEFINITIONS`, so the model
cannot name them; they exist only behind staff-only HTTP endpoints.

For every tool request, `dispatch_tool_call` enforces, in order:
allow-list → JSON-parseable arguments → role authorization → input
schema → safe execution (errors become messages, never stack traces) →
output schema. A failure at any step returns
`{"success": false, "error": ...}` to the agent as an observation; it
does not crash the run.

## 5. State

State lives for **one run only** (no memory across requests).

| Field | Meaning |
|---|---|
| `run_id` | Unique ID for the run (UUID) |
| `status` | Current run status — one of the values in Section 7 (`running` while in progress) |
| `iteration_count` | Plan/Decide cycles completed |
| `tool_call_count` | Tool executions performed |
| `steps[]` | Ordered trace of every decision (below) |
| `plan` | Context summary recorded before the first decision |
| `sources` | Retrieved evidence (document, page) the run was grounded in |
| `drafted_ticket_ids` | Tickets drafted this run — drives the human-approval stop |
| `response` | Final text returned to the student |

The model's message history is held internally for the run and is not
returned.

Each entry in `steps[]`:

| Field | Meaning |
|---|---|
| `iteration` | Which cycle produced this step |
| `decision` | `tool_call`, `final_answer`, `stop`, or `error` |
| `tool_name`, `tool_arguments` | Present when `decision = tool_call` |
| `tool_result` | The validated dict returned by `dispatch_tool_call` |
| `observation` | What the agent took away from the result (Observe) |
| `error` | Present when `decision = error` |

## 6. Limits

| Limit | Value | Enforced in |
|---|---|---|
| Maximum iterations (model decisions) per run | 4 (`AGENT_MAX_ITERATIONS`) | `agent/orchestrator.py` loop guard |
| Maximum tool executions per run | 3 (`MAX_TOOL_CALLS`, shared with Week 4) | `agent/orchestrator.py`; tools are withdrawn from the model once spent |
| Model request timeout | 20 s per call | `llm/client.py` |
| Message length | 2000 chars | `schemas.py` |
| Tools | Allow-list of 2 | `tools/registry.py` |
| Ticket outcome | Draft (`PENDING_APPROVAL`) only | `tools/tickets.py` |

Limits are enforced by application code, not by asking the model to
respect them — the same principle as Week 4's hard cap on tool
executions.

## 7. Stop conditions (Stop/Re-plan)

After each Observe step the agent either **re-plans** (another
iteration) or **stops** with exactly one terminal status:

| Status | Trigger | What the student gets |
|---|---|---|
| `completed` | Model returns a final answer with no further tool request | The grounded/tool-backed answer |
| `human_approval_required` | A ticket draft was created | Confirmation the ticket is **pending staff approval**, never "submitted" |
| `max_iterations_reached` | `iteration_count` hits the iteration limit | A safe "could not complete" message |
| `max_tool_calls_reached` | `tool_call_count` hits the tool limit | A safe "could not complete" message |
| `tool_not_approved` | Model requests a tool not on the allow-list | Refusal; the tool is never executed |
| `llm_error` | Provider timeout, rate limit, connection, or empty response | A safe error message, no internal details |

A tool that is approved but **fails** (unauthorized role, invalid
arguments, no data, service unavailable) does **not** stop the run: the
failure is recorded as an observation and fed back so the agent can
re-plan — usually by telling the student plainly. Only the six statuses
above end a run.

Every run ends in exactly one of these statuses — there is no code path
that leaves a run `running`.

## 8. Human hand-off conditions

The agent hands the case to a human whenever it reaches the edge of its
authority. The "Enforced by" column is deliberately honest: some
hand-offs are guaranteed by code, others rely on the model following the
prompt and are backed by a code-level limit.

| # | Condition | What the agent does | Who takes over | Enforced by |
|---|---|---|---|---|
| H1 | A support ticket was drafted | Stops with `human_approval_required`; tells the student the ticket is pending staff approval, not submitted | Staff, via `POST /api/v1/support-tickets/{id}/approve` or `/reject` with `X-User-Role: staff` | **Code:** `orchestrator.py` (drafted ticket → status); `main.py` (staff-only endpoints, 403 otherwise) |
| H2 | Student asks the agent to approve, submit, or resolve a ticket | Refuses and explains only staff can do that | Staff, as in H1 | **Code:** no approve/submit tool exists (`tools/registry.py`); **prompt:** `agent-v1.0` wording |
| H3 | Model asks for a tool that isn't approved | Stops with `tool_not_approved` without executing it; directs the student to staff | Student support staff | **Code:** `contract.is_approved_tool` check in `orchestrator.py` |
| H4 | Iteration or tool budget is used up | Stops with `max_iterations_reached` / `max_tool_calls_reached`; tells the student to contact staff | Student support staff | **Code:** loop guards in `orchestrator.py` |
| H5 | Request needs a high-impact decision (admissions, grades, discipline, fees, legal, medical) | Gives no decision; explains it must go to the relevant office, and may draft a ticket (then H1 applies) | The relevant university office | **Prompt:** `tools-v1.0` / `agent-v1.0` rules. No code-level topic filter yet (a known limitation) |
| H6 | Model provider fails | Stops with `llm_error` and a safe message to try again | Student retries; staff if it persists | **Code:** `orchestrator.py` catches `LLMRequestError` |

**The authority boundary:** the agent's power ends at a
`PENDING_APPROVAL` draft. Moving a ticket to `SUBMITTED` or `REJECTED`
needs a separate staff call that the agent cannot reach, so no prompt
can make the agent approve anything.

## 9. Evidence

Every element of this contract maps to the code that enforces it, a
test that proves it, and, where a live run can show it, a real trace.

| Requirement | Contract section | Enforced in | Proven by test (`tests/test_agent_orchestrator.py`) | Live trace (`evidence/traces/week5/`) |
|---|---|---|---|---|
| Multi-step task | 0 | `agent/orchestrator.py` | `test_timetable_tool_then_answer_completes` | trace1, trace2 |
| Goal | 1 | `agent/contract.py` (`AGENT_GOAL`) | `test_direct_answer_completes_without_tools` | trace1 |
| Required tools (approved only) | 4 | `agent/contract.py`, `tools/registry.py` | `test_contract_approved_tools_are_exactly_the_week4_allow_list`, `test_unapproved_tool_is_never_executed` | all three: only approved tools used |
| State | 5 | `agent/state.py` | `test_agent_endpoint_returns_full_trace` | every `.json`: `run_id`, counts, steps |
| Limits | 6 | `agent/orchestrator.py`, `config.py` | `test_tool_budget_exhausted_stops_safely`, `test_iteration_budget_exhausted_stops_safely` | all three stay within 2 iterations / 1 tool call |
| Stop conditions | 7 | `agent/orchestrator.py` | One test per status (`completed`, `human_approval_required`, `tool_not_approved`, `max_tool_calls_reached`, `max_iterations_reached`, `llm_error`) | trace1 `completed`; trace2, trace3 `human_approval_required` |
| Re-plan after a failed tool | 7 | `orchestrator._observe` | `test_failed_tool_is_observed_and_agent_replans`, `test_guest_role_tool_request_is_refused_by_dispatch` | — |
| Hand-off H1 (ticket → staff) | 8 | `orchestrator.py`, `main.py` | `test_ticket_draft_stops_for_human_approval` | trace2 |
| Hand-off H2 (refuse self-approval) | 8 | `tools/registry.py`, prompt | `test_unapproved_tool_is_never_executed` | trace3 + `trace3_boundary_check.txt` (ticket still pending; student approval → 403) |

The full test run is saved in
`evidence/traces/week5/agent-contract-tests.txt`.

The three traces are real runs against Groq (`openai/gpt-oss-20b`),
checked automatically against this contract by
`agent-backend/scripts/capture_agent_trace.py`. All three pass every
check:

1. **Happy path:** tool call → final answer → `completed`.
2. **Human hand-off:** ticket draft → `human_approval_required`.
3. **Boundary push:** the student tells the agent to approve its own
   ticket; it drafts the ticket only and refuses to approve it
   (`human_approval_required`).
