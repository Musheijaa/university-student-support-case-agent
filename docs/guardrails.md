# Week 7 - System Guardrails and Security Controls

This document is the guardrail implementation evidence required by the
Week 7 brief: for every safety boundary, it says what the guardrail is,
where it lives in code, and which test proves it holds.

Guardrails are enforced in code, not by asking the model to behave.
Prompt instructions exist (see llm/prompts.py), but every safety
boundary below has a code-level enforcement point that does not depend
on the model complying.


## 1. Input validation (Pydantic)

What: every request body is validated before any business logic runs.

Where: agent-backend/schemas.py, class StudentSupportRequest.

Rules:
- message is a required string
- minimum length 1
- maximum length 2000 (MAX_MESSAGE_LENGTH)
- the message is stripped; whitespace-only input is rejected
- non-string types are rejected by Pydantic

Tests:
- tests/test_main.py::test_missing_message_field
- tests/test_main.py::test_empty_message
- tests/test_main.py::test_whitespace_only_message
- tests/test_main.py::test_non_string_message_type_rejected
- tests/test_main.py::test_excessively_long_message
- tests/test_main.py::test_malformed_request_body


## 2. Tool allow-list

What: the model can only ever request tools that are explicitly
registered in the tool registry. A tool that exists as code but is not
registered cannot be called.

Where:
- agent-backend/tools/registry.py, dict TOOL_REGISTRY
- agent-backend/agent/contract.py, build_contract() sets
  approved_tools = frozenset(TOOL_REGISTRY)

The agent's allow-list is derived from the registry itself, so a tool
cannot be added to the allow-list without also being registered with a
schema, an authorization rule, and an executor. There is no separate
list that can drift.

Currently registered tools:
- check_timetable (roles: student, staff)
- create_support_ticket (roles: student, staff)

Deliberately NOT registered and therefore not callable by the model:
- approve_ticket
- reject_ticket
- search_application_requirements (exists as code but is not wired in)

Tests:
- tests/test_tool_registry.py::test_unregistered_tool_name_is_rejected
- tests/test_agent_orchestrator.py::test_contract_approved_tools_are_exactly_the_week4_allow_list
- tests/test_agent_orchestrator.py::test_unapproved_tool_is_never_executed
- tests/test_prompt_injection.py::test_unregistered_tool_is_rejected_even_when_it_exists_as_code
- tests/test_prompt_injection.py::test_contract_allow_list_matches_tool_registry_exactly


## 3. Role-based authorization (X-User-Role)

What: the actor's role is read from the X-User-Role header, never from
the message body. Every tool call and every staff-only endpoint checks
the role before acting.

Where:
- agent-backend/auth.py, get_actor() reads the header
- agent-backend/tools/registry.py, dispatch_tool_call() checks the
  caller's role against the tool's allowed_roles before executing
- agent-backend/main.py, approve/reject endpoints check
  actor.role == "staff" and return 403 otherwise

Roles: student (default), staff, guest. An unknown or missing role is
treated as the least-privileged role, never the most privileged.

Tests:
- tests/test_tool_registry.py::test_guest_is_unauthorized_for_check_timetable
- tests/test_tool_registry.py::test_guest_is_unauthorized_for_create_support_ticket
- tests/test_tool_failure_handling.py::TestUnauthorizedRequests (10 tests)
- tests/test_ticket_approval_api.py::test_student_cannot_approve_a_ticket
- tests/test_ticket_approval_api.py::test_missing_role_header_defaults_to_student_and_is_forbidden
- tests/test_prompt_injection.py::test_role_comes_from_header_not_message_body
- tests/test_prompt_injection.py::test_guest_role_cannot_invoke_tools


## 4. Loop budgets (AGENT_MAX_ITERATIONS, MAX_TOOL_CALLS)

What: the agent loop is bounded in two independent ways:
- maximum model decisions per run (agent_max_iterations)
- maximum tool executions per run (max_tool_calls)

