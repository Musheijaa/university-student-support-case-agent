# Week 6 Progress Report

**Group L — UniSupport AI: A Bounded Agentic Student Support Case System**  
**Week ending:** 9th October 2026  
**Submitted by:** Kizito Ryan  

---

## 1. Work Completed Against Week 6 Deliverables

The objective of Week 6, per the capstone project brief, was to establish **Memory, State, and Interoperability**: implementing justified persistent state and memory, defining data governance and privacy boundaries, demonstrating memory impact on multi-turn interactions, and specifying an interoperable interface.

Work completed against the five defined Week 6 deliverables:

1. **State Model (`agent-backend/agent/state.py`, `agent-backend/agent/state_store.py`)**:
   - Implemented an explicit session-state object tracking the agent's 6-stage cognitive lifecycle (`INITIALIZED` → `SENSE` → `CONTEXT` → `PLAN` → `ACT` → `OBSERVE` → `REPLAN` → `TERMINAL`).
   - Defined strict state transition validation rules (`ALLOWED_STATUS_TRANSITIONS` and `ALLOWED_STAGE_TRANSITIONS`) raising `InvalidStateTransitionError` on illegal paths. Terminal statuses (`completed`, `human_approval_required`, `max_iterations_reached`, `max_tool_calls_reached`, `tool_not_approved`, `llm_error`) operate as permanent, immutable sinks.
   - Built a persistent SQLite state store (`session_state.db`) capturing the full agent state, execution steps, iteration counts, and tool metrics per episode.

2. **Memory Design and Data Handling Note (`docs/memory-design.md`)**:
   - Authored the formal specification defining what is stored, rationale, access controls, retention, and deletion.
   - Built a **Privacy-Preserving Case History Store** (`agent-backend/agent/case_history.py`) allowing retention of only approved fields (`case_id`, `student_id`, `category`, `summary`, `status`, `action_taken`, `ticket_id`, `created_at`).
   - Implemented runtime rejection (`PrivacyViolationError`) against storing raw chat transcripts (`FORBIDDEN_TRANSCRIPT_KEYS`) or personal identity attributes beyond student ID (`FORBIDDEN_PERSONAL_DATA_KEYS`).
   - Built bounded **Per-Session Memory** (`agent-backend/agent/memory.py`) persisting exactly one prior turn per session in `data/sessions.db` with a configurable 24-hour TTL (`MEMORY_TTL_HOURS`) and purge routines.

3. **Working Memory/State Demonstration (`evidence/traces/week6/`)**:
   - Captured four real end-to-end execution traces against the live Groq API (`openai/gpt-oss-20b`) demonstrating a 2-turn dialogue with memory disabled versus enabled (`evidence/traces/week6/README.md`).
   - In Turn 1, the student reports a lost ID, and the agent drafts a ticket (`human_approval_required`).
   - In Turn 2, the student asks: *"What is the status of that ticket?"*.
   - **With Memory OFF**: The agent has no referent and correctly refuses to guess or invent a status.
   - **With Memory ON**: The agent remembers that a draft ticket was created and informs the student that it is pending staff review, without hallucinating ticket IDs or taking unapproved actions.

4. **Integration / MCP-Style Interface Specification (`docs/interoperability.md`)**:
   - Specified the internal capability `check_timetable` as an MCP-style (Model Context Protocol) tool interface.
   - Formally documented tool metadata, JSON Schema inputs (`course_code`, optional ISO `date`), output schemas (success sessions array or structured error), side-effect classification (read-only), role authorization (`student`/`staff` allowed, `guest` rejected), and security boundaries (synthetic data, no PII, bounded responses, error containment).

5. **Week 6 Progress Report**:
   - Completed this document (`docs/weekly-reports/week6_Progress_Report.md`), detailing engineering outcomes, architectural decisions, failure modes, contribution accounting, and the Week 7 plan.

---

## 2. Key Engineering Decisions

### Why Case History Was Chosen
University student support workflows are inherently case-centric. Students frequently return with follow-up questions regarding ongoing academic issues (e.g., replacement of IDs, timetable clashes, admission procedures, or examination concerns). Storing a structured case history rather than unbounded conversation logs was chosen for two critical reasons:
1. **Privacy & Data Minimization**: Retaining verbatim chat transcripts creates unacceptable data privacy risks under university data handling guidelines and risks prompt injection/history poisoning across sessions. Bounding case history to approved summary fields (`case_id`, `student_id`, `category`, `summary`, `status`, `action_taken`, `ticket_id`) provides institutional traceability while ensuring zero personal data leakage.
2. **Deterministic Governance**: Structured case summaries allow university staff to audit and inspect previous case outcomes through dedicated endpoints (`GET /api/v1/cases/{student_id}` and `DELETE /api/v1/cases/{student_id}`) without exposing internal model prompts or unparsed text.

