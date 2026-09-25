# Week 4 Tool Catalogue & Specification

**UniSupport AI: University Student Support Case Agent**
*Assignment Week 4: Tools and Function Calling*

---

## Overview

Per the BSE4104 Capstone Project Brief (Week 4), tools allow the AI-native application to perform explicit, deterministic, safe software capabilities beyond raw text generation.

All tools in `agent-backend/tools/` implement a strict engineering contract comprising five required components:
1. **Purpose**: Explicit rationale and functional intent.
2. **Input Schema**: Strongly-typed Pydantic model with validation rules and field constraints.
3. **Output Schema**: Strongly-typed return contract with status metadata and outcome details.
4. **Authorization**: Explicit token/role permission checks evaluated prior to execution.
5. **Failure Behaviour**: Graceful containment for validation errors, unauthorized access, missing cases, and system errors without application crashes.

---

## Registered Tool Specifications

### 1. `create_support_ticket`

- **Purpose**: Creates a formal student support ticket and routes it to the designated Makerere University department (e.g. Academic Registrar, DICTS IT Helpdesk, Bursar/Financial Aid, Hall Allocation). Performs a low-risk side-effect record creation.
- **Implementation File**: [`agent-backend/tools/ticket_tool.py`](file:///c:/Users/sean/Desktop/UniveristyAgentic/university-student-support-case-agent/agent-backend/tools/ticket_tool.py)
- **Input Schema (`CreateTicketInput`)**:
  - `student_id` (`str`): Student registration number or student ID (min 3, max 20 chars).
  - `category` (`TicketCategory` Enum): Department category (`Academic Registrar`, `Financial Aid & Bursary`, `Hall Allocation & Accommodation`, `Library Services`, `DICTS / IT Support`, `General Student Affairs`).
  - `subject` (`str`): Brief summary title of the issue (min 5, max 100 chars).
  - `description` (`str`): Detailed description of student issue (min 10, max 1000 chars).
  - `priority` (`TicketPriority` Enum): `LOW`, `MEDIUM`, `HIGH`, `URGENT` (default: `MEDIUM`).
  - `auth_token` (`str`): Student credentials/token.
- **Output Schema (`CreateTicketOutput`)**:
  - `success` (`bool`): Operational success flag.
  - `ticket_id` (`str | None`): Generated unique ticket ID (e.g. `TICK-2026-8412`).
  - `status` (`str`): Status code (`CREATED`, `UNAUTHORIZED`, `INVALID_INPUT`, `SERVICE_ERROR`).
  - `assigned_department` (`str | None`): Department assigned to handle ticket.
  - `created_at` (`str | None`): ISO 8601 timestamp.
  - `estimated_response_days` (`int | None`): Expected SLA response days.
  - `message` (`str`): Human-readable summary message.
  - `error` (`str | None`): Error code or detail string if failed.
- **Authorization**:
  - Validates `auth_token`. Tokens matching `unauthorized`, `expired`, `invalid`, or `forbidden` are rejected.
  - Unauthorized calls return `status="UNAUTHORIZED"`, `success=False`, and `error="AUTH_DENIED"`.
- **Failure Behaviour**:
  - Blank/invalid input fields fail Pydantic validation cleanly (`status="INVALID_INPUT"`, `error="VALIDATION_ERROR"`).
  - System or unexpected execution exceptions return `status="SERVICE_ERROR"`.

---

### 2. `get_case_status`

- **Purpose**: Retrieves live status, assigned department officer, progress audit notes, and last update timestamp for an existing student case.
- **Implementation File**: [`agent-backend/tools/case_tool.py`](file:///c:/Users/sean/Desktop/UniveristyAgentic/university-student-support-case-agent/agent-backend/tools/case_tool.py)
- **Input Schema (`GetCaseStatusInput`)**:
  - `case_id` (`str`): Case identifier (e.g., `TICK-2026-1001`).
  - `student_id` (`str`): Student ID requesting status lookup.
  - `auth_token` (`str`): Identity verification token.
- **Output Schema (`GetCaseStatusOutput`)**:
  - `success` (`bool`): Status lookup success.
  - `case_id` (`str | None`): Case ID.
  - `student_id` (`str | None`): Student ID on record.
  - `category` (`str | None`): Department category.
  - `subject` (`str | None`): Subject summary.
  - `status` (`str`): Current status (`UNDER_REVIEW`, `RESOLVED`, `NOT_FOUND`, `UNAUTHORIZED`, etc.).
  - `assigned_officer` (`str | None`): Officer currently assigned.
  - `created_at` (`str | None`): ISO creation timestamp.
  - `last_updated` (`str | None`): ISO last update timestamp.
  - `notes` (`list[CaseNote]`): Audit and progress notes list.
  - `message` (`str`): Explanation of status outcome.
  - `error` (`str | None`): Error code if query failed.
- **Authorization**:
  - Verifies token validity and validates ownership: only the student who owns the ticket (or a staff token starting with `staff-`) may query case details.
  - Student mismatch returns `status="UNAUTHORIZED"`, `error="AUTH_DENIED: Student ID mismatch"`.
- **Failure Behaviour**:
  - Non-existent case ID returns `status="NOT_FOUND"`, `error="CASE_NOT_FOUND"`.

---

### 3. `check_timetable`

- **Purpose**: Queries lecture, tutorial, lab, and examination timetable schedules for Makerere University courses or enrolled student courses.
- **Implementation File**: [`agent-backend/tools/timetable_tool.py`](file:///c:/Users/sean/Desktop/UniveristyAgentic/university-student-support-case-agent/agent-backend/tools/timetable_tool.py)
- **Input Schema (`CheckTimetableInput`)**:
  - `student_id` (`str`): Student registration number or ID.
  - `course_code` (`str | None`): Optional course code filter (e.g., `BSE4104`, `BIT2101`).
  - `semester` (`str`): Academic semester (default `2026/2027-SEM1`).
  - `auth_token` (`str`): Authorization token.
- **Output Schema (`CheckTimetableOutput`)**:
  - `success` (`bool`): Operational success flag.
  - `student_id` (`str | None`): Student ID.
  - `semester` (`str | None`): Queried semester.
  - `total_found` (`int`): Count of schedule entries found.
  - `entries` (`list[TimetableEntry]`): Array of timetable entries (`course_code`, `course_title`, `entry_type`, `day`, `start_time`, `end_time`, `venue`, `instructor`).
  - `message` (`str`): Summary message.
  - `error` (`str | None`): Error details if failed.
- **Authorization**:
  - Validates `auth_token`. Rejects invalid/expired credentials.
- **Failure Behaviour**:
  - If no published schedule matches the course or student, returns `success=True`, `total_found=0`, `entries=[]` with an informative message rather than failing or throwing an error.

---

### 4. `submit_grade_appeal` (High-Impact Action — Human Approval Required)

- **Purpose**: Submits a formal academic grade appeal/re-marking request to the Makerere University Senate Examinations Committee. As a high-impact academic and financial action (imposing a non-refundable 50,000 UGX fee deposit and irreversible senate review), autonomous execution by the AI agent is prohibited without explicit human approval.
- **Implementation File**: [`agent-backend/tools/appeal_tool.py`](file:///c:/Users/sean/Desktop/UniveristyAgentic/university-student-support-case-agent/agent-backend/tools/appeal_tool.py)
- **Input Schema (`SubmitGradeAppealInput`)**:
  - `student_id` (`str`): Student registration number or student ID.
  - `course_code` (`str`): Course code being appealed (e.g., `BSE4104`).
  - `semester` (`str`): Academic semester (default: `2026/2027-SEM1`).
  - `appeal_type` (`AppealType` Enum): `REMARKING`, `CALCULATION_CHECK`, or `SPECIAL_CIRCUMSTANCES`.
  - `claimed_score` (`float | None`): Expected score if calculation discrepancy is claimed (0 to 100).
  - `justification` (`str`): Detailed grounds for appeal (min 20, max 1000 chars).
  - `confirm_fee_obligation` (`bool`): Explicit student confirmation of the 50,000 UGX deposit (must be `True`).
  - `auth_token` (`str`): Authorization token representing student credentials.
- **Output Schema (`SubmitGradeAppealOutput`)**:
  - `success` (`bool`): True if grade appeal was lodged.
  - `appeal_id` (`str | None`): Unique appeal ID (e.g. `APPL-2026-4410`).
  - `status` (`str`): Status (`LODGED`, `PENDING_APPROVAL`, `UNAUTHORIZED`, `INVALID_INPUT`, `REJECTED`).
  - `course_code` (`str | None`): Course code appealed.
  - `appeal_fee_ugx` (`int | None`): 50,000 UGX deposit fee charged.
  - `assigned_board` (`str | None`): `Makerere Senate Examinations Committee`.
  - `created_at` (`str | None`): ISO 8601 timestamp.
  - `message` (`str`): Human-readable outcome message.
  - `error` (`str | None`): Error details if failed.
- **Authorization**:
  - Validates `auth_token`. Rejects unauthorized or expired tokens.
- **Failure Behaviour**:
  - Unacknowledged fee obligation or short justification (<20 chars) returns `status="INVALID_INPUT"`.
  - Human rejection via the HITL gate returns `status="REJECTED"`, leaving the underlying tool unfired.

---

## Human-in-the-Loop (HITL) Approval State Architecture

Implemented in [`agent-backend/tools/approval.py`](file:///c:/Users/sean/Desktop/UniveristyAgentic/university-student-support-case-agent/agent-backend/tools/approval.py):

```
[Agent proposes Action: submit_grade_appeal]
                     │
                     ▼
        [requires_human_approval?]
             /                \
          No                   Yes
          /                      \
   [Fire Tool]           [Pause Execution]
                                 │
                                 ▼
                     [Create ApprovalRequest]
                     (status = PENDING, APPR-XXXX)
                                 │
                                 ▼
                     [Prompt Human Reviewer]
                                 │
                 ┌───────────────┴───────────────┐
                 ▼                               ▼
       Decision = APPROVE               Decision = REJECT
                 │                               │
                 ▼                               ▼
            [FIRE TOOL]                  [CANCEL EXECUTION]
   (status = APPROVED, run tool)    (status = REJECTED, no tool fired)
```

---

## REST API Endpoints

The tool and approval system is exposed via FastAPI in `agent-backend/main.py`:

1. **`GET /api/v1/tools`**: Returns the Tool Catalogue with full function descriptions and OpenAI/Groq compatible JSON Schemas.
2. **`POST /api/v1/tools/execute`**: Executes any tool by name. If tool requires human approval, execution pauses and returns an approval request ID.
3. **`POST /api/v1/approvals/request`**: Explicitly pauses execution and registers an approval request.
4. **`GET /api/v1/approvals/pending`**: Lists all pending actions waiting for human decision.
5. **`GET /api/v1/approvals/{approval_id}`**: Retrieves approval status, details, and review notes.
6. **`POST /api/v1/approvals/{approval_id}/decide`**: Processes human decision (`APPROVE` or `REJECT`). Fires the target tool only upon approval!

---

## Verification & Test Suite

Automated tests in `agent-backend/tests/` verify:
- ✅ **`tests/test_tools.py`**: Execution, validation, authorization, and fallbacks for standard tools (13 tests).
- ✅ **`tests/test_approval.py`**: Grade appeal validation, execution pause, human approval firing, and rejection blocking (6 tests).
- ✅ **`demo_tools.py`**: Live terminal demo proving pause, prompt, and conditional tool firing.

