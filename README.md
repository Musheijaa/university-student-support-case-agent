# University Student-Support Case Agent

A bounded AI-native student-support case agent for routine academic-support queries, simulated case-status checks, and controlled support-ticket workflows.

## Project Summary
This project is a BSE4104 capstone prototype for an AI-native student-support system at Makerere University. The solution is intentionally limited to a realistic academic-support domain: helping students understand approved guidance, checking simulated timetable or case-status information, and creating or routing routine support requests in a traceable workflow.

The system is designed around an important principle: AI is used where it adds value in understanding, retrieval, explanation, and workflow assistance, while deterministic software remains responsible for validation, authorization, routing rules, and controlled system actions. Any high-impact or sensitive decisions remain under human approval.

## Team
- Okema Paul Mark — AI Engineering Lead
- Kizito Ryan — Quality/Security Lead
- Benita Akakikunda — Application/Integration Lead
- Mushieja Abraham — Project Lead
- Mwesigwa Duncan — DevOps/Documentation Lead

## Problem
University students often face fragmented guidance across documents, portals, and support procedures. Common academic tasks such as checking timetable details, clarifying course-related issues, or starting a support request can be slow and inconsistent when the relevant guidance is not centralized or clearly traceable.

## Target Users
- Students seeking help with common academic-support questions
- Support staff who need a clear and auditable routing workflow
- Course and student-service teams who need a bounded, governed support process

## Project Objective
To prototype a bounded, AI-assisted student-support case agent that can:
- interpret student questions in natural language
- retrieve and explain approved academic guidance
- check simulated case-status or timetable information
- create a routine support ticket or case record
- route support requests according to deterministic rules
- require human approval for escalation or high-impact decisions

## Primary End-to-End Workflow
1. A student submits a question or support request.
2. The system identifies the relevant approved knowledge source.
3. The AI provides a grounded explanation or next step using approved content.
4. If case handling is needed, the system checks simulated case-status or timetable information.
5. The system validates required inputs and creates a support case record.
6. The case is routed using deterministic business rules.
7. Human staff review is required for escalation or any sensitive outcome.

## Role of AI
AI supports the project in the following bounded ways:
- natural-language understanding of student requests
- retrieval assistance for approved knowledge sources
- explanation and summarization of academic guidance
- case and workflow assistance within a controlled domain

AI does not make final decisions about grades, admissions, fee matters, disciplinary actions, medical issues, or legal matters.

## Deterministic Responsibilities
The deterministic software layer handles:
- input validation
- authorization and permission checks
- case-state tracking
- routing based on business rules
- creation and updates to simulated support records
- blocking unsupported or high-impact actions

## Human Approval Boundaries
Human approval remains required for:
- escalations outside the bounded support workflow
- academic or operational decisions with significant impact
- concerns involving fees, disciplinary matters, grades, legal issues, or medical matters
- any case beyond the project’s defined scope

## Scope of the Prototype
This prototype includes:
- grounded academic-support questions using approved documentation
- case creation and status checking in simulated data
- basic workflow orchestration and case-state tracking
- deterministic validation and routing logic
- documentation and evidence for traceability and review

This prototype intentionally excludes:
- live institutional systems integration
- confidential university or student data
- fees, grading, admission, legal, or disciplinary decisions
- any uncontrolled general-purpose chatbot behavior

## Planned Technology Areas
- Python for backend/service logic
- lightweight UI or console demo interface
- retrieval and grounding on approved project knowledge
- deterministic workflow and validation logic
- documentation, evaluation, and evidence tracking

## Repository Structure
- `README.md` — project overview and GitHub homepage
- `docs/requirements/` — charter, user stories, AI boundary matrix
- `docs/architecture/` — initial architecture and context diagram
- `docs/evaluation/` — evaluation planning and traceability notes
- `docs/weekly-reports/` — progress reporting
- `docs/ai-engineering-log.md` — AI-assisted work log
- `docs/model-selection.md` — Week 2: why an external foundation-model API was chosen
- `docs/prompt-specification.md` — Week 2: versioned prompt specification (V1.0, V2.0)
- `docs/prompt-evaluation.md` — Week 2: prompt evaluation test cases and results
- `docs/corpus-source-register.md`, `docs/rag-architecture.md`, `docs/rag-evaluation.md`, `docs/rag-failures.md` — Week 3: RAG corpus, architecture, evaluation, and documented failures
- `docs/architecture.md` — Week 4: current system architecture and the Week 2→3→4 progression
- `docs/tool-catalogue.md` — Week 4: tool schemas, authorization, and failure behavior
- `docs/tool-test-evidence.md` — Week 4: real test results for every failure/authorization scenario
- `docs/agent-task-contract.md`, `docs/agent-architecture.md` — Week 5: bounded agent goal, approved tools, limits, and terminal statuses
- `docs/memory-design.md`, `docs/interoperability.md` — Week 6: memory/state data-handling spec and the MCP-style interface spec for `check_timetable`
- `docs/evaluation.md`, `docs/guardrails.md`, `docs/failure-catalogue.md` — Week 7: 39-scenario evaluation benchmark, code-level guardrails, and six documented real failures with fixes
- `docs/RELEASE_NOTES_v1.0.0.md` — Week 8: the `v1.0.0` release notes
- `prompts/` — prompt and workflow notes
- `knowledge/` — approved project knowledge sources
- `agent-backend/` — FastAPI backend and LLM integration (see `agent-backend/README.md`); includes `agent-backend/tests/`
- `frontend/` — React (Vite) minimal test console: chat UI with source/timetable/ticket rendering and staff approve/reject controls
- `evidence/` — screenshots and traces
- `demo/` — demonstration materials

