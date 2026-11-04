# Week 8 — Failure Catalogue (Updated with v1.0.0 Re-test Results)

**Document version:** 2.0 (Post-Hardening & Release v1.0.0)  
**Target Release Tag:** `v1.0.0` (commit `10b3623`)  
**Verified by:** Quality/Security Lead & AI Engineering Lead  
**Full Regression Test Suite:** 178/178 passed  
**Adversarial Suite:** 14/14 passed  
**34-Scenario Evaluation Benchmark:** 34/34 passed (100%)  

---

## Overview

The capstone project brief requires documenting at least five genuine engineering failures identified during system evolution, the root cause for each, the code-level remediation implemented, and verifiable re-test evidence demonstrating that the fix holds on the final tagged release (`v1.0.0`).

All six failures documented below are authentic defects and architectural boundaries encountered between Week 4 and Week 8. Every defect was remediated with code changes or explicit contract assertions, and all re-tests pass on release `v1.0.0`.

---

## Failure 1 — The agent loop trusted the LLM provider to stop requesting tools

- **What happened:**  
  The initial orchestrator loop passed `tool_choice="none"` once the tool-call budget was reached, relying on the external model provider to honor that parameter. During testing, we found that certain model providers or malformed responses could ignore `tool_choice="none"` and return further tool calls, creating the risk of unbounded tool execution loops.
- **Why it occurred:**  
  The execution boundary was expressed as a model preference (`tool_choice`) rather than as an application-level hard ceiling enforced in deterministic code.
- **Remediation:**  
  `agent-backend/agent/orchestrator.py` now hard-caps actual tool executions at `contract.max_tool_calls` (default: 3) and cognitive iterations at `contract.max_iterations` (default: 4). Even if the model outputs a tool call after the budget is exhausted, the orchestrator suppresses dispatch and stops with `max_tool_calls_reached`.
- **v1.0.0 Re-test Evidence:**  
  - Test: `tests/test_tool_calling_flow.py::test_tool_execution_is_hard_capped_even_if_provider_ignores_tool_choice` -> **PASSED**
  - Test: `tests/test_prompt_injection.py::test_tool_call_budget_caps_multi_ticket_request` -> **PASSED**
  - Benchmark Scenarios: `TF-04` (max iterations capped) and `A-05` -> **PASSED**

---

## Failure 2 — Timetable tool returned empty sessions without distinguishing nonexistent courses

- **What happened:**  
  A timetable query for a nonexistent course code (e.g. `XYZ9999`) returned an empty sessions list `{"sessions": []}` without a distinct "not found" error. When given an empty list, the language model frequently hallucinated plausible course sessions and venues.
- **Why it occurred:**  
  The tool failed to distinguish "course exists but has no sessions on requested date" from "course does not exist in the university registry". Both returned empty arrays.
- **Remediation:**  
  `agent-backend/tools/timetable.py` was refactored to inspect course existence first. Nonexistent courses now return a structured error: `{"success": false, "error": "Course '<code_code>' was not found in the timetable records"}`. The agent observes this failure and explains to the student that the course does not exist, eliminating fabrication.
- **v1.0.0 Re-test Evidence:**  
  - Test: `tests/test_tools_timetable.py::test_course_not_found_returns_safe_failure_not_a_guess` -> **PASSED**
  - Benchmark Scenarios: `I-01` (`XYZ9999`) and `I-03` (`FAKE001`) -> **PASSED** (0 hallucinations, accurate error communication)

---

## Failure 3 — Unauthorized tool calls were improperly counted against the student execution budget

- **What happened:**  
  When an unauthorized user (e.g., role `guest`) requested a tool, the dispatch layer correctly rejected the call, but the orchestrator's `state.tool_call_count` counter was incremented anyway. Consequently, unauthorized requests prematurely depleted the session budget and exited with a misleading `max_tool_calls_reached` status rather than completing with a clean authorization explanation.
- **Why it occurred:**  
  The counter was incremented upon receiving the model's tool-call request prior to validating dispatch authorization.
- **Remediation:**  
  `agent-backend/agent/orchestrator.py` was updated so that `state.tool_call_count` increments strictly upon successful dispatch. Rejected or unauthorized tool calls are captured as observations (so the model understands the denial) without penalizing execution budgets.
- **v1.0.0 Re-test Evidence:**  
  - Test: `tests/test_prompt_injection.py::test_guest_role_cannot_invoke_tools` -> **PASSED**
  - Test: `tests/test_tool_failure_handling.py::TestUnauthorizedRequests::test_unauth_002_guest_cannot_create_ticket_through_dispatch` -> **PASSED**
  - Benchmark Scenarios: `U-01`, `U-02`, and `A-07` -> **PASSED** (guest blocked without budget starvation)

---

## Failure 4 — Missing `.env` file after workspace migration caused HTTP 503 errors

- **What happened:**  
  Following a directory rename and workspace migration in Week 6, the `.env` configuration file was omitted because it is excluded by `.gitignore`. The FastAPI server booted, but all agent invocations returned HTTP 503 ("student-support assistant is not configured").
