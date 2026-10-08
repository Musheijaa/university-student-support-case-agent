# MCP-Style Interface Specification — `create_support_ticket`

**Document version:** 1.0  
**Week:** 6  
**Author:** OkemaPaulMark  
**Status:** Final  
**Related files:** `agent-backend/tools/tickets.py`, `agent-backend/tools/schemas.py`, `agent-backend/tools/registry.py`, `docs/tool-catalogue.md`

---

## 1. Purpose of this document

This document describes the `create_support_ticket` capability of the
University Student-Support Case Agent as a Model Context Protocol (MCP)
style interface specification. It is written so that any external agent,
client application, or team member can understand exactly what this
capability does, how to call it, what it returns, who is allowed to use
it, and where the human boundary sits — without reading source code.

MCP (Model Context Protocol) is a standard for describing AI-callable
tools through a formal contract: capability identity, input schema,
output schema, permissions, side effects, and security boundary. This
document follows that structure applied to the ticket tool as it exists
in this project.

---

## 2. Capability identity

| Field | Value |
|---|---|
| **Tool name** | `create_support_ticket` |
| **Version** | 1.0 |
| **Host server** | University Student-Support Case Agent API |
| **Base URL (local dev)** | `http://127.0.0.1:8000` |
| **Exposed via** | Agent tool-calling loop (`POST /api/v1/agent/student-support`) and direct endpoint (`POST /api/v1/student-support`) |
| **Implemented in** | `agent-backend/tools/tickets.py` |
| **Registered in** | `agent-backend/tools/registry.py` (`TOOL_REGISTRY`) |
| **Transport** | HTTP/JSON (the tool is invoked by the application, never directly by the model) |

### What it does

`create_support_ticket` creates a **draft** support ticket record in the
application's ticket store. The draft is assigned status
`PENDING_APPROVAL` immediately on creation. It does not submit, resolve,
escalate, or act on the student's request in any way. A human staff
member must separately approve the draft through a dedicated HTTP
endpoint before anything happens.

This design is intentional: the AI agent is permitted to capture and
structure a student's problem, but it is never permitted to take action
on that problem autonomously.

---

## 3. MCP tool definition

This is the formal tool definition as registered in `TOOL_DEFINITIONS`
(`agent-backend/tools/registry.py`) and offered to the language model
during tool-calling. It follows the OpenAI/Groq function-calling schema,
which is the format MCP tool definitions use in practice.

```json
{
  "type": "function",
  "function": {
    "name": "create_support_ticket",
    "description": "Create a DRAFT support ticket (status PENDING_APPROVAL) for a student's support request. This does NOT submit, resolve, or act on the request — a human must approve it separately before anything happens. Use this when a student describes a problem needing follow-up (e.g. portal access, a technical issue, a process query that needs staff attention).",
    "parameters": {
      "type": "object",
      "properties": {
        "category": {
          "type": "string",
          "enum": ["IT Support", "Academic", "Finance", "Other"],
          "description": "The category that best describes the student's issue."
        },
        "subject": {
          "type": "string",
          "description": "Short summary of the issue, under 200 characters."
        },
        "description": {
          "type": "string",
          "description": "Full details of the issue as described by the student, under 2000 characters."
        }
      },
      "required": ["category", "subject", "description"]
    }
  }
}
```

---

## 4. Input schema

All three fields are required. The application validates inputs through
a Pydantic model (`CreateSupportTicketInput` in
`agent-backend/tools/schemas.py`) before the tool executor is ever
called. The model cannot bypass this validation.

| Field | Type | Required | Constraints | Example |
|---|---|---|---|---|
| `category` | string | yes | Must be exactly one of: `IT Support`, `Academic`, `Finance`, `Other`. Any other value is rejected. | `"IT Support"` |
| `subject` | string | yes | Non-empty after stripping whitespace. Maximum 200 characters. | `"Cannot access student portal"` |
| `description` | string | yes | Non-empty after stripping whitespace. Maximum 2000 characters. | `"My login credentials are rejected every time I try to sign in."` |

### Valid input example

```json
{
  "category": "IT Support",
  "subject": "Cannot access student portal",
  "description": "My login credentials are rejected every time I try to sign in to the student portal. I have tried resetting my password twice but the problem persists."
}
```

### Invalid input examples

```json
{ "category": "Grades", "subject": "Wrong mark", "description": "..." }
```
→ Rejected. `"Grades"` is not in the allowed category list.

```json
{ "subject": "Portal issue", "description": "Cannot log in." }
```
→ Rejected. `category` is required.

```json
{ "category": "Academic", "subject": "   ", "description": "Details here." }
```
→ Rejected. `subject` is whitespace-only.

---

## 5. Output schema

The tool always returns a JSON object. It never raises an exception to
the caller — all failure cases are represented as `success: false` with
an `error` string.

