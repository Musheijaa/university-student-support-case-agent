# Project Charter: University Student-Support Case Agent

## 1. Project Title
University Student-Support Case Agent

## 2. Problem Statement
Many students need quick, consistent guidance on routine academic-support issues such as timetable interpretation, course-related concerns, class attendance questions, support-case status checks, and selection of the correct support route. Universities often maintain this guidance across multiple documents, portals, and departmental processes, so students may not know which rules apply or which support channel to use. The result is a fragmented experience, inconsistent advice, and slower triage for support staff.

This capstone project addresses a bounded and realistic student-support need: providing a grounded, traceable support experience using approved academic information, while ensuring that any high-impact or sensitive actions remain under human review. The system is not intended to act as a general-purpose chatbot or to replace human judgment in sensitive cases.

## 3. Target Users
Primary users:
- Undergraduate or postgraduate university students seeking guidance on academic-support questions
- Students who need to initiate a simple support case or check a simulated status

Secondary users:
- Academic support staff
- Student support administrators
- Course coordinators or department representatives who may review routine case routing

## 4. Current Pain Point
Students currently face several common problems:
- information is distributed across multiple documents and systems
- they may not know which official source is authoritative
- they may not know whether a concern is a routine support request or requires escalation
- support teams often receive repeated or partially formed requests
- cases may be routed inconsistently if no clear workflow exists

The project focuses on a narrow, bounded improvement: supporting students with common academic-related issues and giving them a clearly defined path to request help and track case status without allowing the system to make high-impact decisions.

## 5. Proposed Solution
The project will create a bounded AI-native student-support case agent that can:
- understand a student’s request in natural language
- retrieve or explain approved academic guidance from curated knowledge sources
- check simulated case-status or timetable information when available
- create a structured support case or route a student to the appropriate support queue
- maintain an active case state during the workflow
- require human approval for escalation or any sensitive decision

The solution is intentionally limited to a controlled academic-support domain. It does not attempt to replace official university policy, human discretion, or advisory roles at the institution.

## 6. Primary End-to-End Workflow
The primary workflow for the prototype is as follows:

1. The student opens the application and submits an academic-support question or request.
2. The system validates the input and determines whether a support case is needed.
3. The AI interprets the student’s question and retrieves relevant approved guidance from curated documents.
4. The system generates a grounded explanation or next-step advice based only on approved sources.
5. If the request requires case handling, the system checks simulated case-status or timetable data if the student provides the required identifiers.
6. The deterministic application validates required fields and creates or updates a structured support ticket record.
7. The case is routed to the appropriate support queue according to a predefined rule set.
8. Human staff review is required before escalation to a higher-risk or high-impact decision path.

This workflow is designed to be traceable, manageable, and easy to demonstrate within the 8-week duration of the capstone.

## 7. Why AI Is Appropriate
AI is appropriate in this project because it adds value in places where language understanding, retrieval, summarization, workflow assistance, and natural-language interpretation improve usability and reduce manual effort. The system can interpret student questions, identify the relevant policies or procedures, and help structure a response or case request using approved knowledge.

However, AI is used within strict boundaries. It does not decide policy outcomes or manage sensitive decisions. Deterministic logic remains responsible for business rules and validation. This division is key to a safe and realistic capstone implementation.

## 8. What AI Will NOT Do
The AI will not:
- decide grades, admission outcomes, disciplinary consequences, or fee-related actions
- make legal, medical, or highly sensitive policy decisions
- override official university approvals or human authority
- act without approved knowledge sources
- create unsupported recommendations when required information is absent

These restrictions are part of the project’s core design and risk management approach.

## 9. Functional Scope
The initial scope of the project includes:
- student question handling for common academic-support topics
- retrieval from approved, curated knowledge documents
- response generation grounded in approved sources
- simulated timetable or support-case status checking
- case creation and routing for routine academic issues
- session/case-state tracking in a controlled environment
- auditability through logs and evidence documents

## 10. Out of Scope
The project is intentionally not designed to cover:
- live production university systems integration
- confidential institutional records or student personal data
- fee or billing workflows
- grading or academic sanctions decisions
- legal, medical, or disciplinary actions
- uncontrolled general-purpose chatbot behavior

## 11. Assumptions
- University-approved guidance can be represented through synthetic or authorized project materials.
- The project team will create or curate fictionalized academic support documents and examples.
- The workflow can be demonstrated using simulated case data and example records.
- The case agent will operate within a bounded domain and not require full institutional deployment.

## 12. Constraints
- The project must remain feasible within 8 weeks.
- The scope must remain bounded and demonstrable.
- We will not use real student information, confidential data, or production systems.
- Any high-impact actions require human approval.
- Documentation and evidence must be traceable and academically honest.

## 13. Success Criteria
The project will be considered successful for Week 1 if it can clearly show:
- one feasible use case is defined and justified
- a realistic end-to-end workflow is documented
- a project charter is complete and professional
- user stories with measurable acceptance criteria are created
- AI boundaries are explicitly documented
- architecture assumptions are captured
- repository structure and evidence plan are established
- the project remains bounded and feasible for the capstone timeline

## 14. Risks
Key risks include:
- scope creep beyond a realistic academic support workflow
- unclear distinction between AI assistance and human authority
- over-claiming what the prototype can do
- using unapproved data or undocumented assumptions
- incomplete traceability and weak project documentation

These risks will be mitigated by maintaining a bounded problem statement, explicit AI boundaries, and academically honest evidence handling.

## 15. Initial Technical Direction
The initial technical direction is intentionally modest and realistic:
- a lightweight user interface or console for demonstrations
- backend logic or service layer for structured handling
- AI reasoning and retrieval layers for approved knowledge access
- deterministic features for validation, rules, and routing
- a simple case-status and case-state workflow for demonstration
- documentation and evidence collection for traceability

This is not a full-scale enterprise deployment. It is a focused, teachable prototype aligned with the project’s academic constraints.

## 16. Team/Ownership Considerations
This project is a team-based capstone. Ownership should be clearly assigned for:
- requirement management and scope control
- documentation and architecture decisions
- AI prompt and knowledge-source curation
- deterministic workflow and validation logic
- evidence and reporting

A clear ownership model is required so that no single area becomes ambiguous and so the project can remain traceable throughout the 8-week schedule.

## Summary
This project is intentionally scoped to a realistic, bounded student-support case workflow. AI contributes where it adds value, but deterministic software and human staff remain responsible for validation, authorization, and high-impact decisions. The result is a professional capstone demonstrator that is explainable, safe, and academically appropriate for the course.
