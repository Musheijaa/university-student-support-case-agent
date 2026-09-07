# Week 1 Progress Report

## 1. Group and project name
- Group: BSE4104 AI-Native & Agentic Engineering Team
- Project: University Student-Support Case Agent
- Course: BSE4104 Emerging Trends in Software Engineering
- Team members:
  - OkemaPaulMark — paulokema342@gmail.com
  - KizitoRyan — ryankizito08@gmail.com
  - Benita Akakikunda — benitaakakikunda@gmail.com
  - Seand1975
  - Mwesigwa Duncan — mwesigwaduncan@gmail.com

## 2. Week ending
- 2026-09-07

## 3. Work completed against weekly objectives
During Week 1, the project team focused on problem framing, use-case selection, and requirement definition for the capstone. The work completed included:

- selection of one feasible and bounded use case: a student-support case agent for common academic-support requests using approved university/course documents
- definition of the primary end-to-end workflow for student guidance, case-status checks, and support-ticket creation within a controlled domain
- preparation of a professional project charter documenting the problem, target users, pain points, AI value, scope, assumptions, constraints, risks, and success criteria
- development of 8–12 user stories with specific, testable acceptance criteria
- creation of an AI Boundary Matrix to make the AI/deterministic/human boundaries explicit
- design of an initial architecture and context view for the planned system
- setup of the repository structure and project documentation skeleton
- preparation of evidence placeholders and documentation requirements for GitHub and ClickUp tracking

This work establishes the Week 1 foundation and ensures the project remains realistic, bounded, and feasible for the remaining 7 weeks of the course.

## 4. Key engineering decisions and why
The main engineering decision for Week 1 was to keep the project scoped to one bounded academic-support case workflow rather than a general-purpose chatbot. This is appropriate because it allows the project team to demonstrate AI value while preserving deterministic control over validation, authorization, routing, and escalation.

Another key decision was the explicit separation of AI responsibilities from deterministic software responsibilities. This is important because the use case is operationally meaningful but should avoid high-impact decisions such as admissions, fees, grades, disciplinary action, or legal/medical concerns.

The project also chose to keep the architecture deliberately simple and academic, with a clear distinction between:
- student interaction
- AI interpretation and retrieval support
- approved knowledge sources
- deterministic validation and case logic
- human review and escalation boundaries

These decisions keep the solution traceable, defensible, and aligned with the assignment requirements.

## 5. Failures/challenges and current response
The main challenge for Week 1 was maintaining a realistic and bounded scope without allowing the project to become a generic assistant. This was addressed by clearly narrowing the use case to routine academic-support questions, simulated case-status checks, and controlled ticket creation.

A second challenge was making the AI boundary explicit so that the project does not overclaim what the system can do. The team responded by documenting the AI boundary matrix and by ensuring that all high-impact decisions remain outside the system’s allowed scope.

Another issue was the current absence of a live ClickUp account and actual GitHub remote URL. Because these are external and user-specific, the project documents contain clearly marked placeholders rather than fabricated links or claims.

## 6. GitHub evidence
The repository has been initialized locally and the Week 1 documents have been created in the project structure. This serves as the current GitHub evidence baseline for the assignment.

Evidence items created in the repository:
- `README.md`
- `docs/requirements/project-charter.md`
- `docs/requirements/user-stories.md`
- `docs/requirements/ai-boundary-matrix.md`
- `docs/architecture/initial-architecture.md`
- `docs/weekly-reports/week-1-progress-report.md`
- `docs/clickup-week1-task-plan.md`
- `docs/ai-engineering-log.md`

GitHub remote and repository URL: [ACTUAL GITHUB URL]

## 7. ClickUp evidence placeholders
The following ClickUp items should be created manually by the project team in the assigned workspace. They are intentionally documented as placeholders because direct ClickUp access is not available in this environment.

- [CLICKUP URL]
- [CLICKUP TASK 1: Select and define primary use case]
- [CLICKUP TASK 2: Develop Project Charter]
- [CLICKUP TASK 3: Create User Stories and Acceptance Criteria]
- [CLICKUP TASK 4: Create AI Boundary Matrix]
- [CLICKUP TASK 5: Design Initial Architecture]
- [CLICKUP TASK 6: Set up GitHub Repository]
- [CLICKUP TASK 7: Set up Project Documentation]
- [CLICKUP TASK 8: Prepare Week 1 Progress Report]

## 8. Individual contribution summary
- OkemaPaulMark: Requirements framing, project charter drafting, and initial scope definition.
- KizitoRyan: User story and acceptance criteria development.
- Benita Akakikunda: AI boundary definition and evidence planning.
- Seand1975: Architecture and repository structure setup.
- Mwesigwa Duncan: Progress documentation and review.

[ACTUAL CONTRIBUTION]

## 9. Plan for Week 2
For Week 2, the project should focus on the first implementation milestone and a more concrete technical foundation. The likely next steps are:

- finalize the project use-case specification and workflow details
- decide on the selected technology stack and initial implementation structure
- create the first minimal prototype or mock workflow for student queries and case creation
- start the knowledge-base and retrieval design using approved project materials
- define the initial validation and routing logic for support cases
- begin recording evidence, screenshots, and trace logs for the project record
- prepare the next weekly report once implementation progress is visible

This will transition the project from planning and requirements documentation into the first demonstrable technical iteration.