## Development Status — v1.0.0

All 8 weeks are complete. Week 1: planning and requirements. Week 2: a foundation-model baseline (Groq + versioned prompts). Week 3: retrieval-augmented generation over a controlled Makerere policy corpus, with cited sources. Week 4: explicit tool calling (`check_timetable`, `create_support_ticket`) executed by the application, never the model, with a separate human-approval step for ticket submission. Week 5: a bounded multi-step agent (plan→act→observe) that stops at one of six terminal statuses, built on the same tools. Week 6: bounded per-session memory (one prior turn, 24h TTL) and a privacy-filtered case-history store, both decoupled from — and unable to override — the agent's execution budgets or approval boundary. Week 7: a 39-scenario evaluation benchmark, documented code-level guardrails, and a failure catalogue of six genuine issues found and fixed during development. Week 8 (this release): hardening, the final README, and the `v1.0.0` tag.

This is an academic capstone prototype. It does not claim production deployment or live institutional integration, and uses only synthetic/public data (see `docs/corpus-source-register.md` and the data-handling notes in `docs/memory-design.md`).

## Running the System

The backend is a FastAPI app in `agent-backend/` (flat layout — `main.py` sits directly in that folder, not nested under `src/`).

### Prerequisites

- Python 3.11+ (tested on 3.13)
- Node.js 18+ and npm (only needed for the frontend)
- A free [Groq API key](https://console.groq.com) (the backend runs without one, but every LLM-backed endpoint returns `503` until it's set)

### 1. Clone the project

```bash
git clone <repository-url>
cd university-student-support-case-agent
```

### 2. Create and activate a virtual environment

```bash
cd agent-backend
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` and set at minimum:

```env
GROQ_API_KEY=your-real-key-here
```

Every other variable in `.env.example` has a working default — see the comments in that file for what each one does (RAG, tools, agent budgets, memory/state/case-history, all grouped by the week that introduced them). Never commit a real `.env` — it's already gitignored.

### 5. Build the RAG index (one-time, re-run if the corpus changes)

```bash
python ingest.py
```

Extracts, chunks, and embeds `docs/makerereUniversityPolicyDocs/` into a local Chroma index at `agent-backend/data/chroma/` (gitignored, regenerable, safe to re-run). The first run downloads a small local embedding model (~80MB, cached afterward — no API key needed for this step). Without it, the API still runs, but knowledge questions correctly report "no sufficiently relevant sources were found" instead of answering.

### 6. Start the backend

```bash
uvicorn main:app --reload
```

### 7. Open the interactive API docs

Visit http://127.0.0.1:8000/docs (Swagger/OpenAPI UI) to try every endpoint from the browser.

### 8. Run the automated tests

```bash
pytest -v
```

Expected: **178 passed**. The suite mocks the Groq API boundary, so it runs without a real key. One explicitly opt-in real-API test (`tests/test_integration_groq.py`) is skipped unless `GROQ_API_KEY` is configured — that's expected, not a failure.

### API endpoints

| Endpoint | Method | Purpose |
|---|---|---|
| `/health` | GET | Liveness check, independent of the LLM provider |
| `/api/v1/student-support` | POST | RAG-grounded answer; model may also request a tool directly (single round-trip, no multi-step planning) |
| `/api/v1/agent/student-support` | POST | **The full bounded agent** (Week 5): plan→act→observe loop over the same tools, stops at one of six terminal statuses (`completed`, `human_approval_required`, `max_iterations_reached`, `max_tool_calls_reached`, `tool_not_approved`, `llm_error`). Pass `X-Session-Id: <any string>` and `X-Memory: on` to enable one-prior-turn memory for that session. |
| `/api/v1/support-tickets/{id}` | GET | Read a ticket's current state |
| `/api/v1/support-tickets/{id}/approve` / `/reject` | POST | **Staff-only.** `PENDING_APPROVAL` → `SUBMITTED`/`REJECTED`. Not reachable by the model under any circumstances. |
| `/api/v1/cases/{student_id}` | GET / DELETE | Read or permanently delete a student's case-history (privacy-filtered summary fields only — see `docs/memory-design.md`) |
| `/api/v1/sessions/{run_id}` | GET | Read a persisted agent run's full state/step trace (keyed by the `run_id` returned in the agent response, *not* the `X-Session-Id` memory header — these are two different identifiers) |
| `/api/v1/memory/traces` | GET | Audit log of every memory/state read, write, and delete |

### Demo / testing identities

There is no real login. Authorization is simulated via request headers (`agent-backend/auth.py`) — this is explicit and documented, not a security boundary:

```bash
-H "X-User-Role: student"   # default if omitted
-H "X-User-Role: staff"     # required to approve/reject tickets
-H "X-User-Role: guest"     # used to demonstrate unauthorized tool calls
-H "X-User-Id: STU-1001"    # free-text synthetic student ID, any value works
```

Example end-to-end walkthrough:

```bash
# 1. Student asks the agent to help with a lost ID (creates a draft ticket)
curl -X POST http://127.0.0.1:8000/api/v1/agent/student-support \
  -H "Content-Type: application/json" -H "X-User-Id: STU-1001" \
  -d '{"message": "I lost my student ID card and need a replacement."}'
# -> status: "human_approval_required", a DRAFT-### ticket id in the response

# 2. Staff approves it
curl -X POST http://127.0.0.1:8000/api/v1/support-tickets/DRAFT-001/approve \
  -H "X-User-Role: staff"

# 3. A grounded knowledge question, with sources
curl -X POST http://127.0.0.1:8000/api/v1/student-support \
  -H "Content-Type: application/json" \
  -d '{"message": "What counts as examination malpractice at Makerere?"}'
```

## Frontend

`frontend/` is a minimal React (Vite) test console — not a polished student-facing app, just enough UI to exercise the backend above:

- A backend-URL field, a role selector (`student`/`staff`/`guest`, sent as `X-User-Role`), and a live health-check dot.
- A chat box rendering the model's answer, its `sources`, and any tool calls — `check_timetable` as a real table, `create_support_ticket` as a draft card with **Approve**/**Reject** buttons (staff role only).
- An agent-steps card showing the bounded agent's per-iteration plan/act/observe trace.

```bash
cd frontend
npm install
npm run dev   # starts the Vite dev server at http://localhost:5173
```

The backend must be running separately, with CORS already enabled for local development in `main.py`. Point the "Backend URL" field at wherever `uvicorn` is listening.

## Responsible AI / Engineering Note
This project follows a bounded, traceable AI design. AI is used only in approved support scenarios and must remain grounded in curated academic knowledge. High-impact operational decisions are intentionally withheld from automated processing and remain under human review. No confidential university or personal data is used in the project.

## GitHub Presentation Summary
This repository is the **v1.0.0 release** of an 8-week bounded AI-native/agentic capstone build: problem framing and requirement definition (Week 1), a foundation-model baseline (Week 2), retrieval-augmented generation over a controlled policy corpus (Week 3), explicit tool calling with human approval (Week 4), a bounded multi-step agent (Week 5), per-session memory and case history (Week 6), and an evaluation/guardrails/failure-catalogue pass (Week 7), hardened and tagged for final submission (Week 8). It is realistic, academically defensible, and safe for a student-support use case — not a production system.

## Project Evidence and Reporting
- Weekly progress reports for every week are in `docs/weekly-reports/` (Week 1 as PDF; Weeks 3-7 as Markdown).
- RAG evaluation and failures: `docs/rag-evaluation.md`, `docs/rag-failures.md`.
- Tool catalogue and test evidence: `docs/tool-catalogue.md`, `docs/tool-test-evidence.md`.
- Agent task contract: `docs/agent-task-contract.md`.
- Memory design and interoperability spec: `docs/memory-design.md`, `docs/interoperability.md`.
- 39-scenario evaluation benchmark, guardrails, and failure catalogue: `docs/evaluation.md`, `docs/guardrails.md`, `docs/failure-catalogue.md`.
- Execution traces against the live Groq API: `evidence/traces/`, `evidence/week7/`.
- **v1.0.0 release notes:** `docs/RELEASE_NOTES_v1.0.0.md`.

## Known Limitations

- **High-impact topics (admissions, grades, discipline, fees, legal, medical) are refused by prompt instruction, not a code-level topic filter.** The tool surface itself cannot act on these (no tool exists that could decide a grade, fee, or disciplinary outcome), but a sufficiently adversarial prompt could still get an inappropriate *sentence* out of the model's final text. Documented in `docs/agent-task-contract.md` (condition H5) and `docs/failure-catalogue.md` (Failure 6) — a known, inherent limitation of any LLM-backed system, not something this release claims to have fully solved.
- **Memory is intentionally one-turn, per-session, with a 24h TTL** (`docs/memory-design.md`) — not a full conversation history. A deliberate scope boundary, not an oversight.
- **Authorization is a header-based simulation** (`X-User-Role`), not real authentication. Documented in `agent-backend/auth.py` and `docs/tool-catalogue.md`.
- **The corpus is a fixed, synthetic/public snapshot** of Makerere policy documents (`docs/corpus-source-register.md`), not a live integration with any official university system.

## License and Safety Note
This repository is for academic and project demonstration purposes only. It does not contain real credentials, secrets, protected academic records, or production user data.
