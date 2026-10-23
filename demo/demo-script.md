# Week 8 - Live Demo Script

This document is the script for the 12-15 minute live demonstration at
the end of the capstone. It follows the structure required by the
brief (Section 10):

- Problem, target user, why AI (1-2 min)
- Architecture and progression (2 min)
- Live end-to-end workflow (4 min)
- Engineering evidence view (2 min)
- One real failure / recovery (2 min)
- Guardrails and human approval boundaries (1-2 min)

The demonstration must show that the team can inspect what the agent
did, explain a real failure, and demonstrate where human control is
retained. A happy-path demo alone is not sufficient.


## Pre-demo checklist (run 10 minutes before)

- Backend running: `uvicorn main:app --reload` from `agent-backend/`
- Frontend running: `npm run dev` from `frontend/`
- Browser tabs open, in this order:
    1. Frontend: http://localhost:5173
    2. Swagger: http://127.0.0.1:8000/docs
    3. Terminal 1: `pytest tests/test_prompt_injection.py -v` (last result visible)
    4. Terminal 2: `git log --oneline -10` (recent commits visible)
    5. Text editor: docs/agent-task-contract.md (open to Section 7)
- `.env` present and `GROQ_API_KEY` set
- `.venv` active in terminals
- Do a test run of the live workflow (so you know it works today)

Fallback if Groq API fails during demo:
- Have `evidence/traces/week5/trace1_happy_path.json` open in a tab
- Have a screenshot of a successful run in the browser
- Explain the recorded trace instead of running live


## Segment 1 - Problem, user, why AI (1-2 min)

**Speaker:** [Name]
**What to say (roughly):**

> University students at Makerere face the same problem over and over:
> they need answers about policies (exam rules, timetable procedures),
> but those answers are spread across PDFs, staff emails, and
> different offices. The current workflow means asking around, being
> told to "check the handbook", and losing trust in the system when
> answers conflict.
>
> We built UniSupport AI - a bounded student-support agent - to answer
> policy questions from approved documents, check timetable and ticket
> state, and route support requests to staff. The reason AI is
> justified here is not novelty: it is natural-language understanding
> (interpreting the student's question), retrieval (finding the right
> passages), and drafting (producing a clear answer or a well-formed
> ticket). Everything that involves a real decision - grades, fees,
> discipline, approvals - stays with a human.

**Why this works:** it names the user, the pain, and the specific AI value. It also names what AI does NOT do, which is a stronger answer than "AI does everything".


## Segment 2 - Architecture and progression (2 min)

**Speaker:** [Name]
**Show:** `docs/agent-architecture.md` on screen, or a slide with the diagram.

**What to say:**

> The system progressed through distinct weeks, and each layer builds on
> the last. In Week 2, a foundation model behind a versioned prompt
> answered questions, but without citing sources. In Week 3 we added
> RAG: answers are now grounded in approved Makerere policy documents,
> with sources returned. In Week 4 we added two explicit tools -
> check_timetable and create_support_ticket - both going through a
> single dispatch choke point that enforces an allow-list, role
> authorization, schema validation, and safe error containment. In
> Week 5 we added a bounded agent loop: the model can chain tool calls,
> but the loop has hard caps on iterations and tool executions. In
> Weeks 6 and 7 we added memory and adversarial evaluation.
>
> The current architecture is: request comes in, RAG retrieves evidence,
> the bounded agent decides between answering directly and calling one
> of the two approved tools, and every run ends in exactly one terminal
> status. Approval of a ticket is not part of that loop - it is a
> separate staff-authenticated endpoint the model cannot reach.

**Key points to emphasize:**
- Every layer is additive, not a rewrite
- The tool allow-list is in one place
- Approval is architecturally outside the agent


## Segment 3 - Live end-to-end workflow (4 min)

**Speaker:** [Name]
**Show:** Frontend at http://localhost:5173, browser tab 1.

**Demo steps:**

1. **Set the role** dropdown to `student`, backend URL as
   `http://127.0.0.1:8000`. Point out the green health dot.