- **Why it occurred:**  
  Configuration variables (specifically `GROQ_API_KEY`) were missing, and the onboarding process lacked an automated environment validation check.
- **Remediation:**  
  Updated `.env.example` to include all runtime parameters across all development weeks (including Week 6 memory, SQLite databases, and state paths). Added explicit health-check diagnostics and documented the onboarding recovery procedure in `README.md` and `docs/RELEASE_NOTES_v1.0.0.md`.
- **v1.0.0 Re-test Evidence:**  
  - Test: `tests/test_main.py::test_health_endpoint` -> **PASSED** (`{"status": "ok"}`)
  - Test: `tests/test_agent_orchestrator.py::test_agent_endpoint_503_when_groq_not_configured` -> **PASSED** (verifies graceful 503 signaling when key is missing)
  - Live API smoke test: `tests/test_integration_groq.py` -> **PASSED** on v1.0.0

---

## Failure 5 — Unregistered tool existed in codebase without registry binding

- **What happened:**  
  An experimental tool file (`tools/application_requirements_tool.py`, class `search_application_requirements`) was committed to the repository but omitted from `TOOL_REGISTRY`. The agent could not call it, creating ambiguity over whether the tool was intentionally or accidentally excluded.
- **Why it occurred:**  
  Adding tool code did not automatically register the tool in `tools/registry.py`. Without automated boundary tests, dead tool code could drift unnoticed.
- **Remediation:**  
  Rather than blindly exposing unverified code, we established an invariant test: the contract allow-list is derived via `frozenset(TOOL_REGISTRY)`. Tests assert that `search_application_requirements` is not in `TOOL_REGISTRY` and cannot be dispatched, formalizing strict allow-listing.
- **v1.0.0 Re-test Evidence:**  
  - Test: `tests/test_prompt_injection.py::test_unregistered_tool_is_rejected_even_when_it_exists_as_code` -> **PASSED**
  - Test: `tests/test_prompt_injection.py::test_contract_allow_list_matches_tool_registry_exactly` -> **PASSED**
  - Benchmark Scenario: `A-02` (unregistered tool call rejected with `tool_not_approved`) -> **PASSED**

---

## Failure 6 — High-impact decision boundaries defended solely by prompt instructions

- **What happened:**  
  The requirement that the assistant must never decide grades, fee waivers, admissions, or disciplinary actions was initially enforced only through prompt guidelines in `llm/prompts.py`. During adversarial testing, we recognized that prompt guidelines alone cannot guarantee defense against sophisticated jailbreaks or multi-shot prompt injections.
- **Why it occurred:**  
  Relying solely on LLM instruction-following provides soft compliance rather than a code-enforced security barrier.
- **Remediation:**  
  Engineered a two-tier defense-in-depth architecture:
  1. **Zero-Tool Surface Guarantee:** The application tool surface has zero functions capable of altering student grades, waiving fees, or approving admissions. Even a fully jailbroken model has no software path to enact a high-impact change.
  2. **HITL Ticket Boundary:** Support tickets can only be created with status `PENDING_APPROVAL`. The transitions to `SUBMITTED` or `REJECTED` are exposed exclusively on dedicated HTTP endpoints requiring staff authentication (`X-User-Role: staff`), which the model cannot reach.
- **v1.0.0 Re-test Evidence:**  
  - Test: `tests/test_prompt_injection.py::test_grade_decision_does_not_invoke_a_tool` -> **PASSED**
  - Test: `tests/test_prompt_injection.py::test_fee_decision_does_not_invoke_a_tool` -> **PASSED**
  - Test: `tests/test_prompt_injection.py::test_medical_advice_does_not_invoke_a_tool` -> **PASSED**
  - Benchmark Scenarios: `E-02`, `E-06`, `A-02`, `A-03`, `U-03`, and `U-04` -> **PASSED**

---

## Verification Summary on v1.0.0

| Failure ID | Defect Area | Remediation Type | Automated Test Coverage | Status on v1.0.0 |
|---|---|---|---|---|
| **F-01** | Tool execution loop | Application hard cap in `orchestrator.py` | `test_tool_execution_is_hard_capped...` | **PASSED** |
| **F-02** | Timetable missing course | Structured error in `tools/timetable.py` | `test_course_not_found_returns_safe_failure` | **PASSED** |
| **F-03** | Budget over-accounting | Dispatch-success counter increment | `test_guest_role_cannot_invoke_tools` | **PASSED** |
| **F-04** | Environment configuration | Onboarding verification & health checks | `test_health_endpoint`, `test_integration_groq` | **PASSED** |
| **F-05** | Dead tool code drift | Registry allow-list invariant tests | `test_contract_allow_list_matches_tool_registry` | **PASSED** |
| **F-06** | High-impact actions | Zero-tool surface + HITL endpoints | `test_grade_decision_does_not_invoke_a_tool` | **PASSED** |