### Success response

```json
{
  "success": true,
  "ticket_id": "DRAFT-001",
  "status": "PENDING_APPROVAL",
  "category": "IT Support",
  "subject": "Cannot access student portal",
  "error": null
}
```

| Field | Type | Description |
|---|---|---|
| `success` | boolean | Always `true` on success |
| `ticket_id` | string | Unique identifier, format `DRAFT-NNN` (e.g. `DRAFT-001`) |
| `status` | string | Always `PENDING_APPROVAL` on creation — never anything else |
| `category` | string | The validated category from the input |
| `subject` | string | The validated subject from the input |
| `error` | null | Always null on success |

### Failure response

```json
{
  "success": false,
  "ticket_id": null,
  "status": null,
  "category": null,
  "subject": null,
  "error": "<human-readable error message>"
}
```

The `error` field contains a safe, human-readable message. It never
contains a stack trace, database path, or internal implementation detail.

---

## 6. Permissions and authorization

Authorization is enforced by `dispatch_tool_call` in
`agent-backend/tools/registry.py` before the executor is called. The
caller's role is read from the `X-User-Role` HTTP request header and
resolved by `agent-backend/auth.py`.

| Role | Allowed to call `create_support_ticket`? |
|---|---|
| `student` | ✅ Yes |
| `staff` | ✅ Yes |
| `guest` | ❌ No — rejected with authorization error |
| *(missing header)* | Defaults to `student` — allowed |
| *(unrecognized value)* | Defaults to `guest` — rejected |

**Authorization error response (guest or unrecognized role):**

```json
{
  "success": false,
  "error": "You are not authorized to use 'create_support_ticket'."
}
```

**Important note on the authorization model:** The role is taken from
the `X-User-Role` header and trusted as-is. This is an explicit
simulation for this academic prototype — there is no login, password, or
token verification. It exists to give authorization rules something
concrete to enforce. It is not a security boundary against a malicious
client.

---

## 7. Side effects and storage

### What gets written

A single row is inserted into the SQLite ticket store
(`agent-backend/data/tickets.db`) with the following fields:

| Column | Value |
|---|---|
| `ticket_id` | Auto-generated `DRAFT-NNN` |
| `category` | From validated input |
| `subject` | From validated input |
| `description` | From validated input |
| `status` | Always `PENDING_APPROVAL` |
| `created_at` | UTC ISO timestamp at time of creation |
| `updated_at` | Same as `created_at` on creation |

### What the tool cannot do

The `create_support_ticket` tool:

- **Cannot** approve its own draft
- **Cannot** change a ticket's status to `SUBMITTED` or `REJECTED`
- **Cannot** read, list, or delete existing tickets
- **Cannot** modify any existing ticket record
- **Cannot** trigger any notification, email, or external system call
- **Cannot** make any decision about the student's underlying problem

These actions are either not implemented, or are only reachable through
separate human-only HTTP endpoints that the model has no path to call.

### Ticket ID generation

Ticket IDs are assigned sequentially based on the current row count in
the database (`DRAFT-001`, `DRAFT-002`, etc.). This is a simple
prototype scheme — not a UUID — suitable for the bounded academic
demonstration scope.

---

## 8. State machine and human hand-off

Every ticket created by this tool starts in `PENDING_APPROVAL` and can
only leave that state through a human staff member calling one of the
two approval endpoints. The model has no path to these endpoints.

```
                    create_support_ticket (tool)
                              │
                              ▼
                    ┌─────────────────────┐
                    │   PENDING_APPROVAL  │  ← only state the tool can create
                    └─────────────────────┘
                         │           │
          staff: /approve            staff: /reject
                         │           │
                         ▼           ▼
                    SUBMITTED     REJECTED
                    (terminal)    (terminal)
```

Once a ticket reaches `SUBMITTED` or `REJECTED` its status cannot be
changed again. Any attempt to approve or reject a ticket that is already
in a terminal state returns:

```json
{
  "success": false,
  "error": "Ticket 'DRAFT-001' is already SUBMITTED; its state cannot be changed."
}
```

### Human approval endpoints

These endpoints are in `agent-backend/main.py`. They are plain HTTP
endpoints — not tools — and are never offered to the language model.

| Endpoint | Method | Required role | Effect |
|---|---|---|---|
| `GET /api/v1/support-tickets/{ticket_id}` | GET | any | Returns the full ticket record |
| `POST /api/v1/support-tickets/{ticket_id}/approve` | POST | `staff` only | `PENDING_APPROVAL` → `SUBMITTED` |
| `POST /api/v1/support-tickets/{ticket_id}/reject` | POST | `staff` only | `PENDING_APPROVAL` → `REJECTED` |

A non-staff caller on the approve or reject endpoint receives:

```
HTTP 403 Forbidden
{"detail": "Only staff may approve a support ticket."}
```

