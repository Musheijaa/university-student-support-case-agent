# UniSupport AI: A Bounded Agentic University Student-Support Case System
**Capstone Project Final Report Deliverable — Sections 1, 2, and 10**  
**Course:** BSE4104: Emerging Trends in Software Engineering  
**Institution:** Makerere University — College of Computing and Information Sciences (CoCIS), School of Computing and Informatics Technology (SCIT)  
**Group L:** Musheija Abraham (23/U/12139/EVE), Okema Paul Mark (23/U/16648/EVE), Akakikunda Benitah (23/U/05477/EVE), Kizito Ryan (23/U/10160/EVE), Mwesigwa Sean (21/U/12248/PS)  

---

## 1. Executive Summary *(Target: ~0.5 page)*

University students at Makerere University routinely experience severe administrative friction when navigating fragmented, opaque academic support procedures. Critical information regarding examination regulations, retake policies, course registration, and departmental procedures is scattered across static physical noticeboards, multi-page PDF handbooks, and siloed administrative desks. When students encounter routine administrative bottlenecks—such as portal access lockouts or timetable clashes—they are forced to pursue informal, untracked channels (in-person visits or unacknowledged emails). These inquiries lack unique tracking identifiers, leave students without visibility into case resolution, and overwhelm university support staff with repetitive administrative queries.

To address this challenge, **UniSupport AI** was developed as a bounded, AI-native student-support case agent serving two primary user groups: (1) undergraduate students seeking prompt, grounded procedural answers and structured case tracking, and (2) departmental support staff requiring auditable, pre-triaged support requests. The system deliberately diverges from open-ended conversational bots by coupling a fast foundation model (Groq `openai/gpt-oss-20b`) with a deterministic software scaffold. The architecture coordinates semantic Retrieval-Augmented Generation (RAG) over 12 verified Makerere University policy documents, explicit tool dispatch (synthetic timetable lookup and support ticket drafting), a 6-stage cognitive loop (Sense → Context → Plan → Act → Observe → Stop), and bounded per-session memory.

Empirical evaluation demonstrates robust performance: across a rigorous 39-scenario benchmark spanning normal, edge, incorrect information, adversarial injection, tool failure, and unauthorized execution categories, the system achieved a 100% pass rate (39/39 passing, integrated within a 178-test automated suite). Policy responses achieved zero citation fabrication by generating source metadata strictly from deterministic vector-store records. Crucially, code-level guardrails proved completely resilient against prompt injection, privilege escalation, and loop exhaustion. The system's principal limitation is its deployment as an academic prototype operating on synthetic timetable/ticket databases and simulated header-based roles (`X-User-Role`), without live integration into Makerere's enterprise Academic Information Management System (AIMS). Furthermore, high-consequence academic decisions (grades, fees, disciplinary hearings, and admissions) are strictly blocked from autonomous resolution and mandate human escalation.

> **Executive Architectural Principle:** UniSupport AI enforces an unyielding architectural boundary: the foundation model provides cognitive synthesis, natural language triage, and evidence explanation, while deterministic code enforces authorization, tool registries, execution budgets, and an immutable Human-in-the-Loop gate for ticket approval.

---

## 2. Problem Context and Requirements *(Target: 0.75 – 1 page)*

### 2.1 Problem Context and Primary End-to-End Workflow
University academic support at Makerere involves high-volume, multi-channel interactions where students require timely guidance on deadlines, examination rules, and course logistics. Traditional institutional workflows suffer from three systemic points of failure: (a) students struggle to extract definitive answers from dense, multi-page PDFs; (b) informal grievance reporting produces untracked cases with zero accountability; and (c) students must repetitively re-explain issues across visits because institutional desks lack session memory. UniSupport AI replaces this friction with an auditable, multi-stage primary workflow:

- **Step 1 (Sense & Validate):** The student submits a natural language message. The application's API gateway parses the payload, enforces Pydantic bounds (1–2,000 characters, non-empty), and extracts the actor's role from trusted headers (`X-User-Role`).
- **Step 2 (Context Retrieval & Planning):** The system semantically queries the ChromaDB policy store to retrieve top-$k$ evidence chunks (filtered at a minimum cosine similarity of 0.35). An initial cognitive budget (`AGENT_MAX_ITERATIONS=4`, `MAX_TOOL_CALLS=3`) is allocated.
- **Step 3 (Cognitive Deliberation):** The foundation model evaluates the student inquiry alongside retrieved policy evidence and prior session context to decide the next step: formulate an answer, inspect schedules via `check_timetable`, or draft a ticket via `create_support_ticket`.
- **Step 4 (Deterministic Action & Guardrail Gate):** If a tool is requested, the application validates the tool name against an immutable registry (`TOOL_REGISTRY`), verifies role authorization, executes the python tool, and validates the output schema.
- **Step 5 (Observation & Re-planning):** The tool observation is ingested back into context, enabling the model to summarize findings or conclude.
- **Step 6 (Terminal Stop & Human-in-the-Loop Gate):** Execution halts deterministically at one of six terminal statuses. If a ticket was created, it is stored as `PENDING_APPROVAL`, halting autonomous progression (`human_approval_required`) until authenticated staff review, approve, or reject it via dedicated endpoints.

