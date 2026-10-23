# Evidence Index

This folder contains the project's runtime evidence: captured traces,
test output, and screenshots. It is organized by week and purpose so a
reader can browse to the artifact that supports any claim in the
report.

Every entry below is real. Nothing here is illustrative; each trace is
a recorded run against the live backend (with the Groq API), and each
test output is a real pytest execution.


## Directory layout
evidence/
├── traces/
│ ├── week5/ - agent loop traces (3 runs)
│ ├── week6/ - memory with/without comparison (4 runs)
│ └── week8/ - final system live run (1 run, plus supporting files)
├── screenshots/
│ ├── week5/ - UI screenshots of the agent's decisions
│ └── (any others)
├── week7/ - pytest output for adversarial and full suites
└── README.md - this file



## evidence/traces/week5/ - Agent loop traces

Three real agent runs from Week 5 (the bounded agent loop).

| File | What it shows |
|---|---|
| trace1_happy_path.json | Tool call (check_timetable) followed by a grounded final answer. status=completed. |
| trace1_happy_path.md | A human-readable narrative of the same trace. |
| trace2_human_approval.json | Agent drafts a support ticket, then stops at human_approval_required. |
| trace2_human_approval.md | Narrative of the same trace. |
| trace3_safe_stop.json | Agent requests an unapproved tool; run ends at tool_not_approved. |
| trace3_safe_stop.md | Narrative of the same trace. |
| trace3_boundary_check.txt | A follow-up staff-only approval attempt, showing the endpoint returns 403 for a student. |
| agent-contract-tests.txt | Captured pytest output for the Week 5 agent test suite. |
| README.md | A short overview of the three traces. |

Covers in the report: section 6 (Tools and Agentic Workflow), section 8
(Evaluation), section 10 (Results).


## evidence/traces/week6/ - Memory with/without comparison

Four real runs demonstrating bounded per-session memory.

| File | What it shows |
|---|---|
| trace_with_memory_turn1.json | First turn with memory ON; agent drafts a ticket, status=human_approval_required. |
| trace_with_memory_turn2.json | Second turn, same session; agent recalls the drafted ticket and states its pending status. |
| trace_without_memory_turn1.json | First turn with memory OFF; identical to the ON run on turn 1. |
| trace_without_memory_turn2.json | Second turn, no memory; agent has no context and says so. |
| README.md | The comparison narrative. |

The with/without pair is the evidence for the memory feature. Turn 2
in the ON run resolves "that ticket"; turn 2 in the OFF run does not.

Covers in the report: section 7 (Memory, State and Interoperability).


## evidence/traces/week8/ - Final system live run

Captured on the day the final report was written, against the current
main branch. Used as evidence that the complete system still runs
end-to-end.

| File | What it shows |
|---|---|
| final_run_rag.json | A RAG-only question (no tools needed). Shows retrieved sources. |
| final_run_tool.json | A question that triggers the check_timetable tool. |
| final_run_ticket.json | A question that triggers a ticket draft. |
| final_run_unauthorized.json | A guest-role request that is refused. |
| README.md | Narrative of the four runs. |

Covers in the report: section 6, section 8, section 10.


## evidence/screenshots/week5/ - UI screenshots

The agent's decisions as seen in the browser during Week 5.

| File | What it shows |
|---|---|
| trace1_happy_path_timetable.png | A timetable query answered with real sessions. |
| trace2_human_approval_ticket.png | The drafted ticket card, with staff-only Approve/Reject buttons. |
| trace2_human_approval_ticket_detail.png | The same card after clicking Approve - status changed to SUBMITTED. |
| trace3_safe_stop_refuses_self_approval.png | A student attempting self-approval is blocked. |
| agent_contract_tests_passing.png | Terminal showing the 12 Week 5 agent tests passing. |
| extra_direct_answer_no_tools.png | The agent answering without a tool call. |
| extra_asks_for_missing_course_code.png | The agent handling a missing-timetable case safely. |
| extra_week4_mode_still_works.png | The older /api/v1/student-support endpoint still works after Week 5. |

Covers in the report: section 6, section 8.


## evidence/week7/ - Guardrail test output

| File | What it shows |
|---|---|
| adversarial-tests.txt | The full verbose output of tests/test_prompt_injection.py (14 tests, all passing). |
| full-suite.txt | The full test suite output at the time of Week 7 (178 tests, 1 skipped). |

Covers in the report: section 8 (Evaluation, Observability and
Guardrails).


## Reproducing any artifact

Every trace can be reproduced by:

1. Starting the backend:
   cd agent-backend && source .venv/bin/activate && uvicorn main:app --reload
2. Sending the same request (the JSON file contains the exact message and headers).
3. Or running the corresponding test:
   pytest tests/<file>::<test> -v

The test files themselves are the ground truth. The traces are the
visible record.


## What is NOT in this folder

- .env (contains the Groq API key; never committed)
- data/chroma/ (regenerated by `python ingest.py`)
- data/tickets.db and data/sessions.db (regenerated by running the system)
- node_modules/ (regenerated by `npm install`)
- __pycache__ and .pytest_cache (regenerated automatically)

All of these are in .gitignore. The repository is reproducible from
source; the runtime artifacts above are evidence of what the source
does.