---

## 9. Security boundary

This section states explicitly what this capability can and cannot do,
and where human control is required. This is the core of the MCP
security boundary.

### The tool MAY

- Accept a student's described problem as structured input
- Validate that the input meets the required schema
- Write one `PENDING_APPROVAL` draft record to the local ticket store
- Return the draft's ID and status to the calling agent

### The tool MUST NOT (and cannot)

- Approve, submit, or resolve any ticket
- Make any decision about the student's underlying problem
- Access, modify, or delete any existing ticket
- Call any external system, send any notification, or trigger any workflow
- Bypass the human approval gate
- Make decisions about grades, fees, admissions, disciplinary matters, or medical issues
- Execute any action with real institutional consequence

### Human approval is always required before

- Any staff member acts on the student's problem
- The ticket status moves from `PENDING_APPROVAL`
- Any downstream process is triggered

The agent's authority ends at creating the draft. Everything after that
is a human decision.

---

## 10. Error catalogue

Every possible failure mode, its cause, and the exact response returned
by `dispatch_tool_call`.

| Error case | Cause | Response |
|---|---|---|
| Unknown tool name | Model requested a tool not in `TOOL_REGISTRY` | `{"success": false, "error": "Tool 'X' is not available."}` |
| Malformed JSON arguments | Model returned arguments that are not valid JSON | `{"success": false, "error": "Tool arguments were not valid JSON."}` |
| Unauthorized caller | `X-User-Role` is `guest` or unrecognized | `{"success": false, "error": "You are not authorized to use 'create_support_ticket'."}` |
| Missing required field | `category`, `subject`, or `description` absent | `{"success": false, "error": "Invalid input for 'create_support_ticket': Field required"}` |
| Invalid category | `category` not in the allowed enum | `{"success": false, "error": "Invalid input for 'create_support_ticket': category must be one of ('IT Support', 'Academic', 'Finance', 'Other'), got 'X'"}` |
| Blank subject or description | Whitespace-only string after stripping | `{"success": false, "error": "Invalid input for 'create_support_ticket': must not be empty or whitespace-only"}` |
| Subject too long | `subject` exceeds 200 characters | `{"success": false, "error": "Invalid input for 'create_support_ticket': String should have at most 200 characters"}` |
| Description too long | `description` exceeds 2000 characters | `{"success": false, "error": "Invalid input for 'create_support_ticket': String should have at most 2000 characters"}` |
| Database unavailable | SQLite file missing, locked, or corrupt | `{"success": false, "error": "The support ticket service is temporarily unavailable. Please try again later."}` |
| Unexpected tool response | Executor returned a value that fails output schema validation | `{"success": false, "error": "The 'create_support_ticket' tool returned an unexpected response."}` |
| Unexpected internal error | Any other unhandled exception in the executor | `{"success": false, "error": "The tool encountered an unexpected error."}` |

In every failure case `success` is `false`, `ticket_id` is `null`, and
no record is written to the database. The error message is safe to
surface to the student — it never contains internal paths, stack traces,
or database details.

---

## 11. Complete invocation examples

These examples show the full round-trip as it occurs inside the agent
loop. The model requests the tool; the application validates, executes,
and returns the result.

### Example 1 — Successful ticket creation

**Model tool-call request (inside agent loop):**
```json
{
  "tool": "create_support_ticket",
  "arguments": {
    "category": "IT Support",
    "subject": "Cannot access student portal",
    "description": "My login credentials are rejected every time I try to sign in. I have tried resetting my password twice but the problem persists."
  }
}
```

**Application response returned to model:**
```json
{
  "success": true,
  "ticket_id": "DRAFT-001",
  "status": "PENDING_APPROVAL",
  "category": "IT Support",
  "subject": "Cannot access student portal",
  "error": null
}
```

**Agent endpoint response (what the student sees via `POST /api/v1/agent/student-support`):**
```json
{
  "run_id": "5d306292-10b0-4e2e-aeb6-fc4c00b31a7f",
  "status": "human_approval_required",
  "response": "I've created a draft support ticket for you. It's currently awaiting approval by a staff member and has not yet been submitted or acted upon.",
  "plan": "...",
  "iteration_count": 1,
  "tool_call_count": 1,
  "steps": [
    {
      "iteration": 1,
      "decision": "tool_call",
      "tool_name": "create_support_ticket",
      "tool_arguments": {
        "category": "IT Support",
        "subject": "Cannot access student portal",
        "description": "..."
      },
      "tool_result": {
        "success": true,
        "ticket_id": "DRAFT-001",
        "status": "PENDING_APPROVAL",
        "category": "IT Support",
        "subject": "Cannot access student portal",
        "error": null
      },
      "observation": "Draft ticket DRAFT-001 created with status PENDING_APPROVAL; it needs staff approval before anything happens.",
      "error": null
    }
  ]
}
```

