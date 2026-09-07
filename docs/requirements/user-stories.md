# User Stories and Acceptance Criteria

## Story 1: Student asks a course-support question
- ID: US-01
- User story: As a student, I want to ask a question about academic support using natural language, so that I can get guidance quickly without searching through many documents.
- Priority: High
- Acceptance criteria:
  1. The user can enter a question through the interface.
  2. The system accepts a natural-language request about a common academic-support topic.
  3. The system returns an answer based only on approved source material.
  4. If the question is outside scope, the system indicates that it cannot answer and provides a safe next step.
- Notes/dependencies: Requires approved knowledge base and a clear retrieval boundary.

## Story 2: System retrieves approved guidance
- ID: US-02
- User story: As a student, I want the system to find relevant approved guidance, so that I can get trustworthy answers.
- Priority: High
- Acceptance criteria:
  1. The system identifies the relevant document or policy fragment for the user’s question.
  2. The system shows or uses the relevant approved source as the basis for the answer.
  3. The system does not invent information or rely on unapproved content.
- Notes/dependencies: Curated knowledge sources must be available and clearly labeled.

## Story 3: Student checks timetable information
- ID: US-03
- User story: As a student, I want to check a simulated timetable or schedule detail, so that I can understand my academic planning and support needs.
- Priority: Medium
- Acceptance criteria:
  1. The user provides a valid student ID or simulated schedule identifier.
  2. The system returns the relevant timetable information from simulated data.
  3. The system clearly labels the data as simulated and not production data.
- Notes/dependencies: Requires a mock or test dataset for timetable information.

## Story 4: Student checks case status
- ID: US-04
- User story: As a student, I want to check the status of my support case, so that I know what stage it is in and what happens next.
- Priority: High
- Acceptance criteria:
  1. The user provides a valid case identifier or matching student data.
  2. The system returns only the status information that is allowed for that user or simulated scenario.
  3. The system prohibits unauthorized access to other cases.
- Notes/dependencies: Requires deterministic authorization and case-state logic.

## Story 5: Student creates a support request
- ID: US-05
- User story: As a student, I want to create a support request for a routine academic issue, so that my concern is recorded and routed appropriately.
- Priority: High
- Acceptance criteria:
  1. The user enters all required fields such as issue category, description, and contact information.
  2. The system validates the fields before creating the case.
  3. A new support case record is created in the simulated workflow.
  4. The system assigns a case ID and status.
- Notes/dependencies: Requires deterministic validation and case creation tooling.

## Story 6: Agent routes a case correctly
- ID: US-06
- User story: As a support administrator, I want the system to route a routine support case according to predefined rules, so that the issue reaches the correct queue.
- Priority: High
- Acceptance criteria:
  1. The system applies a routing rule based on issue type and category.
  2. The route matches the deterministic business logic in the project specification.
  3. Cases outside the supported domain are not auto-routed without human approval.
- Notes/dependencies: Requires explicit routing logic and administrative review for exceptions.

## Story 7: System maintains active case state
- ID: US-07
- User story: As a support officer, I want the system to maintain the active case state through the workflow, so that actions and decisions remain traceable.
- Priority: High
- Acceptance criteria:
  1. The system stores the current case state, status, and summary for each active case.
  2. The state updates as actions occur in the workflow.
  3. The case state is available for review in a session or evidence trail.
- Notes/dependencies: Needs a simple state model or session record.

## Story 8: Human approval is required for escalation
- ID: US-08
- User story: As a support staff member, I want the system to require human approval for any escalation outside the bounded support scope, so that high-impact decisions remain controlled.
- Priority: Critical
- Acceptance criteria:
  1. Escalation requests outside the approved boundary are blocked by default.
  2. The system displays a clear message that human review is required.
  3. No automatic high-impact decision is taken without approval.
- Notes/dependencies: Must be enforced by deterministic software and documented in the AI boundary matrix.

## Story 9: System refuses unsupported or high-impact requests
- ID: US-09
- User story: As a student, I want the system to explain the limits of what it can help with, so that I understand when to contact a human support officer.
- Priority: High
- Acceptance criteria:
  1. If a request involves fee, grade, disciplinary, medical, or legal matters, the system declines or redirects appropriately.
  2. The system provides a safe and clear next-step message.
  3. The system does not attempt to make a decision in those domains.
- Notes/dependencies: Requires explicit risk-aware workflow and policy boundaries.

## Story 10: Documentation and evidence are traceable
- ID: US-10
- User story: As a project team member, I want project evidence to be captured in a traceable way, so that the Week 1 process is defensible and reviewable.
- Priority: Medium
- Acceptance criteria:
  1. The repository contains requirements, architecture, and evidence artifacts.
  2. AI engineering logs record key tool-assisted work and human review.
  3. The documentation clearly marks any placeholders or unimplemented items.
- Notes/dependencies: Must be maintained throughout the capstone project.

## Story 11: Project demonstrates a feasible bounded use case
- ID: US-11
- User story: As a capstone team member, I want a single workable student-support use case, so that the project remains realistic and implementable within 8 weeks.
- Priority: High
- Acceptance criteria:
  1. The project defines one primary workflow.
  2. The workflow integrates student query handling, approved guidance, and case state management.
  3. The project scope is clearly bounded and does not extend to high-impact decisions.
- Notes/dependencies: This is a planning and scoping story that informs the rest of the project.

## Story 12: Week 1 deliverables are complete
- ID: US-12
- User story: As a course instructor or reviewer, I want the Week 1 deliverables to be available in the repository, so that I can assess the project’s problem framing and plan quality.
- Priority: High
- Acceptance criteria:
  1. README, Project Charter, user stories, AI boundary matrix, architecture docs, and weekly progress report are present.
  2. The documentation follows the assignment structure and includes realistic placeholders where needed.
  3. No fabricated implementation claims are made.
- Notes/dependencies: Must align with the official assignment requirements.
