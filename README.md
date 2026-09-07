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
- `prompts/` — prompt and workflow notes
- `knowledge/` — approved project knowledge sources
- `src/` — implementation artifacts as they are added
- `tests/` — validation artifacts
- `evidence/` — screenshots and traces
- `demo/` — demonstration materials

## Development Status
Week 1 planning and requirement framing are complete and documented in the repository. The project is intentionally scoped for an 8-week academic execution and does not claim production deployment or live institutional integration.

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