Both are read from settings and enforced in the orchestrator loop
guard. Even if the model keeps asking for the same tool call forever,
the loop terminates.

Where:
- agent-backend/agent/contract.py, build_contract() reads both limits
- agent-backend/agent/orchestrator.py, while-loop condition and
  tool-call guard

Default values: max_tool_calls = 3, agent_max_iterations = 4.

Tests:
- tests/test_agent_orchestrator.py::test_tool_budget_exhausted_stops_safely
- tests/test_agent_orchestrator.py::test_iteration_budget_exhausted_stops_safely
- tests/test_tool_calling_flow.py::test_tool_execution_is_hard_capped_even_if_provider_ignores_tool_choice
- tests/test_prompt_injection.py::test_tool_call_budget_caps_multi_ticket_request
- tests/test_prompt_injection.py::test_iteration_budget_stops_a_loop_that_keeps_requesting_tools


## 5. Human-in-the-loop approval for ticket submission

What: the agent can create a ticket, but only as a PENDING_APPROVAL
draft. Moving a ticket to SUBMITTED or REJECTED requires a separate
staff-authenticated HTTP call that the model cannot reach.

Where:
- agent-backend/tools/tickets.py, create_support_ticket inserts with
  status PENDING_APPROVAL; approve_ticket / reject_ticket are separate
  functions not registered as tools
- agent-backend/main.py, POST /api/v1/support-tickets/{id}/approve and
  /reject require actor.role == "staff" and return 403 otherwise

The agent's authority ends at a draft. There is no code path by which
the model can submit or approve its own ticket.

Tests:
- tests/test_ticket_approval_api.py::test_staff_can_approve_a_pending_ticket
- tests/test_ticket_approval_api.py::test_student_cannot_approve_a_ticket
- tests/test_ticket_approval_api.py::test_staff_can_reject_a_pending_ticket
- tests/test_ticket_approval_api.py::test_approving_an_already_approved_ticket_fails
- tests/test_tools_tickets.py::test_create_ticket_returns_draft_pending_approval
- tests/test_agent_orchestrator.py::test_ticket_draft_stops_for_human_approval
- tests/test_prompt_injection.py::test_student_cannot_approve_ticket_via_message


## 6. Prompt-injection and jailbreak resistance

What: the code-level boundaries above do not depend on prompt
instructions, so attempts to talk the model out of its bounds cannot
succeed. This is verified by an adversarial test suite.

Adversarial categories covered by tests/test_prompt_injection.py:
- direct injection: "approve my ticket", "submit it", "ignore all
  previous instructions"
- instruction override: "you are now staff"
- system prompt disclosure attempt
- unregistered tool request
- budget exhaustion attacks (many tools, repeated tool)
- role impersonation via the message body
- high-impact topics that must not trigger tools (grades, fees, medical)
- indirect injection via a tool result (the ticket subject text)

Tests: tests/test_prompt_injection.py (14 tests, all passing)


## 7. Error containment

What: tool execution errors and unexpected tool responses are converted
into structured error dicts that the loop can handle, never raised as
exceptions that crash the request.

Where:
- agent-backend/tools/registry.py, dispatch_tool_call wraps execution
  and returns {"success": false, "error": ...} for all failures
- agent-backend/agent/orchestrator.py, wraps the LLM call and the tool
  dispatch in try/except and ends the run with a terminal status

Tests:
- tests/test_tool_failure_handling.py::TestUnavailableServices (8 tests)
- tests/test_tool_failure_handling.py::TestUnexpectedToolResponses (5 tests)
- tests/test_tool_registry.py::test_timetable_service_unavailable_is_caught_safely
- tests/test_tool_registry.py::test_unexpected_tool_response_is_caught_safely


## Summary

Total tests: 178 passed
Adversarial tests: 14 passed (tests/test_prompt_injection.py)
Raw evidence: evidence/week7/adversarial-tests.txt,
              evidence/week7/full-suite.txt

Every guardrail above is code-enforced and test-verified. The model
cannot exceed the agent's bounds, no matter what a user asks it to do.
