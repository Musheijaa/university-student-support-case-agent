# v1.0.0 — Final Capstone Release

**UniSupport AI** — a bounded, RAG-grounded, tool-using, agentic student-support case agent for Makerere University. BSE4104 Emerging Trends in Software Engineering capstone, Group L.

This is the final tagged release of the 8-week build. Verified end-to-end from a genuinely clean clone (fresh virtual environment, fresh git history), following only `README.md`: **178/178 automated tests passing**.

## What's in this release

- **Week 2 — Foundation model baseline:** Groq-backed chat completion through versioned prompts (V1.0, V2.0).
- **Week 3 — Retrieval-augmented generation:** answers grounded in a controlled corpus of real Makerere University policy documents, with cited `document`/`page` sources (`docs/rag-architecture.md`, `docs/rag-evaluation.md`).
- **Week 4 — Explicit tool calling:** `check_timetable` and `create_support_ticket`, executed by the application and never by the model, with a strict allow-list and role-based authorization (`docs/tool-catalogue.md`). Ticket submission requires a separate staff-only approval step the model cannot reach.
- **Week 5 — Bounded agent:** a plan→act→observe loop over the same tools, hard-capped by iteration and tool-call budgets enforced in code (not trusted to the model), stopping at one of six terminal statuses (`docs/agent-task-contract.md`).
- **Week 6 — Memory, state, and interoperability:** bounded one-turn-per-session memory (24h TTL), a privacy-filtered case-history store that rejects raw transcripts/PII at write time, a persisted 6-stage run-state machine, and an MCP-style interface spec for `check_timetable` (`docs/memory-design.md`, `docs/interoperability.md`).
- **Week 7 — Evaluation, observability, guardrails:** a 39-scenario evaluation benchmark across six archetypes (normal, edge, incorrect-info, adversarial, tool-failure, unauthorized), a 14-test adversarial/prompt-injection suite, seven documented defense-in-depth guardrails, and a failure catalogue of six genuine issues found and fixed with re-test evidence (`docs/evaluation.md`, `docs/guardrails.md`, `docs/failure-catalogue.md`).
- **Week 8 — Hardening and release:** README rewritten to cover the full system (it previously only documented Weeks 2-4), `.env.example` completed with every Week 6 variable, a thorough secrets scan, and this tag.

## API surface

| Endpoint | Method | Purpose |
|---|---|---|
| `/health` | GET | Liveness check |
| `/api/v1/student-support` | POST | RAG-grounded answer, single-round-trip tool calling |
| `/api/v1/agent/student-support` | POST | The full bounded agent, with optional per-session memory |
| `/api/v1/support-tickets/{id}` | GET | Read ticket state |
| `/api/v1/support-tickets/{id}/approve` / `/reject` | POST | Staff-only approval, unreachable by the model |
| `/api/v1/cases/{student_id}` | GET / DELETE | Case history (privacy-filtered), including right-to-be-forgotten |
| `/api/v1/sessions/{run_id}` | GET | Full agent run state/trace |
| `/api/v1/memory/traces` | GET | Audit log of every memory/state operation |

## Running it

See `README.md` for the full walkthrough. In short:

```bash
cd agent-backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # set GROQ_API_KEY
python ingest.py
uvicorn main:app --reload
pytest -v   # 178 passed
```

## Known limitations

- High-impact topics (admissions, grades, discipline, fees, legal, medical) are refused by prompt instruction, not a code-level topic filter on the model's text output — the tool surface itself has no path to act on them either way. (`docs/agent-task-contract.md` condition H5, `docs/failure-catalogue.md` Failure 6)
- Memory is intentionally one prior turn per session, not a full conversation history.
- Authorization is a header-based simulation (`X-User-Role`), not real authentication.
- The corpus is a fixed, synthetic/public snapshot, not a live institutional integration.

Full list: `README.md`'s "Known Limitations" section.

## Security

No secrets are committed. Verified via `detect-secrets` across all tracked files and a full git-history grep across all branches for the project's real API key pattern — no real credential found anywhere. `.env` is gitignored and has never been tracked.
