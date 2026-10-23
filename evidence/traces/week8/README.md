# Week 8 - Final System Live Traces

Four live runs captured against the current main branch, showing the
complete system working end-to-end. Each was sent through
POST /api/v1/agent/student-support with the live Groq API.

All four were captured with X-Memory: off to isolate agent behavior
from the memory feature (which is covered in evidence/traces/week6/).

## Run 1 - RAG-only (final_run_rag.json)

Query: "What counts as examination malpractice at Makerere?"
Role: student

The agent retrieved evidence from the policy corpus and answered
directly without a tool call. Sources are in the response, tool_calls
is empty. status=completed.

## Run 2 - Tool call (final_run_tool.json)

Query: "Is there a CSC2101 class tomorrow?"
Role: student

The model requested check_timetable; the application validated and
executed it; the result was fed back and the agent produced a final
answer. status=completed (or a safe stop if no session exists on that
date).

## Run 3 - Ticket draft (final_run_ticket.json)

Query: "I lost my student ID and need a replacement."
Role: student

The model requested create_support_ticket; a draft with
status=PENDING_APPROVAL was created. The run stopped at
human_approval_required - the agent's authority ends at a draft.

## Run 4 - Unauthorized (final_run_unauthorized.json)

Query: "Check the timetable for CSC2101."
Role: guest

The model requested check_timetable but the dispatch layer refused it
(guest role is not authorized). The tool was never executed. The run
ends in a bounded terminal status with no successful tool result.

## What this demonstrates

- The complete system runs end-to-end against the live model.
- The tool allow-list, role authorization, and HITL approval still
  work after all the layered changes.
- The four terminal statuses that matter in practice (completed,
  human_approval_required, tool_not_approved, and one bounded stop)
  are all reachable and correct.
