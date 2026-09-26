# Week 4 Progress Report

**UniSupport AI: A Bounded Agentic Student Support Case System**
GROUP L | BSE4104: Emerging Trends in Software Engineering
Week Ending: 26th September 2026

## 1. Project Overview and Context

Week 3 delivered a working RAG pipeline: student questions are answered from a controlled corpus of Makerere University policy documents, with sources returned alongside every answer. Week 4's objective, per the brief, was to move beyond answer generation by giving the model explicit, safe software capabilities — tool/function calling — while keeping Week 2's foundation-model baseline and Week 3's RAG functionality fully intact.

## 2. Work Completed

- Implemented two explicit tools behind a strict allow-list (`agent-backend/tools/registry.py`): `check_timetable` (read-only, synthetic timetable data) and `create_support_ticket` (creates a low-risk `PENDING_APPROVAL` draft, never a submitted action).
- Added a new prompt version, `tools-v1.0`, now the active default — additive alongside V1.0, V2.0, and `rag-v1.0`, which remain untouched and fully tested.
- Extended the Groq client (`llm/client.py`) with a tool-calling-capable completion method, and implemented a bounded tool-calling loop in `llm/service.py`: the model is offered both tools and the same RAG evidence used in Week 3; if it requests a tool, the application (never the model) validates, authorizes, executes, and schema-checks the result before continuing the conversation.
- Bounded the loop two ways: it stops offering new tool calls once `MAX_TOOL_CALLS` (default 3) is reached, and — defensively — it will not *execute* more than that bound even if a provider or bug ignores the request to stop, with a hard cap on round-trips so a request can never hang.
- Implemented human approval as a genuinely separate mechanism: `approve_ticket`/`reject_ticket` are not registered as callable tools at all — they only exist behind two new staff-only HTTP endpoints (`POST /api/v1/support-tickets/{id}/approve`, `.../reject`), plus a `GET` for status. There is no code path by which the model can submit or approve a ticket itself.
- Added a minimal, explicitly-non-production authorization layer (`agent-backend/auth.py`): an `X-User-Role` header (`student`/`staff`/`guest`, default `student`), since the application had no auth concept at all before this week.
- Added synthetic timetable data (`agent-backend/data/timetable/timetable.json`, clearly labeled as such) and a SQLite-backed ticket store (`agent-backend/data/tickets.db`, stdlib `sqlite3`, no new dependency).
- Added 46 new automated tests across tool validation, authorization, service-unavailable simulation, unexpected-output handling, the ticket-approval API, and five end-to-end tool-calling scenarios (mocked Groq responses, no live API dependency) — full suite: **88 passed**.
- Verified live against the real Groq API: a timetable question correctly triggered `check_timetable` and returned a real, non-fabricated schedule; a portal-access complaint correctly triggered `create_support_ticket`, created a real `PENDING_APPROVAL` row, and the model explicitly told the student it was pending approval; an unauthorized approval attempt returned a real `403`; a staff approval correctly transitioned the ticket to `SUBMITTED`; a re-approval attempt was correctly rejected; a plain knowledge question still returned a grounded RAG answer with `tool_calls: []`; an unknown course code correctly returned "no timetable information found" rather than a fabricated schedule.
- Documented the tool catalogue (`docs/tool-catalogue.md`), updated system architecture (`docs/architecture.md`, including the Week 2→3→4 progression), and this report.

## 3. Individual Contributions

Based on `git log` for this period: no new commits landed between the Week 3 report (2026-09-16) and this session, so all Week 4 work below is attributed to Okema Paul Mark. Any other team member's non-code contributions this week (research, review, planning) are not visible in git history and should be added by the team before submission.

| Team Member | Task(s) | Contribution Summary |
|---|---|---|
| Okema Paul Mark | Full Week 4 implementation | Designed and built the tool registry, both tools, the bounded tool-calling loop, the ticket approval endpoints, the minimal authorization layer, all new tests, and the supporting documentation. |

## 4. Key Engineering Decisions and Rationale

**No real authentication exists yet, so authorization is an explicit, bounded simulation.** Building real login/authentication was out of scope for Week 4. A header-based role (`X-User-Role`) was chosen over, e.g., a shared staff API key, because it makes the authorization *rule* (only staff may approve/reject) directly testable and visible in code without pretending to be a real security boundary. This is documented plainly in `auth.py` and `docs/tool-catalogue.md` so it is never mistaken for production-grade auth later.

