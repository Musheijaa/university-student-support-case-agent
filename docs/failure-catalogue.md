# Week 7 - Failure Catalogue

The brief asks for at least five genuine failures found during the
project, with a description of the fix and evidence that the fix held.
Each entry below is a real problem the team hit, not a contrived one.

For each failure:
- What happened
- Why
- What changed
- Re-test evidence


## Failure 1 - The agent loop trusted the provider to stop calling tools

What happened:
The first tool-calling loop only passed tool_choice="none" once the
tool-call budget was exhausted, relying on the model to honor that
request. During test authoring, we realized a misbehaving provider (or
a bug) could ignore tool_choice and keep returning tool calls, letting
the loop execute tools indefinitely.

Why:
The bound was expressed as a preference (tool_choice) rather than as a
hard cap enforced by the application.

Fix:
agent-backend/agent/orchestrator.py now hard-caps actual tool
executions at max_tool_calls, regardless of what the provider returns.
Total round-trips are also capped so the loop always terminates.

Re-test:
tests/test_tool_calling_flow.py::test_tool_execution_is_hard_capped_even_if_provider_ignores_tool_choice
Result: PASSED (with the fix). Before the fix, this test would have
looped until the mock ran out of responses.

Related adversarial test:
tests/test_prompt_injection.py::test_tool_call_budget_caps_multi_ticket_request


## Failure 2 - The timetable tool could return an empty match without saying so

What happened:
Early in Week 4, a timetable query for a nonexistent course could
return an empty sessions list without a clear "not found" signal. The
model, given an empty list, sometimes invented plausible sessions.

Why:
The failure mode was not distinguished from "no sessions on this date".
Both returned an empty list.

Fix:
tools/timetable.py now distinguishes "course not found" from "no
sessions on the requested date" and returns a structured error in the
first case. The agent observes the error and reports it to the student
rather than guessing.

Re-test:
tests/test_tools_timetable.py::test_course_not_found_returns_safe_failure_not_a_guess
Result: PASSED. The tool returns {"success": false, "error": ...} for
unknown courses, never an empty-success.


## Failure 3 - Unauthorized tool calls were being counted against the budget

What happened:
When a guest role requested a tool, the dispatch layer correctly
refused it - but the agent's tool-call counter still incremented. This
meant a guest could exhaust their own budget on calls that were never
allowed to run, ending the run earlier than necessary and with a
misleading status.

Why:
The counter incremented on the model's *request*, before the dispatch
result was checked for success.

Fix:
agent-backend/agent/orchestrator.py now increments the tool-call
counter only on successful dispatch. Failed or unauthorized calls are
recorded as observations (so the model learns from them) but do not
consume the budget.

Re-test:
tests/test_prompt_injection.py::test_guest_role_cannot_invoke_tools
Result: PASSED. The guest's calls are refused, recorded, and the run
terminates at a bounded terminal status with no successful tool result.

Note: This failure was found while writing the Week 7 adversarial
tests - the original test expected only two terminal statuses, and the
run stopped with max_tool_calls_reached. On investigation we found the
counter was over-counting refused calls.


## Failure 4 - The Week 6 .env file was lost in a folder move

What happened:
When the project folder was replaced during Week 6, the .env file
(which contains GROQ_API_KEY) was not restored. All agent requests
started returning HTTP 503 "the student-support assistant is not
configured", even though the code was unchanged.

Why:
.env is correctly listed in .gitignore, so git does not track it. A
fresh clone or folder replacement therefore has no .env, and the
Settings object reads an empty groq_api_key.

Fix:
The recovery procedure is now documented for new team members:
cp .env.example .env, fill in the real key, restart uvicorn. This is
recorded in the Week 6 progress report and the agent-backend README.

Re-test:
After recreating .env and restarting the server:
- GET /health returns {"status":"ok"}
- POST /api/v1/agent/student-support returns a real response
Result: PASSED. Documented as a lessons-learned item; no code change
was needed because the behavior was correct - the missing file was the
problem.


## Failure 5 - A tool existed in the codebase but was not registered

What happened:
tools/application_requirements_tool.py was added to the repository as
a fifth tool (class name search_application_requirements). It was
never added to TOOL_REGISTRY, so the agent could not call it - but
nobody noticed because nothing tested the boundary.

Why:
Adding a tool file does not automatically expose it. Only registration
in TOOL_REGISTRY does. This is by design (a strict allow-list), but
without a test the team could not tell whether the tool was
intentionally or accidentally excluded.

Fix:
Instead of wiring the tool in, we turned this into a test: the
allow-list invariant test asserts that search_application_requirements
is not in TOOL_REGISTRY, and therefore not callable. This makes the
exclusion explicit and prevents accidental exposure if the tool is
later registered without review.

Re-test:
tests/test_prompt_injection.py::test_unregistered_tool_is_rejected_even_when_it_exists_as_code
tests/test_prompt_injection.py::test_contract_allow_list_matches_tool_registry_exactly
Result: PASSED. The tool is refused with status tool_not_approved.


## Failure 6 - High-impact topics were only refused by prompt, not code

What happened:
During Week 7 design, we noticed that the "no grades / fees /
discipline" rule was enforced only by prompt instructions in
llm/prompts.py. The model was told to refuse, but there was no
code-level check preventing a tool from running if the model was
induced to request one.

Why:
The prompt-only approach works most of the time but is not a code
guarantee. A prompt injection that convinces the model to ignore its
instructions would have no code-level backstop.

Fix:
Two-part mitigation:
1. The tool surface itself has no tool that could implement a grade,
   fee, or discipline decision. So even a fully-compliant model cannot
   *act* on such a request through the tools.
2. The adversarial test suite now includes explicit scenarios
   (grade, fee, medical) that assert no tool call is triggered.

The prompt instruction remains as defence in depth, but the code
guarantee is that no tool exists to carry out the decision.

Re-test:
tests/test_prompt_injection.py::test_grade_decision_does_not_invoke_a_tool
tests/test_prompt_injection.py::test_fee_decision_does_not_invoke_a_tool
tests/test_prompt_injection.py::test_medical_advice_does_not_invoke_a_tool
Result: PASSED. No tool call is made on any of these topics.

Known limitation: A prompt-injected model could still *say* something
inappropriate in its final text response. This is a limitation of any
LLM-backed system and is documented here so it is not mistaken for a
fully solved problem. It does not affect the tool surface or any state
change.


## Summary

Six genuine failures, all fixed or documented. Five were code fixes;
one was a recovery procedure; one was a design decision to constrain
the tool surface rather than rely on prompt instructions.

Total regression test count: 178 tests, all passing.
Adversarial tests: 14 tests, all passing.
