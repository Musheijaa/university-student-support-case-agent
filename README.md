# University Student-Support Case Agent

## Project Team
- OkemaPaulMark — paulokema342@gmail.com
- KizitoRyan — ryankizito08@gmail.com
- Benita Akakikunda — benitaakakikunda@gmail.com
- Seand1975
- Mwesigwa Duncan — mwesigwaduncan@gmail.com

## Problem Statement
University students often need quick answers to routine academic-support questions, such as how to interpret a timetable, when a course-related issue should be escalated, or how to start a support case for an academic concern. These requests are often spread across different university documents, email threads, and support procedures. Without a governed and traceable workflow, students may receive inconsistent guidance and support teams may struggle to monitor case status, route issues, and document decisions.

## Target User
The primary user is a university student who needs help with common academic-support questions and case initiation. Secondary users include academic support staff and student support administrators who review, validate, and route student requests.

## Project Objective
This project aims to prototype a bounded AI-native student-support case agent that can help students with common academic-support questions using approved university and course documents. The agent will support a traceable workflow for retrieving relevant guidance, checking simulated case-status information, creating or updating a support case, and routing the case to the correct support queue when appropriate.

## Primary Workflow
1. A student submits a question or request through the application.
2. The system identifies the relevant approved knowledge source and retrieves context.
3. The AI summarizes or explains the guidance in a supported and grounded way.
4. If the request involves a case, the system checks simulated student case/status information.
5. The system validates required inputs and creates a support ticket or case record.
6. The case is routed according to deterministic rules and business logic.
7. Human staff review and approval are required for escalation or any high-impact action.

## Role of AI
AI is used for bounded language understanding, retrieval assistance, summarization, question interpretation, intent classification, and workflow support. The AI helps a student understand approved guidance and assists with structured case creation when grounded in validated sources and approved business rules.

## Deterministic Responsibilities
The software layer remains responsible for: validating required fields, checking simulated status information, enforcing routing rules, authorizing access within the approved scope, creating structured records, and preventing unsupported actions. Deterministic logic must also maintain the rules for what the system may and may not do.

## Human Approval Boundaries
Human approval is required for any escalation outside the bounded workflow, for any decision that affects a student’s academic record, grading, fees, disciplinary action, medical or legal matters, or any other high-impact outcome. The project intentionally avoids these decisions.

## Initial Scope
This project will cover the following bounded scope:
- grounded student questions using approved academic documents
- simulated timetable or case-status lookups
- case creation and routing for routine academic support issues
- session/case state tracking during a workflow
- deterministic validation and controlled routing
- human-in-the-loop review for escalations and high-impact decisions

## Planned Technology Areas
- Python-based application logic or backend service
- lightweight web or console UI for demonstration
- retrieval and document grounding patterns with approved source material
- structured workflow orchestration
- deterministic validation and routing rules
- documentation, traceability, and evaluation artifacts

## Repository Structure
The repository is organized to separate project requirements, architecture decisions, evidence, and weekly planning from implementation artifacts.

## Development Status
This repository currently contains the Week 1 planning and documentation baseline for the capstone project. Features and implementation details are intentionally scoped to a realistic 8-week academic project and do not claim production-level deployment or live data integration.

## Responsible AI / Engineering Note
This project follows a bounded, traceable AI design. AI is used to support student queries and workflow coordination only within controlled, approved boundaries. All decisions with significant operational or academic impact remain under human review. All knowledge sources are synthetic, public, or approved by the project team; no confidential university or personal data is used.

## Repository Layout
- `README.md` — project overview and scope
- `docs/requirements/` — project charter, user stories, AI boundary matrix
- `docs/architecture/` — initial architecture and planned system boundaries
- `docs/evaluation/` — evaluation approach and traceability notes
- `docs/weekly-reports/` — Week 1 progress and future reporting
- `docs/ai-engineering-log.md` — record of material AI-assisted work
- `prompts/` — prompt and workflow documentation
- `knowledge/` — approved knowledge sources and prompts for ground truth
- `src/` — implementation artifacts as they are added
- `tests/` — validation and test artifacts
- `evidence/` — screenshots and traces for project record
- `demo/` — demonstration material