2. **Ask a RAG question.** Type:What counts as examination malpractice at Makerere?
Press Send.
- Wait for the answer (5-15 seconds).
- Point out: the answer has content AND a **Sources** panel with
  document names and page numbers.
- Point out: `prompt_version: agent-v1.0` (or whatever is shown at
  the bottom of the message).
- Say: "This is the RAG pipeline - it cited the exact pages it used."

3. **Ask a tool question.** Type:Is there a CSC2101 class tomorrow?
Press Send.
- The answer should mention real sessions OR "no timetable
  information found".
- Point out: the **tool_calls** panel (if visible) shows
  `check_timetable` was invoked with `{"course_code": "CSC2101"}`.
- Say: "The model requested the tool; the application executed it
  after validation and authorization. Look at the trace."

4. **Draft a ticket.** Type:I lost my student ID and need a replacement.
Press Send.
- A **draft ticket card** should appear with an ID like `DRAFT-007`,
  status `PENDING_APPROVAL`.
- Point out: the card shows Approve/Reject buttons ONLY if the role
  is `staff`. Currently the role is `student` - so no buttons.
- Say: "The agent drafted this ticket. It cannot approve it. That
  is enforced by the design: approve_ticket is not a tool."

5. **Switch to staff role.** Change the dropdown to `staff`. Re-run
the same message (or refresh).
- The **Approve/Reject** buttons should now appear on the ticket
  card.
- Click Approve. The status changes to `SUBMITTED`.
- Say: "Staff approval happened through a separate, staff-only HTTP
  call. The model has no path to this endpoint."

**If something breaks live:**
- Switch to `evidence/screenshots/week5/trace2_human_approval_ticket.png`
- Talk through it as if the live demo had worked
- Say: "This is a recorded trace from the same workflow; the live
system matches it."


## Segment 4 - Engineering evidence view (2 min)

**Speaker:** [Name]
**Show:** `evidence/traces/week5/trace1_happy_path.json` in an editor,
or `docs/evaluation.md` on screen.

**What to say:**

> We want to show that the system is inspectable, not just
> working. Every agent run produces a full trace with the request, the
> retrieved evidence, every tool call, every observation, and the
> terminal status. Here is one example.

**Open the trace JSON:**

- Point out `run_id` - "every run is uniquely identified"
- Point out `plan` - "the retrieval step is recorded before any decision"
- Point out `steps[]` - "each iteration is logged with its decision"
- Point out `sources[]` - "the exact pages the answer was grounded in"
- Point out `status: "completed"` - "one of six terminal statuses; never
left 'running'"

**Optionally show `docs/evaluation.md`:**

- Point out that the evaluation set covers 39 scenarios across six
categories (normal, edge, incorrect-information, adversarial,
tool-failure, unauthorized)
- Say: "Every scenario is automated and passing."


## Segment 5 - One real failure / recovery (2 min)

**Speaker:** [Name]
**Show:** `docs/failure-catalogue.md` on screen, or one of the tests
below in a terminal.

**What to say:**

> A polished happy-path demo is not enough. We want to show a real
> failure we found and how we fixed it. This is Failure #3 from our
> catalogue.

**Open `docs/failure-catalogue.md`** and scroll to Failure 3:

> What happened: Unauthorized tool calls were being counted against the
> tool-call budget. When a guest role requested a tool, the dispatch
> layer correctly refused it - but the counter still incremented. A
> guest could exhaust their budget on calls that were never allowed to
> run, ending the run earlier than necessary with a misleading status.

> Why: The counter incremented on the model's request, before the
> dispatch result was checked for success.

> Fix: agent-backend/agent/orchestrator.py now increments the tool-call
> counter only on successful dispatch. Failed or unauthorized calls
> are recorded as observations (so the model learns from them) but do
> not consume the budget.

> Re-test: tests/test_prompt_injection.py::test_guest_role_cannot_invoke_tools
> Result: PASSED.

