# MCP-Style Interface Specification — `create_support_ticket`

**Document version:** 1.0 | **Week:** 6 | **Author:** OkemaPaulMark | **Status:** Final  
**Related files:** `tools/tickets.py`, `tools/schemas.py`, `tools/registry.py`, `docs/tool-catalogue.md`

---

## 1. Purpose

This document describes the `create_support_ticket` capability as a formal MCP-style interface contract — covering identity, input/output schema, permissions, side effects, security boundary, and error catalogue — so any agent, client, or team member can integrate with it without reading source code.

---

## 2. Capability identity

| Field | Value |
|---|---|
| **Tool name** | `create_support_ticket` |
| **Version** | 1.0 |
| **Base URL (local dev)** | `http://127.0.0.1:8000` |
| **Exposed via** | `POST /api/v1/agent/student-support` (agent loop) and `POST /api/v1/student-support` (direct) |
| **Implemented in** | `agent-backend/tools/tickets.py` |
| **Transport** | HTTP/JSON — invoked by the application, never directly by the model |

Creates a **draft** ticket with status `PENDING_APPROVAL`. It does not submit, resolve, or act on the request. A human staff member must approve it separately.

---

## 3. MCP tool definition

```json
{
  "type": "function",
  "function": {
    "name": "create_support_ticket",
    "description": "Create a DRAFT support ticket (status PENDING_APPROVAL) for a student's support request. Does NOT submit or resolve the request — a human must approve it separately.",
    "parameters": {
      "type": "object",
      "properties": {
        "category": {
          "type": "string",
          "enum": ["IT Support", "Academic", "Finance", "Other"]
        },
        "subject": {
          "type": "string",
          "description": "Short summary of the issue, under 200 characters."
        },
        "description": {
          "type": "string",
          "description": "Full details of the issue, under 2000 characters."
        }
      },
      "required": ["category", "subject", "description"]
    }
  }
}
```

---

## 4. Input schema

Validated by `CreateSupportTicketInput` (Pydantic) in `tools/schemas.py` before the executor is called.

| Field | Type | Constraints |
|---|---|---|
| `category` | string | Required. One of: `IT Support`, `Academic`, `Finance`, `Other` |
| `subject` | string | Required. Non-empty, max 200 characters |
| `description` | string | Required. Non-empty, max 2000 characters |

**Valid example:**
```json
{
  "category": "IT Support",
  "subject": "Cannot access student portal",
  "description": "My login credentials are rejected every time I try to sign in. Password reset has not helped."
}
```

---

## 5. Output schema

Always returns a JSON object. Never raises — failures are `success: false` with an `error` string.

**Success:**
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

**Failure:**
```json
{
  "success": false,
  "ticket_id": null,
  "status": null,
  "category": null,
  "subject": null,
  "error": "<human-readable message — no stack traces or internal paths>"
}
```

---

## 6. Permissions

Role is read from the `X-User-Role` header and resolved by `auth.py`. Missing header defaults to `student`; unrecognized value defaults to `guest`.

| Role | Allowed |
|---|---|
| `student` | yes |
| `staff` | yes|
| `guest` / unrecognized | no→ `{"success": false, "error": "You are not authorized to use 'create_support_ticket'."}` |

> Note: role is trusted from the header — this is a simulation for the academic prototype, not a real authentication boundary.

---

## 7. Side effects and storage

**Written to SQLite** (`agent-backend/data/tickets.db`):

| Column | Value |
|---|---|
| `ticket_id` | Auto-generated `DRAFT-NNN` |
| `category`, `subject`, `description` | From validated input |
| `status` | Always `PENDING_APPROVAL` |
| `created_at` / `updated_at` | UTC ISO timestamp |

**The tool cannot:** approve its own draft, change ticket status, read/list/delete existing tickets, send notifications, or trigger any external system.

---

## 8. State machine and human hand-off

```
        create_support_ticket (tool)
                  │
                  ▼
        ┌─────────────────────┐
        │   PENDING_APPROVAL  │  ← only state the tool creates
        └─────────────────────┘
             │           │
  staff: /approve    staff: /reject
             │           │
             ▼           ▼
        SUBMITTED     REJECTED
        (terminal)    (terminal)
```

Terminal states cannot be changed. Attempting to approve/reject a terminal ticket returns:
```json
{"success": false, "error": "Ticket 'DRAFT-001' is already SUBMITTED; its state cannot be changed."}
```

**Human-only approval endpoints** (never offered to the model):

| Endpoint | Method | Role | Effect |
|---|---|---|---|
| `GET /api/v1/support-tickets/{id}` | GET | any | Read ticket |
| `POST /api/v1/support-tickets/{id}/approve` | POST | `staff` | → `SUBMITTED` |
| `POST /api/v1/support-tickets/{id}/reject` | POST | `staff` | → `REJECTED` |

