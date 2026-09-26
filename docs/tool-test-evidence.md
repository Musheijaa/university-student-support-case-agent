# Tool Failure & Authorization Test Evidence — Week 4

Real evidence for every required failure/authorization scenario, drawn
from an actual test run — not hypothetical. Commands used:

```bash
cd agent-backend && source .venv/bin/activate
python -m pytest tests/test_tool_registry.py tests/test_tools_timetable.py \
  tests/test_tools_tickets.py tests/test_ticket_approval_api.py \
  tests/test_tool_calling_flow.py -v
```

**Result: 46 passed, 0 failed** (run date: 2026-09-26). See
`docs/tool-catalogue.md` for what each failure mode is supposed to do;
this document is the record that it actually does it.

---

## 1. Missing parameters

| Scenario | Test | Result |
|---|---|---|
| `check_timetable` with no `course_code` | `test_tool_registry.py::test_missing_required_argument_is_rejected` | PASS — returns `{"success": false, "error": "Invalid input for 'check_timetable': ..."}`, never guesses a course |
| `check_timetable` with empty `course_code` | `test_tools_timetable.py::test_empty_course_code_is_a_validation_error` | PASS |
| `check_timetable` with malformed `course_code` (e.g. not letters+digits) | `test_tools_timetable.py::test_invalid_course_code_format_is_a_validation_error` | PASS |
| `check_timetable` with invalid `date` | `test_tools_timetable.py::test_invalid_date_is_a_validation_error` | PASS |
| `create_support_ticket` missing `category` | `test_tools_tickets.py::test_missing_category_is_a_validation_error` | PASS |
| `create_support_ticket` missing `subject` | `test_tools_tickets.py::test_missing_subject_is_a_validation_error` | PASS |
| `create_support_ticket` missing `description` | `test_tools_tickets.py::test_missing_description_is_a_validation_error` | PASS |
| `create_support_ticket` invalid `category` (not in the allowed list) | `test_tools_tickets.py::test_invalid_category_is_a_validation_error` | PASS |
| `create_support_ticket` blank/whitespace-only `subject` | `test_tools_tickets.py::test_blank_subject_is_a_validation_error` | PASS |
| End-to-end: model calls `check_timetable` with no arguments at all | `test_tool_calling_flow.py::test_scenario_missing_tool_parameter_is_reported_back_to_the_model` | PASS — the validation error is fed back to the model as the tool result, and the model's final answer reflects it ("I need a course code to look that up.") rather than the request crashing |

## 2. Unauthorized requests

| Scenario | Test | Result |
|---|---|---|
| `guest` role calls `check_timetable` | `test_tool_registry.py::test_guest_is_unauthorized_for_check_timetable` | PASS — `{"success": false, "error": "You are not authorized to use 'check_timetable'."}` |
| `guest` role calls `create_support_ticket` | `test_tool_registry.py::test_guest_is_unauthorized_for_create_support_ticket` | PASS |
| `student` role can call `check_timetable` (authorized case, for contrast) | `test_tool_registry.py::test_student_can_call_check_timetable` | PASS |
| `staff` role can also call `check_timetable` | `test_tool_registry.py::test_staff_can_also_call_check_timetable` | PASS |
| End-to-end: `guest` actor triggers a tool call through the full loop | `test_tool_calling_flow.py::test_scenario_unauthorized_actor_tool_call_fails_safely` | PASS — dispatch returns the unauthorized error, the loop still completes normally |
| `student` (or missing role header) attempts to approve a ticket via the HTTP endpoint | `test_ticket_approval_api.py::test_student_cannot_approve_a_ticket`, `::test_missing_role_header_defaults_to_student_and_is_forbidden` | PASS — real `403 Forbidden` |
| **Also verified live** (not just unit-tested) against a running server in this session: `curl -X POST .../approve` with `X-User-Role: student` and with no header at all both returned `HTTP 403 {"detail":"Only staff may approve a support ticket."}`; `X-User-Role: staff` returned `HTTP 200` and transitioned the ticket. | — | Confirmed |

## 3. Unavailable services