**Optionally run it live:**
cd agent-backend
pytest tests/test_prompt_injection.py::test_guest_role_cannot_invoke_tools -v

Wait for the green PASSED line. Say:

> This test failed when first written. Investigating the failure
> revealed the bug. This is what the evaluation was for.

**If something breaks:** skip the live test, just walk through the
catalogue entry. The catalogue itself is the evidence.


## Segment 6 - Guardrails and human approval boundaries (1-2 min)

**Speaker:** [Name]
**Show:** `docs/guardrails.md` on screen.

**What to say:**

> Everything in the demo so far has been about the happy path. The
> safety story is what makes this a real system. We have seven
> guardrails, and every one of them is enforced in code, not by asking
> the model to behave.

**Walk through the seven guardrails from `docs/guardrails.md`:**

1. Input validation (Pydantic, 1-2000 chars, non-blank)
2. Tool allow-list (2 tools, no others callable)
3. Role-based authorization (X-User-Role; guest cannot call tools)
4. Loop budgets (max_iterations=4, max_tool_calls=3)
5. HITL approval for tickets (only staff endpoints)
6. Prompt-injection resistance (14 adversarial tests)
7. Error containment (all failures return safe structured errors)

**Emphasize the human-approval boundary:**

> The single most important design decision in this project is that
> approve_ticket and reject_ticket are NOT tools. They are staff-only
> HTTP endpoints. There is no code path by which the model can approve
> its own action. That is not a prompt instruction - it is a structural
> guarantee.

**Close with:**

> The system is bounded, evaluated, and safe. It is not autonomous -
> it is a curated, audited support workflow where AI handles
> understanding and drafting, and humans handle all decisions with
> consequence.


## Post-demo Q&A - common questions to be ready for

1. **"How do you know the model won't hallucinate?"**
   It may, but we have four layers: (a) RAG forces it to answer from
   evidence; (b) sources are returned so a user can verify; (c) if
   there is no evidence, the prompt instructs a refusal; (d) the
   evaluation set includes "questions the corpus cannot answer" and
   checks that refusals happen. It's not zero-risk; it's bounded and
   audited.

2. **"What if someone types 'ignore your instructions'?"**
   Prompt instructions can be overridden; the code cannot. approve_ticket
   doesn't exist as a tool, so even a compromised prompt cannot approve
   a ticket. See `tests/test_prompt_injection.py`.

3. **"Why not use LangChain / LangGraph / a framework?"**
   A direct implementation makes every step auditable - we can point to
   the exact line where authorization happens. A framework would work,
   but for a bounded student project the explicit implementation is
   easier to verify and explain.

4. **"What would you build next?"**
   Two things: (a) a code-level topic classifier for high-impact
   requests (currently prompt-enforced), and (b) real authentication
   instead of the X-User-Role header simulation.

5. **"Does memory leak between users?"**
   No. `agent/memory.py` keys everything by `X-Session-Id`. Sessions
   are isolated; there is no cross-session lookup. See
   `docs/memory-design.md`.


## Timing guide

| Segment | Target | Cumulative |
|---|---|---|
| 1. Problem + user + why AI | 1.5 min | 1.5 min |
| 2. Architecture + progression | 2 min | 3.5 min |
| 3. Live end-to-end workflow | 4 min | 7.5 min |
| 4. Engineering evidence view | 2 min | 9.5 min |
| 5. One real failure / recovery | 2 min | 11.5 min |
| 6. Guardrails + human approval | 1.5 min | 13 min |
| Buffer / transition | 1-2 min | 14-15 min |

Q&A follows after the demo ends.


## Roles (assign before the day)

- **Speaker 1** - Segments 1 and 2 (problem + architecture)
- **Speaker 2** - Segments 3 and 4 (live demo + evidence)
- **Speaker 3** - Segments 5 and 6 (failure + guardrails)
- **Operator** - sits at the keyboard, runs the demo commands
- **Timekeeper** - watches the clock, signals at each transition

If the team is smaller, one person can play multiple roles; the
Operator and Timekeeper should still be distinct people.