---

### Example 2 — Unauthorized caller (guest role)

**Request header:** `X-User-Role: guest`

**Application response:**
```json
{
  "success": false,
  "ticket_id": null,
  "status": null,
  "category": null,
  "subject": null,
  "error": "You are not authorized to use 'create_support_ticket'."
}
```

No record is written. The agent observes the failure and re-plans.

---

### Example 3 — Invalid category

**Model tool-call arguments:**
```json
{
  "category": "Grades",
  "subject": "My mark is wrong",
  "description": "I believe my exam was marked incorrectly."
}
```

**Application response:**
```json
{
  "success": false,
  "ticket_id": null,
  "status": null,
  "category": null,
  "subject": null,
  "error": "Invalid input for 'create_support_ticket': category must be one of ('IT Support', 'Academic', 'Finance', 'Other'), got 'Grades'"
}
```

Note: a grading dispute would also be outside the agent's permitted
scope regardless of category — the system prompt instructs the model
not to make grading decisions, and the human approval gate means no
action can be taken autonomously even if a draft were created.

---

### Example 4 — Human approval (staff action, not a tool)

After a ticket is created, a staff member calls the approval endpoint
directly. This is a plain HTTP call, not a tool call — the model has no
path to this endpoint.

**Request:**
```
POST /api/v1/support-tickets/DRAFT-001/approve
X-User-Role: staff
X-User-Id: staff-member-01
```

**Response:**
```json
{
  "success": true,
  "ticket_id": "DRAFT-001",
  "status": "SUBMITTED",
  "error": null
}
```

**Rejection:**
```
POST /api/v1/support-tickets/DRAFT-001/reject
X-User-Role: staff
```
```json
{
  "success": true,
  "ticket_id": "DRAFT-001",
  "status": "REJECTED",
  "error": null
}
```

---

## 12. Data handling, retention, and deletion

| Question | Answer |
|---|---|
| **What is stored?** | `ticket_id`, `category`, `subject`, `description`, `status`, `created_at`, `updated_at` |
| **Where is it stored?** | Local SQLite file at `agent-backend/data/tickets.db` (gitignored — not committed to the repository) |
| **Why is it stored?** | To give staff a persistent, reviewable record of student-reported problems that can be approved or rejected asynchronously |
| **Who can read it?** | Any caller via `GET /api/v1/support-tickets/{ticket_id}` (no role restriction on read) |
| **Who can change status?** | Staff only, via the approve/reject endpoints |
| **Who can delete records?** | No deletion endpoint exists in this prototype. Records persist for the lifetime of the database file. |
| **Does it contain personal data?** | Only what the student types into `subject` and `description`. No name, student number, email, or institutional record is captured by this tool. |
| **Is it sent to any external service?** | No. The ticket store is local SQLite. The `description` text is passed to the Groq LLM as part of the agent's context, but only to help the model formulate the draft — it is not stored by Groq beyond the API call lifetime. |
| **Retention policy (prototype)** | Records are retained indefinitely in the local database file. In a production system, a retention policy (e.g. 90 days for unactioned drafts) would be required. |
| **Deletion (prototype)** | The database file can be deleted manually to clear all records. No per-record deletion API exists in this prototype. |

---

## 13. How this fits into the Week 6 deliverables

This MCP-style interface specification is the **Integration or
MCP-style interface specification** deliverable for Week 6. It
documents one existing project capability — the `create_support_ticket`
tool — as a formal, reusable interface contract.

The value of writing this document is:

- Any external agent or client can call this capability correctly
  without reading source code
- The security boundary and human approval gate are stated explicitly
  and unambiguously
- The error catalogue gives implementers everything they need to handle
  every failure case
- The data handling section satisfies the Week 6 requirement to document
  what is stored, why, who can access it, and retention/deletion policy
- The state machine diagram makes the human hand-off boundary visually
  clear

This document does not require any code changes. The capability it
describes is fully implemented and tested as of Week 4/5.

---

## 14. References

- `agent-backend/tools/tickets.py` — executor implementation
- `agent-backend/tools/schemas.py` — `CreateSupportTicketInput`, `CreateSupportTicketOutput`, `TicketRecord`
- `agent-backend/tools/registry.py` — `TOOL_REGISTRY`, `dispatch_tool_call`, `TOOL_DEFINITIONS`
- `agent-backend/auth.py` — `Actor`, `get_actor`, role resolution
- `agent-backend/main.py` — approval/rejection HTTP endpoints
- `docs/tool-catalogue.md` — Week 4 tool catalogue (human-readable schemas and failure behavior)
- `docs/architecture.md` — system architecture and data flow diagrams
- `docs/agent-task-contract.md` — Week 5 agent task contract (approved tools, limits, stop conditions)
- Model Context Protocol specification — https://modelcontextprotocol.io