| Scenario | Test | Result |
|---|---|---|
| Timetable data file missing/unreadable | `test_tool_registry.py::test_timetable_service_unavailable_is_caught_safely`, `test_tools_timetable.py::test_service_unavailable_raises_rather_than_fabricating` | PASS — `dispatch_tool_call` returns `{"success": false, "error": "The timetable service is temporarily unavailable. Please try again later."}`; no fabricated schedule |
| Ticket database unavailable (simulated `sqlite3.OperationalError`) | `test_tools_tickets.py::test_service_unavailable_raises_rather_than_fabricating` | PASS |

## 4. Unexpected tool responses

| Scenario | Test | Result |
|---|---|---|
| A tool's executor returns a value that doesn't match its declared output schema | `test_tool_registry.py::test_unexpected_tool_response_is_caught_safely` | PASS — caught by Pydantic output validation, returned as `{"success": false, "error": "The 'check_timetable' tool returned an unexpected response."}`; no raw exception or malformed data ever reaches the model |

## 5. Ticket state-transition rules (human approval)

| Scenario | Test | Result |
|---|---|---|
| Staff approves a `PENDING_APPROVAL` ticket | `test_tools_tickets.py::test_approve_pending_ticket_transitions_to_submitted`, `test_ticket_approval_api.py::test_staff_can_approve_a_pending_ticket` | PASS — `PENDING_APPROVAL` → `SUBMITTED` |
| Staff rejects a `PENDING_APPROVAL` ticket | `test_tools_tickets.py::test_reject_pending_ticket_transitions_to_rejected`, `test_ticket_approval_api.py::test_staff_can_reject_a_pending_ticket` | PASS — `PENDING_APPROVAL` → `REJECTED` |
| Approving an already-`SUBMITTED` ticket | `test_tools_tickets.py::test_approve_already_approved_ticket_fails_safely`, `test_ticket_approval_api.py::test_approving_an_already_approved_ticket_fails` | PASS — rejected with `"... is already SUBMITTED; its state cannot be changed."` |
| Rejecting an already-`REJECTED` ticket | `test_tools_tickets.py::test_reject_already_rejected_ticket_fails_safely` | PASS |
| Approving a ticket ID that doesn't exist | `test_tools_tickets.py::test_approve_nonexistent_ticket_fails_safely`, `test_ticket_approval_api.py::test_approving_a_nonexistent_ticket_fails` | PASS — `"... was not found."` |
| `GET` a nonexistent ticket | `test_ticket_approval_api.py::test_get_nonexistent_ticket_is_404` | PASS — real `404` |

## 6. Bounded tool-calling loop (defense against a misbehaving model/provider)

| Scenario | Test | Result |
|---|---|---|
| Compliant provider stops requesting tools once `tool_choice="none"` is sent | `test_tool_calling_flow.py::test_tool_calls_are_bounded_by_max_tool_calls` | PASS — exactly `MAX_TOOL_CALLS` (3) executions, then a clean final answer |
| **Non-compliant provider keeps requesting tool calls anyway** | `test_tool_calling_flow.py::test_tool_execution_is_hard_capped_even_if_provider_ignores_tool_choice` | PASS — no more than 3 tools ever actually *execute* regardless, and the loop still terminates with a response rather than hanging. This gap was found while writing this test (see `docs/weekly-reports/Week4_Progress_Report.md` §4) and fixed before being counted as passing. |

## 7. Real (non-mocked) working demonstration

Beyond the automated suite, both tools were exercised against the live Groq API and a running server earlier in this session:

- "When is BSE4104 scheduled?" → real `check_timetable` call → correct table of real (synthetic) sessions, verified in both `curl` and an actual browser via the frontend.
- "I cannot access the student portal..." → real `create_support_ticket` call → real `DRAFT-XXX` row created in `agent-backend/data/tickets.db`, model explicitly stated it was pending approval, not submitted.
- Full approve flow verified live: unauthorized (403) → staff approval (200, `SUBMITTED`) → re-approval attempt (rejected, already-`SUBMITTED`).