### 2.2 System Requirements and Acceptance Criteria
The project established concrete Functional Requirements (FR), Non-Functional Requirements (NFR), and testable Acceptance Criteria (AC):

- **FR1 (Grounded Policy Assistance):** The system shall interpret free-text queries and retrieve relevant policy chunks from official documentation. *AC:* Answers must cite exact document IDs and page numbers (e.g., DOC001 p12). Queries with zero matching evidence must return an explicit "no evidence found" statement without hallucination.
- **FR2 (Schedule Lookup):** The system shall query course schedules via `check_timetable`. *AC:* Valid course codes return synthetic class sessions; nonexistent codes return structured errors (`Course not found`) rather than fabricated schedules.
- **FR3 (Support Case Ticketing):** The system shall generate structured support tickets via `create_support_ticket` for issues requiring departmental action. *AC:* Every generated ticket must receive a unique ID, initialize in `PENDING_APPROVAL` status, and record category/summary.
- **FR4 (Human-in-the-Loop Governance):** The system shall restrict ticket approval and rejection exclusively to university staff. *AC:* Staff endpoints (`/approve`, `/reject`) must enforce role authentication (`X-User-Role: staff`); student attempts must return HTTP 403 Forbidden.
- **FR5 (Bounded Per-Session Memory):** The system shall maintain short-term context across conversation turns. *AC:* Exactly one prior turn summary is prepended to subsequent turns (24-hour TTL); follow-up queries regarding an active ticket must resolve without re-prompting.
- **NFR1 (Deterministic Safety):** Cognitive execution loops must be strictly bounded. *AC:* Loops must terminate deterministically within 4 iterations or 3 tool calls without hanging.
- **NFR2 (Data Privacy & Minimization):** Historical case retention must exclude raw conversation transcripts and student PII. *AC:* Attempted ingestion of forbidden keys (`raw_transcript`, `phone_number`) must raise a `PrivacyViolationError`.
- **NFR3 (Adversarial Robustness):** The agent must resist direct and indirect prompt injection. *AC:* System prompt override attempts and unauthorized tool dispatch commands must be safely neutralized.

### 2.3 AI Boundary Matrix
A foundational architectural safeguard of UniSupport AI is the explicit partitioning of responsibilities across probabilistic AI, deterministic software logic, and mandatory human authorization. This tripartite division is formalized in Table 2.1.

**Table 2.1: UniSupport AI Boundary Matrix defining operational allocation**

| AI May Do (Probabilistic) | Stays Deterministic (Application Code) | Requires Human Approval (Mandatory HITL) |
|---|---|---|
| Synthesize natural language explanations grounded strictly in retrieved policy chunks. | Query validation, Pydantic length bounds (1–2,000 chars), and input sanitization. | Final determination on admissions, grading changes, fee waivers, or disciplinary actions. |
| Triage and classify unstructured student complaints into support categories. | Role extraction from `X-User-Role` header and Role-Based Access Control (RBAC). | Approving or transitioning a support ticket from `PENDING_APPROVAL` to `SUBMITTED`. |
| Select the appropriate tool (`check_timetable` or `create_support_ticket`) based on intent. | Enforcement of the tool allow-list (`frozenset(TOOL_REGISTRY)`) and schema validation. | Rejecting or permanently closing an active student support ticket. |
| Draft concise ticket summaries, categories, and descriptions from student input. | UUID/ticket ID generation, timestamping, and SQLite database read/write transactions. | Overriding deterministic departmental routing tables or escalation rules. |
| Formulate clarifying questions when student intent or course parameters are ambiguous. | Enforcement of dual loop budgets (`AGENT_MAX_ITERATIONS=4`, `MAX_TOOL_CALLS=3`). | Accessing confidential student academic transcripts or real-world university records. |

### 2.4 Project Success Measures
Project success was quantitatively evaluated against five pre-defined engineering criteria: 
1. **Grounded Retrieval Accuracy:** $\ge 90\%$ of in-corpus policy questions answered with correct document citations (achieved 100% on the evaluation set);
2. **Zero Autonomous Escalation:** 0 instances of autonomous ticket approvals, fee decisions, or grade alterations across all adversarial tests (achieved 0/14);
3. **Loop Termination Reliability:** 100% of agent runs terminate at an explicit terminal state within budget bounds without hanging (achieved 100%);
4. **Failure Containment:** 100% of simulated tool and provider failures handled gracefully via structured error observations without process crash (achieved 100%); and
5. **Test Suite Coverage:** Full system regression pass across $\ge 150$ automated tests (achieved 178 passing tests).

---

