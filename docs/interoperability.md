# Week 6 - Interoperability: MCP-style interface for check_timetable

The capstone brief (Week 6) asks for "one external integration OR one
project capability as an MCP-style interface: capability, inputs,
outputs, permissions and security boundary."

This document specifies check_timetable as an MCP-style tool
interface. No external network service is introduced; instead, an
existing internal capability is documented in the form a Model Context
Protocol host would consume.

## Capability

Name: check_timetable
Version: 1.0
Purpose: Return scheduled sessions for a course code, optionally
filtered to a single date. Read-only; no side effects.

## Inputs

| Field | Type | Required | Constraints |
|---|---|---|---|
| course_code | string | yes | 3-12 chars, uppercase alphanumerics (e.g. CSC2101) |
| date | string (ISO 8601 date) | no | If provided, only sessions on this date are returned |

Invalid inputs return a structured error with a human-readable reason.
They are never executed as a partial match.

## Outputs

Success returns a JSON object with success=true, the course_code, and a
sessions array. Each session has: course_code, date, start_time,
end_time, venue, session_type.

Failure (invalid input, no matching session, service unavailable)
returns: { "success": false, "error": "..." }

A failed call never returns fabricated sessions. If the underlying data
file is missing or malformed, the tool returns a structured error, not
a guess (see docs/tool-test-evidence.md for the tests that prove this).

## Permissions

| Role | Allowed? | Notes |
|---|---|---|
| student | yes | Default role |
| staff | yes | |
| guest | no | Rejected before execution |
| Unknown role | no | Defaults to guest (least privilege) |

Authorization is enforced in tools/registry.py::dispatch_tool_call
before the tool function runs. The tool has no side effects, so a
successful call cannot change any state.

## Security boundary

- Read-only. No writes, deletes, or state transitions.
- Synthetic data. Reads from data/timetable/timetable.json, which is
  clearly labelled as project-supplied synthetic data.
- No external network. The tool does not call any third party.
- No PII. The data contains only course codes, dates, times, and venue
  names.
- Bounded output. A course code matches a small number of sessions; the
  tool does not paginate unbounded data.
- Error containment. Any exception during execution is converted to
  a structured error - never a stack trace, never a crash of the agent
  loop.

## Interoperability notes (MCP-style)

Were this exposed through a Model Context Protocol host, the manifest
would be:

- Tool name: check_timetable
- Description: "Look up university timetable sessions for a course
  code, optionally filtered to one date."
- Input schema: as in the Inputs section above (JSON Schema
  type: object with the two properties).
- Output schema: as in the Outputs section above (JSON Schema oneOf
  for the success and failure shapes).
- Permissions: as in the Permissions section above.
- Side-effect class: read.
- Rate/size limits: one call returns all matching sessions for the
  given course; the underlying data is small and static.

The Week 5 agent invokes this capability through
tools/registry.py::dispatch_tool_call, which is the MCP-host
equivalent of the "call the tool, validate the result" step.

## Why this satisfies the brief

- Capability, inputs, outputs, permissions, security boundary - all
  specified above.
- No new external dependency. The brief allows documenting a project
  capability in MCP form rather than integrating an external service.
- Maps to real code. Every field above is enforced in
  tools/registry.py and covered by tests in tests/test_tool_registry.py
  and tests/test_tools_timetable.py.
