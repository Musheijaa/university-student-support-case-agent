# University Student-Support Case Agent

A bounded AI-native student-support case agent for routine academic-support queries, simulated case-status checks, and controlled support-ticket workflows.

## Project Summary
This project is a BSE4104 capstone prototype for an AI-native student-support system at Makerere University. The solution is intentionally limited to a realistic academic-support domain: helping students understand approved guidance, checking simulated timetable or case-status information, and creating or routing routine support requests in a traceable workflow.

The system is designed around an important principle: AI is used where it adds value in understanding, retrieval, explanation, and workflow assistance, while deterministic software remains responsible for validation, authorization, routing rules, and controlled system actions. Any high-impact or sensitive decisions remain under human approval.

## Team
- OkemaPaulMark — paulokema342@gmail.com
- KizitoRyan — ryankizito08@gmail.com
- Benita Akakikunda — benitaakakikunda@gmail.com
- Seand1975
- Mwesigwa Duncan — mwesigwaduncan@gmail.com

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
- `prompts/` — prompt and workflow notes
- `knowledge/` — approved project knowledge sources
- `agent-backend/` — FastAPI backend and LLM integration (see `agent-backend/README.md`); includes `agent-backend/tests/`
- `frontend/` — React (Vite) dashboard scaffold; no application code implemented yet
- `evidence/` — screenshots and traces
- `demo/` — demonstration materials

## Development Status
Week 1 planning and requirement framing are complete and documented in the repository. Week 2 adds a working foundation-model baseline: a FastAPI backend that sends student questions to an external LLM (Groq) through a versioned prompt and returns a structured response, with no document retrieval or agentic behavior yet. The project is intentionally scoped for an 8-week academic execution and does not claim production deployment or live institutional integration.

## Week 2: Running the Baseline

The Week 2 baseline is a FastAPI backend in `agent-backend/` (flat layout —
`main.py` sits directly in that folder, not nested under `src/`) with two
endpoints:

- `GET /health` — liveness check, independent of the LLM provider.
- `POST /api/v1/student-support` — sends a student's question to Groq using a versioned prompt (see `agent-backend/llm/prompts.py` and `docs/prompt-specification.md`) and returns a structured JSON response.

It intentionally does **not** yet include document retrieval (RAG), tools/function calling, case memory, or agent orchestration — those are planned for later weeks (see `agent-backend/README.md`).

A `frontend/` folder holds a scaffolded React (Vite) dashboard — dependencies installed, no application code written yet. See [Frontend scaffold](#frontend-scaffold) below.

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

Copy the example file and fill in a real Groq API key locally (never commit it):

```bash
cp .env.example .env
```

Then edit `.env` and set:

```env
GROQ_API_KEY=your-real-key-here
GROQ_MODEL=openai/gpt-oss-20b
```

Get a key from https://console.groq.com. Without a configured key, the API still runs and `/health` still works, but `/api/v1/student-support` returns `503`.

### 5. Start the backend

Run from inside `agent-backend/`:

```bash
uvicorn main:app --reload
```

### 6. Open the interactive API docs

Visit http://127.0.0.1:8000/docs (Swagger/OpenAPI UI) to try both endpoints from the browser.

### 7. Test `/health`

```bash
curl http://127.0.0.1:8000/health
```

Expected: `{"status":"ok"}`

### 8. Test `/api/v1/student-support`

```bash
curl -X POST http://127.0.0.1:8000/api/v1/student-support \
  -H "Content-Type: application/json" \
  -d '{"message": "How does course registration work?"}'
```

Expected (once `GROQ_API_KEY` is set): a JSON body with `response`, `prompt_version`, and `model` fields.

### 9. Run the automated tests

Run from inside `agent-backend/`:

```bash
pytest -v
```

## Frontend scaffold

`frontend/` is a React app scaffolded with Vite (`npm create vite@latest frontend -- --template react`). Only dependencies are installed — no dashboard UI has been implemented yet; that begins in a later week.

```bash
cd frontend
npm install   # already done; re-run only if node_modules is missing
npm run dev   # starts the Vite dev server to confirm the scaffold runs
```

The test suite mocks the Groq API boundary, so it runs without a real API key. A separate, explicitly-opt-in real-API test (`tests/test_integration_groq.py`) is skipped unless `GROQ_API_KEY` is configured.

## Responsible AI / Engineering Note
This project follows a bounded, traceable AI design. AI is used only in approved support scenarios and must remain grounded in curated academic knowledge. High-impact operational decisions are intentionally withheld from automated processing and remain under human review. No confidential university or personal data is used in the project.

## GitHub Presentation Summary
This repository demonstrates a professional Week 1 capstone foundation for a bounded AI-native support workflow. It focuses on problem framing, requirement definition, AI boundary design, and early architecture planning in a way that is realistic, academically defensible, and safe for student-support use cases.

## Project Evidence and Reporting
- Week 1 details and progress are recorded in `docs/weekly-reports/week-1-progress-report.md`
- The AI engineering log is in `docs/ai-engineering-log.md`
- The initial system context is in `docs/architecture/initial-architecture.md`
- The ClickUp task plan is in `docs/clickup-week1-task-plan.md`

## License and Safety Note
This repository is for academic and project demonstration purposes only. It does not contain real credentials, secrets, protected academic records, or production user data.