## 10. Results, Limitations and Professional Reflection *(Target: 0.75 – 1 page)*

### 10.1 What Works: Verified System Strengths
The empirical evaluation demonstrates that UniSupport AI operates reliably within its defined academic support boundaries. Key achievements include:
- **Verifiable Source Grounding:** The RAG subsystem reliably grounds policy explanations in the Makerere policy corpus. Because citations are assembled from deterministic ChromaDB metadata rather than model text generation, citation hallucination is eliminated (DOC001 to DOC018).
- **Resilient Agent Orchestration:** The orchestrator loop bounds cognitive execution through independent iteration and tool budgets. The system cleanly halts in one of six terminal statuses, preventing costly provider loops or hanging requests.
- **Immutable Human-in-the-Loop Barrier:** Support tickets are strictly drafted in `PENDING_APPROVAL` status. Transitions to `SUBMITTED` or `REJECTED` are architecturally isolated behind staff-authenticated REST endpoints that the LLM has no code path to execute.
- **Multi-Layer Adversarial Defense:** The system demonstrated complete resilience across 14 dedicated adversarial penetration tests, neutralizing prompt injections, instruction overrides, system prompt extraction, and role header spoofing.
- **Privacy-Preserving Continuity:** Per-session memory maintains multi-turn context (e.g., resolving follow-up questions to an active ticket) while the case history store enforces strict data minimization, rejecting raw transcripts and student PII via `PrivacyViolationError`.

### 10.2 What Does Not Work and Genuine Technical Failures
Development and rigorous testing uncovered several non-contrived architectural failure modes that highlight the boundaries of current techniques:
- **Chunk-Boundary Bisection (Failure F4):** The fixed-offset chunking strategy (1,000 characters with 150-character overlap) operates without syntactic awareness. In testing, chunk boundaries occasionally bifurcated legal sub-clauses across page boundaries, resulting in incomplete evidence retrieval.
- **Scanned PDF Text Inaccessibility:** Six of the original 18 university policy PDFs were scanned image-only documents. Standard text extraction (`pypdf`) yielded zero extractable characters, necessitating their manual removal from the corpus manifest until OCR pipelines are introduced.
- **Provider Non-Compliance with Tool Choice:** When setting `tool_choice="none"` after budget exhaustion, third-party LLM providers occasionally continued returning tool-call JSON objects. This forced the implementation of hard code-level interception within `orchestrator.py` to suppress unauthorized downstream dispatches.
- **Rigid Timetable Lookup Semantics:** The `check_timetable` tool relies on exact alphanumeric course code matching. Queries with minor spelling variations or natural language course descriptions fail to match without a semantic alias layer.

### 10.3 Remaining Risks, Cost, and Latency
Several residual risks and operational trade-offs remain for real-world institutional adoption:
1. **Simulated Authorization:** Role verification relies on the HTTP `X-User-Role` header. While sufficient for a capstone prototype, deploying this in production without institutional SSO (e.g., OAuth2/OpenID Connect linked to Makerere EduID) would allow trivial header spoofing by malicious clients.
2. **Upstream API Availability:** The system depends on external foundation model endpoints (Groq). Cloud network latency, token rate limits, and provider downtime (manifesting as HTTP 502/503 errors) represent points of vulnerability outside the application's control.
3. **Cost and Latency Profile:** The system demonstrates exceptional cost efficiency: local MiniLM embeddings incur zero API charges, while Groq inference averages under $0.001 per student turn. Latency averages 1.2–2.5 seconds per turn across multi-step agent iterations, providing responsive real-time interaction but remaining subject to cloud API spikes.

### 10.4 Future Work and Professional Reflection
Future engineering enhancements should prioritize four key areas: 
1. Integrating enterprise institutional authentication (EduID SSO) to replace simulated headers;
2. Establishing live read/write adapters with Makerere's Academic Information Management System (AIMS) for authentic timetable and enrolment data;
3. Implementing structure-aware semantic chunking (e.g., Markdown/HTML header hierarchy parsing) combined with OCR preprocessing for historical circulars; and
4. Incorporating an active semantic classifier for early detection and redirection of out-of-scope high-impact requests.

**Professional Reflection and Human Responsibility:** Developing UniSupport AI reinforced a critical paradigm in AI-native software engineering: probabilistic foundation models must never be entrusted with authoritative institutional power. In high-stakes university environments, allowing an LLM to autonomously approve financial waivers, alter grades, or resolve disciplinary hearings creates unacceptable legal, ethical, and institutional liabilities. Software engineers bear the professional duty to bound AI systems through robust, deterministic application layers, explicit tool registries, transparent audit trails, and non-negotiable Human-in-the-Loop checkpoints. UniSupport AI demonstrates that when artificial intelligence is positioned strictly as a cognitive amplifier for information triage, retrieval, and draft generation—while preserving deterministic governance and human primacy—it provides profound administrative relief without compromising institutional integrity.
