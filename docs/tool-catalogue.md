# Tool Catalogue — Week 4

Every tool the model may request is registered in exactly one place:
`agent-backend/tools/registry.py` (`TOOL_REGISTRY` / `TOOL_DEFINITIONS`).
Nothing outside that allow-list is ever callable. The model only ever
*requests* a tool by name and arguments; the application validates,
authorizes, executes, and validates the result before anything is
trusted — see `docs/architecture.md` for the full request/response
loop.

**Authorization model (bounded, not real authentication):** every
request carries an `X-User-Role` header (`student` / `staff` / `guest`,
defaulting to `student` if omitted) and an optional `X-User-Id`,
resolved in `agent-backend/auth.py`. This is an explicit simulation for
this academic phase — there is no login, password, or token
verification behind it. It exists only so tool/endpoint authorization
rules have something concrete to check.

---

## Tool: `check_timetable`

### Purpose

Retrieve real class-schedule sessions for a course code from the
application's timetable data. Read-only; the model is instructed to
never guess a schedule and to call this tool instead.

### Input

```json
{
  "course_code": "BSE4104",
  "date": "2026-09-24"
}
```

| Field | Type | Required | Validation |
|---|---|---|---|
| `course_code` | string | yes | Normalized to uppercase; must match `^[A-Z]{2,5}\d{3,5}$` (e.g. `BSE4104`) |
| `date` | string | no | Must be a valid ISO date (`YYYY-MM-DD`) if supplied |

### Output

```json
{
  "success": true,
  "course_code": "BSE4104",
  "sessions": [
    {"date": "2026-09-24", "start_time": "10:00", "end_time": "12:00", "venue": "Room 204"}
  ],
  "error": null
}
```

On no match: `{"success": false, "course_code": "BSE4104", "sessions": [], "error": "No timetable information found for BSE4104"}`.

**Data source:** `agent-backend/data/timetable/timetable.json` — synthetic, team-created data, explicitly labeled as such in the file itself (`_disclaimer` field). Not an official university feed.

### Authorization

`student` and `staff` may call this tool. `guest` is rejected with `"You are not authorized to use 'check_timetable'."`.

### Failure behavior

| Case | Behavior |
|---|---|
| Missing `course_code` | Pydantic validation error → `{"success": false, "error": "Invalid input for 'check_timetable': ..."}` |
| Malformed `course_code` (e.g. empty, wrong shape) | Same as above |
| Invalid `date` | Same as above |
| Course not found | `{"success": false, "error": "No timetable information found for ..."}` — not a guess |
| Timetable file missing/unreadable | Caught as a service-unavailable error: `{"success": false, "error": "The timetable service is temporarily unavailable. Please try again later."}` |
| Malformed/unexpected tool return value | Caught by output-schema validation: `{"success": false, "error": "The 'check_timetable' tool returned an unexpected response."}` |

---

## Tool: `create_support_ticket`

### Purpose

Create a **draft** support ticket (`status: PENDING_APPROVAL`) from a student's described problem. This is a deliberately low-risk, simulated side effect: it never submits, resolves, or acts on the request — only a human calling the separate approval endpoint can do that.

### Input

```json
{
  "category": "IT Support",
  "subject": "Unable to access student portal",
  "description": "The student portal is rejecting my login."
}
```

| Field | Type | Required | Validation |
|---|---|---|---|
| `category` | string | yes | Must be one of `IT Support`, `Academic`, `Finance`, `Other` |
| `subject` | string | yes | Non-empty, ≤200 chars |
| `description` | string | yes | Non-empty, ≤2000 chars |

### Output

```json
{
  "success": true,
  "ticket_id": "DRAFT-001",
  "status": "PENDING_APPROVAL",
  "category": "IT Support",
  "subject": "Unable to access student portal",
  "error": null
}
```

**Storage:** SQLite (`agent-backend/data/tickets.db`, stdlib `sqlite3`, no new dependency) — chosen per the brief's guidance for a bounded Week 4 demonstration rather than introducing new infrastructure.

### Authorization

`student` and `staff` may create a draft (for the current bounded demo, any authenticated actor may create their own draft). `guest` is rejected the same way as `check_timetable`.

**Approving or rejecting a ticket is a completely separate action, never exposed to the model as a tool at all** — see the endpoints below.

### Failure behavior

| Case | Behavior |
|---|---|
| Missing `category`/`subject`/`description` | Validation error → `{"success": false, "error": "Invalid input for 'create_support_ticket': ..."}` |
| Invalid `category` (not in the allowed list) | Same as above |
| Blank subject/description (whitespace-only) | Same as above |
| Database unavailable | `{"success": false, "error": "The support ticket service is temporarily unavailable. Please try again later."}` |
| Malformed/unexpected tool return value | `{"success": false, "error": "The 'create_support_ticket' tool returned an unexpected response."}` |

---

## Ticket approval (human-only, not a tool)

These are plain authenticated HTTP endpoints in `main.py` — the model has no path to call them.

| Endpoint | Method | Authorization | Effect |
|---|---|---|---|
| `/api/v1/support-tickets/{ticket_id}` | GET | any | Returns the ticket's current record |
| `/api/v1/support-tickets/{ticket_id}/approve` | POST | `staff` only (else `403 Forbidden`) | `PENDING_APPROVAL` → `SUBMITTED` |
| `/api/v1/support-tickets/{ticket_id}/reject` | POST | `staff` only (else `403 Forbidden`) | `PENDING_APPROVAL` → `REJECTED` |

State-transition failure behavior (both endpoints, same underlying logic in `tools/tickets.py`):

| Case | Behavior |
|---|---|
| Ticket does not exist | `{"success": false, "error": "Ticket '...' was not found."}` |
| Ticket already `SUBMITTED` or `REJECTED` | `{"success": false, "error": "Ticket '...' is already ...; its state cannot be changed."}` |
| Valid `PENDING_APPROVAL` ticket, authorized caller | `{"success": true, "ticket_id": "...", "status": "SUBMITTED"/"REJECTED"}` |

---

## Bounded tool-calling loop

`llm/service.py`'s `_run_tool_calling_loop` enforces `MAX_TOOL_CALLS` (default 3, env `MAX_TOOL_CALLS`) two ways: it stops *requesting* new tool calls from the model once the bound is reached (`tool_choice="none"`), and — defensively, in case a provider or a bug ignores that — it will not *execute* more than the bound regardless of what the model asks for. The whole loop is also capped at a small, finite number of round-trips, so a request can never hang indefinitely waiting on the model to produce a final answer.