Non-staff callers on approve/reject receive `HTTP 403`.

---

## 9. Security boundary

**MAY:**
- Accept and validate structured input from a student
- Write one `PENDING_APPROVAL` draft to the local ticket store
- Return the draft ID and status to the agent

**MUST NOT (and cannot):**
- Approve, submit, or resolve any ticket
- Access, modify, or delete existing tickets
- Call any external system or send notifications
- Make decisions about grades, fees, admissions, disciplinary, or medical matters
- Bypass the human approval gate

---

## 10. Error catalogue

| Error case | Response |
|---|---|
| Unknown tool name | `{"success": false, "error": "Tool 'X' is not available."}` |
| Malformed JSON arguments | `{"success": false, "error": "Tool arguments were not valid JSON."}` |
| Unauthorized caller | `{"success": false, "error": "You are not authorized to use 'create_support_ticket'."}` |
| Missing required field | `{"success": false, "error": "Invalid input for 'create_support_ticket': Field required"}` |
| Invalid category | `{"success": false, "error": "Invalid input for 'create_support_ticket': category must be one of ('IT Support', 'Academic', 'Finance', 'Other'), got 'X'"}` |
| Blank subject or description | `{"success": false, "error": "Invalid input for 'create_support_ticket': must not be empty or whitespace-only"}` |
| Subject > 200 chars | `{"success": false, "error": "Invalid input for 'create_support_ticket': String should have at most 200 characters"}` |
| Description > 2000 chars | `{"success": false, "error": "Invalid input for 'create_support_ticket': String should have at most 2000 characters"}` |
| Database unavailable | `{"success": false, "error": "The support ticket service is temporarily unavailable. Please try again later."}` |
| Unexpected tool response | `{"success": false, "error": "The 'create_support_ticket' tool returned an unexpected response."}` |
| Unexpected internal error | `{"success": false, "error": "The tool encountered an unexpected error."}` |

In every failure case no record is written to the database.

---

## 11. Invocation examples

### Success
```json
// Tool call
{"category": "IT Support", "subject": "Cannot access student portal", "description": "Login rejected after two password resets."}

// Response
{"success": true, "ticket_id": "DRAFT-001", "status": "PENDING_APPROVAL", "category": "IT Support", "subject": "Cannot access student portal", "error": null}
```

### Unauthorized (guest)
```json
{"success": false, "ticket_id": null, "status": null, "category": null, "subject": null, "error": "You are not authorized to use 'create_support_ticket'."}
```

### Invalid category
```json
// Tool call
{"category": "Grades", "subject": "My mark is wrong", "description": "I believe my exam was marked incorrectly."}

// Response
{"success": false, "error": "Invalid input for 'create_support_ticket': category must be one of ('IT Support', 'Academic', 'Finance', 'Other'), got 'Grades'"}
```

### Staff approval (HTTP, not a tool call)
```
POST /api/v1/support-tickets/DRAFT-001/approve
X-User-Role: staff
→ {"success": true, "ticket_id": "DRAFT-001", "status": "SUBMITTED", "error": null}
```

---

## 12. Data handling

| Question | Answer |
|---|---|
| **Stored fields** | `ticket_id`, `category`, `subject`, `description`, `status`, `created_at`, `updated_at` |
| **Location** | `agent-backend/data/tickets.db` (local SQLite, gitignored) |
| **Who can read** | Any caller via `GET /api/v1/support-tickets/{id}` |
| **Who can change status** | Staff only (approve/reject endpoints) |
| **Deletion** | No deletion endpoint; delete the `.db` file to clear all records |
| **Personal data** | Only what the student types into `subject`/`description` — no name, student number, or email captured |
| **External transmission** | `description` is passed to the Groq LLM during the agent call; not stored beyond the API call lifetime |
| **Retention (prototype)** | Indefinite; a production system would require a defined retention policy |

---

## 13. Week 6 fit

This document is the **MCP-style interface specification** deliverable for Week 6. It covers the full contract for `create_support_ticket` — schema, permissions, state machine, security boundary, error catalogue, and data handling — without requiring any code changes. The capability is fully implemented and tested as of Week 4/5.

---

## 14. References

- `agent-backend/tools/tickets.py` — executor
- `agent-backend/tools/schemas.py` — `CreateSupportTicketInput`, `CreateSupportTicketOutput`
- `agent-backend/tools/registry.py` — `TOOL_REGISTRY`, `dispatch_tool_call`
- `agent-backend/auth.py` — role resolution
- `agent-backend/main.py` — approval/rejection endpoints
- `docs/tool-catalogue.md` — Week 4 tool catalogue
- `docs/architecture.md` — system architecture
- Model Context Protocol — https://modelcontextprotocol.io
