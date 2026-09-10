# QA Test Matrix: University Student-Support Case Agent

## Scope
This matrix covers the public API for the Week 2 baseline in `agent-backend/main.py`.

## Test execution notes
- The backend is tested through FastAPI's `TestClient`.
- LLM calls are mocked in the automated suite so tests remain deterministic and do not require a real Groq API key.
- Status is recorded as `PASS` when the actual result matches the expected behavior.

## Formal QA matrix

| ID | Priority | Test case | Input / setup | Expected behavior | Actual behavior | Status |
| --- | --- | --- | --- | --- | --- | --- |
| QA-01 | P0 | Health endpoint returns OK | `GET /health` | HTTP 200 and JSON body `{"status": "ok"}` | Matches expected | PASS |
| QA-02 | P0 | Valid student message accepted | `POST /api/v1/student-support` with valid text | HTTP 200 and JSON includes `response`, `prompt_version`, and `model` | Matches expected when the LLM function is mocked | PASS |
| QA-03 | P0 | Missing message field rejected | `POST` body `{}` | HTTP 422 validation error | Matches expected | PASS |
| QA-04 | P0 | Empty message rejected | `{"message": ""}` | HTTP 422 validation error | Matches expected | PASS |
| QA-05 | P0 | Whitespace-only message rejected | `{"message": "     "}` | HTTP 422 validation error | Matches expected | PASS |
| QA-06 | P0 | Non-string message rejected | `{"message": 123}` and `{"message": null}` | HTTP 422 validation error | Matches expected | PASS |
| QA-07 | P1 | Value with surrounding whitespace accepted | `{"message": "  How does course registration work?  "}` | HTTP 200, trimmed input processed successfully | Matches expected | PASS |
| QA-08 | P1 | Multiline message accepted | `{"message": "How does course registration work?\nWhat if I miss the deadline?"}` | HTTP 200 with valid structured response | Matches expected | PASS |
| QA-09 | P0 | Long message rejected | message length > 2000 chars | HTTP 422 validation error | Matches expected | PASS |
| QA-10 | P0 | Malformed JSON rejected | raw invalid JSON request body | HTTP 422 validation error | Matches expected | PASS |
| QA-11 | P1 | Unknown route returns 404 | `GET /definitely-not-a-real-route` | HTTP 404 | Matches expected | PASS |
| QA-12 | P0 | Missing API configuration is handled | `get_student_support_response` raises `LLMConfigurationError` | HTTP 503 and internal config details not exposed | Matches expected | PASS |
| QA-13 | P0 | LLM provider failure is handled | `get_student_support_response` raises `LLMRequestError` | HTTP 502 and provider failure is surfaced cleanly | Matches expected | PASS |

## Result summary
The API baseline currently behaves as expected for the implemented request-validation and error-handling scenarios. The tests provide a deterministic safety net for normal requests, malformed input, and upstream LLM failures.