**SQLite over new infrastructure.** The brief explicitly allows SQLite for a bounded Week 4 demonstration. Using Python's stdlib `sqlite3` added zero new dependencies while still giving tickets real persistent state and real state-transition rules (`PENDING_APPROVAL` → `SUBMITTED`/`REJECTED`, rejecting any further transition once resolved).

**The bound on tool calls is enforced by the application, not just requested from the provider.** Initially the loop only passed `tool_choice="none"` once the limit was reached, trusting Groq to stop requesting tools. While writing the test for this, it became clear that a correct implementation must not *trust* that — a misbehaving provider (or a bug) ignoring `tool_choice` could otherwise let the loop keep executing tools indefinitely. The loop now hard-caps actual tool executions at `MAX_TOOL_CALLS` regardless of what the model asks for, and caps total round-trips so it always terminates. This was found and fixed during this week's own test-writing, not assumed correct from the start.

**Approval is architecturally, not just procedurally, separate from tool calling.** `approve_ticket`/`reject_ticket` were deliberately never added to `TOOL_REGISTRY` or `TOOL_DEFINITIONS` — the model cannot request them even if it tried, because they don't exist in the vocabulary Groq is given. This is a stronger guarantee than a prompt instruction alone would be.

## 5. Tool Calling Flow Summary

```text
Student question
      ↓
LLM Service (llm/service.py) - runs RAG retrieval, same as Week 3
      ↓
Groq, offered check_timetable + create_support_ticket (tool_choice="auto")
      ↓
   ┌──── no tool needed ────┐        ┌──── tool requested ────┐
   ↓                        │        ↓                        │
Final grounded answer       │   tools/registry.py:             │
(Week 3 behavior,           │   allow-list check → JSON parse  │
tool_calls: [])             │   → auth check → input validation │
                             │   → execute → output validation   │
                             │        ↓                          │
                             │   Tool result → back to Groq ─────┘
                             │        ↓ (repeats, bounded by MAX_TOOL_CALLS)
                             └──── Final grounded answer + tool_calls
```

Ticket approval is intentionally outside this diagram entirely — it is a separate, later, staff-authenticated HTTP call, not a step the model participates in.

## 6. Failures, Challenges, and Current Response

No new *retrieval/grounding* failures were found this week beyond the four already documented in `docs/rag-failures.md` (still open). One engineering issue was found and fixed during development, not left as a known gap: the tool-calling loop's original boundedness relied on the provider honoring `tool_choice="none"`; this was corrected to enforce the bound defensively at the application level (see Section 4) before being considered complete, and is covered by a dedicated test (`test_tool_execution_is_hard_capped_even_if_provider_ignores_tool_choice`).

## 7. Risks Going Into Week 5

- The authorization model is explicitly not real authentication; if Week 5 introduces anything security-sensitive, this should be revisited rather than extended further as-is.
- The ticket store and timetable data are both small, single-purpose, file/SQLite-backed stores; they are adequate for this bounded demonstration but were not designed for concurrent multi-user load.
- Tool descriptions and the `tools-v1.0` prompt currently rely on the model correctly distinguishing "create a draft" from "submit a ticket" through instruction-following alone (reinforced architecturally by approval never being a callable tool) — this held up in every live test this week, but has not been adversarially tested (e.g. a student explicitly asking the model to "just submit it now").

## 8. Plan for Week 5

Per the brief, Week 5 is expected to introduce bounded agentic orchestration. Planned activities (not yet implemented):

- Evaluate LangGraph for orchestrating retrieval, tools, and generation as an explicit, bounded graph rather than the current single hand-written loop.
- Consider persistent session/case memory (e.g. remembering an active ticket across turns) — not implemented yet, and not to be added prematurely per this week's scope boundary.
- Adversarially test the draft-vs-submit distinction (e.g. prompt-injection attempts asking the model to claim a ticket was approved) before extending tool capability further.
- Continue treating RAG and tools as the grounding/capability layer any future agent orchestration sits on top of, not something it replaces.

## 9. Links

- GitHub Repository: https://github.com/Musheijaa/university-student-support-case-agent
- Tool catalogue: `docs/tool-catalogue.md`
- Tool failure/authorization test evidence: `docs/tool-test-evidence.md`
- System architecture (Week 2→3→4): `docs/architecture.md`
- RAG architecture (Week 3 detail): `docs/rag-architecture.md`