### Why Memory Is Context-Only
Per `docs/memory-design.md` and `docs/agent-architecture.md`, memory was intentionally decoupled from the core agent execution loop:
1. **Passive Context Prefixing**: Memory sits beside the cognitive loop. Before execution, `main.py` fetches the single prior turn and passes it into `orchestrator.py`, which prepends a bounded summary to the prompt (`_prefix_prior_context`). After execution, the current turn is updated.
2. **No Autonomous Agency from Memory**: Memory is strictly forbidden from triggering tools on its own, modifying execution budgets (`MAX_TOOL_CALLS`, `AGENT_MAX_ITERATIONS`), altering terminal stop conditions, or bypassing role authorization.
3. **Preservation of Human Approval Boundaries**: Memory cannot approve, reject, or submit tickets. High-impact state transitions remain strictly confined to staff-only HTTP endpoints (`/api/v1/support-tickets/{id}/approve`), completely out of reach of the LLM and memory subsystems.

---

## 3. Failures and Challenges

1. **Model Hallucination of Ticket Status Resolution**:
   - *Challenge*: During early testing of Turn 2 follow-ups (*"What is the status of that ticket?"*), the LLM occasionally attempted to invent ticket numbers or claim it had queried an external database.
   - *Resolution*: Hardened the prior-context injection prompt to explicitly provide the terminal status of the prior turn (`human_approval_required`) and inform the model that ticket approval is pending human staff review, preventing fabricated status reports.
2. **Guarding Against Transcript Smuggling in Case Store**:
   - *Challenge*: Case history payloads could inadvertently receive raw chat dictionaries or PII attributes from client requests or unvetted scripts.
   - *Resolution*: Implemented strict programmatic filters in `agent/case_history.py` (`FORBIDDEN_TRANSCRIPT_KEYS` and `FORBIDDEN_PERSONAL_DATA_KEYS`). Any write attempt containing fields like `raw_transcript`, `messages`, `email`, or `phone_number` immediately raises a `PrivacyViolationError` and logs an audit failure trace.
3. **State Machine Sink Re-entrancy**:
   - *Challenge*: Edge cases where an agent run that terminated with `completed` or `max_tool_calls_reached` could be mistakenly invoked for another transition, risking indeterminate states.
   - *Resolution*: Configured `ALLOWED_STATUS_TRANSITIONS` such that all terminal statuses map to empty sets (`frozenset()`), ensuring that any attempt to transition out of a terminal state raises an `InvalidStateTransitionError`.
4. **Database State Isolation**:
   - *Challenge*: Potential risk of schema lock contention or accidental state loss if memory and operational tickets shared a database file.
   - *Resolution*: Split storage into independent SQLite databases (`data/sessions.db`, `data/tickets.db`, `data/case_history.db`, and `data/session_state.db`). Clearing session memory or resetting TTL cache leaves ticket and audit states completely untouched.

---

## 4. GitHub Commit & PR Links

- **Pull Requests:**
  - **PR #12:** `Week 6: bounded per-session memory + with/without comparison` (Merged via commit `ef18bb9`)
  - **PR #11:** `docs(week5): add Week 5 progress report` (Merged via commit `7fcd2f2`)
- **Key Commits:**
  - `63a1fc8`: Added State Store, case memory, cognitive lifecycle stages, and audit traces (`agent-backend/agent/`)
  - `5342574`: Implemented bounded per-session memory, with/without comparison traces, interoperability spec, and memory design
  - `76723a1`: Merge branch `main` into `week6-memory`
  - `ef18bb9`: Merge pull request #12 into `main`
- **Key Documentation & Evidence Files:**
  - `docs/memory-design.md`: Memory design and data handling specification
  - `docs/interoperability.md`: MCP-style interface specification for `check_timetable`
  - `docs/agent-architecture.md`: Cognitive lifecycle architecture and memory hook diagram
  - `evidence/traces/week6/README.md`: With/without memory test methodology and excerpts
  - `evidence/traces/week6/trace_with_memory_turn1.json`, `trace_with_memory_turn2.json`
  - `evidence/traces/week6/trace_without_memory_turn1.json`, `trace_without_memory_turn2.json`
- **Automated Test Evidence (All Passing):**
  - `agent-backend/tests/test_agent_memory.py`: Bounded per-session memory operations, upsert behavior, and TTL expiration
  - `agent-backend/tests/test_state_model.py`: 6-stage lifecycle transitions, terminal sink enforcement, and state store
  - `agent-backend/tests/test_case_history.py`: Approved fields persistence, raw transcript rejection, and PII blocking
  - `agent-backend/tests/test_memory_api.py`: REST API endpoints for session state and case history
  - `agent-backend/tests/test_memory_traces.py`: Audit logging of every READ, WRITE, and DELETE memory operation

---

## 5. Individual Contributions

| Member | Task Owned | Evidence Link |
|---|---|---|
| **Akakikunda Benita** | Bounded per-session memory store (`agent/memory.py`), memory context injection in orchestrator (`orchestrator.py`), live Groq trace capture and evaluation (`evidence/traces/week6/`), Memory Design documentation (`docs/memory-design.md`), Interoperability MCP specification (`docs/interoperability.md`), Week 6 Progress Report | Commits `5342574`, `76723a1`, PR #12; files in `agent-backend/agent/memory.py`, `docs/memory-design.md`, `docs/interoperability.md`, `evidence/traces/week6/` |
| **Mwesigwa Sean** | SQLite session-state store (`agent/state_store.py`), 6-stage cognitive lifecycle state model and transition validation (`agent/state.py`), privacy-preserving case history store (`agent/case_history.py`), memory observability logging (`agent/traces.py`), test suites (`test_state_model.py`, `test_case_history.py`, `test_memory_api.py`, `test_memory_traces.py`) | Commit `63a1fc8`; files in `agent-backend/agent/state.py`, `agent-backend/agent/state_store.py`, `agent-backend/agent/case_history.py`, `agent-backend/tests/` |
| **Okema Paul Mark** | Orchestrator and API integration for state lifecycle hooks, Application Requirements search tool (`tools/application_requirements_tool.py`), test review, and boundary constraint verification | Commit `63a1fc8`, `5342574`; files in `agent-backend/tools/application_requirements_tool.py`, `agent-backend/agent/orchestrator.py` |
| **Kizito Ryan** | Schemas and endpoint support (`schemas.py`, `main.py`), verification of data retention policies, TTL expiration testing, and API serialization | Commits `63a1fc8`, `5342574`; files in `agent-backend/schemas.py`, `agent-backend/main.py` |
| **Musheija Abraham (Mwesigwa Duncan)** | Branch coordination, pull request code reviews and merges (PR #11, PR #12), architectural documentation alignment (`docs/agent-architecture.md`) | Commits `7fcd2f2`, `ef18bb9`; PR #11, PR #12; file `docs/agent-architecture.md` |

---

## 6. Plan for Week 7: Evaluation, Observability, and Guardrails

**Focus (12th Oct – 16th Oct 2026):** Produce rigorous, empirical evidence demonstrating that UniSupport AI is reliable, grounded, inspectable, and safe within its bounded student-support domain.

### Activities & Deliverables
1. **30+ Scenario Evaluation Dataset & Results**:
   - Construct a structured evaluation benchmark of at least 30 distinct scenarios categorized across six archetypes:
     - *Normal*: Standard academic policy queries, valid timetable lookups, legitimate ticket drafting.
     - *Edge*: Boundary conditions (e.g., courses across multiple campuses, end-of-semester dates, ambiguous multi-intent requests).
     - *Incorrect Information*: Inquiries regarding non-existent courses or false policy claims.
     - *Adversarial*: Direct prompt injection attempts, system prompt exfiltration, instruction overrides, and jailbreak phrases.
     - *Tool Failures*: Missing data files, corrupted databases, simulated timeout errors.
     - *Unauthorized Actions*: `guest` role tool execution attempts, student attempts to invoke ticket approval/rejection endpoints.
   - Measure performance across six objective criteria: **Task Completion Rate**, **Groundedness Score** (absence of hallucination), **Tool Selection Accuracy**, **Instruction Following**, **Latency (p50/p95)**, and **Safety/Authorization Violation Count** (zero tolerance).

2. **Observability & Tracing Evidence**:
   - Enhance logging to record comprehensive audit traces for each execution: model version, prompt template version, retrieved context passages and relevance scores, tool arguments/responses, execution step latency, error codes, and final terminal statuses.
   - Export structured JSON and markdown traces for representative evaluation runs.

3. **Guardrail Implementation Evidence**:
   - Verify and document code-level guardrails:
     - Strict Pydantic schema validation on all inputs and outputs.
     - Tool allow-list enforcement in `tools/registry.py`.
     - Explicit role-based access control (`X-User-Role`).
     - Hard iteration and tool call budgets (`AGENT_MAX_ITERATIONS=4`, `MAX_TOOL_CALLS=3`).
     - Human-in-the-loop approval barriers for ticket creation.
     - Prompt injection detection and boundary markers.

4. **Failure Catalogue with Remediation and Re-test Evidence**:
   - Identify and document at least five genuine, observed failure modes across the system (e.g., retrieval misses, ambiguity handling, tool parameter mismatch, boundary edge-cases).
   - Document root-cause analysis, implement engineering remediations, and present before-and-after re-test evidence.

5. **Week 7 Progress Report**:
   - Summarize evaluation metrics, observability artifacts, guardrail validation, and remediation outcomes in a concise 2-page report.
