# Agent Backend

A FastAPI backend for the University Student-Support Case Agent —
**v1.0.0**, the full 8-week build. Week 2 added a foundation-model
baseline (Groq + versioned prompts). Week 3 added retrieval-augmented
generation (RAG) over a controlled Makerere policy corpus, with cited
sources. Week 4 added explicit tool calling (`check_timetable`,
`create_support_ticket`), executed by the application (never the
model), with ticket submission requiring a separate human-approval
step. Week 5 added a bounded multi-step agent (plan→act→observe) over
the same tools, stopping at one of six terminal statuses. Week 6 added
bounded per-session memory and a privacy-filtered case-history store,
both unable to override the agent's budgets or approval boundary. Week
7 added a 39-scenario evaluation benchmark, documented guardrails, and
a failure catalogue. See the root `README.md` for full setup
instructions, the API table, and demo identities.

## Layout

```text
agent-backend/
├── main.py           # FastAPI app: all endpoints (see root README's API table)
├── config.py         # Environment-based settings, grouped by the week that introduced them
├── schemas.py        # Pydantic request/response models and validation
├── auth.py            # Minimal, explicit role header (X-User-Role) - not real authentication
├── ingest.py           # CLI: builds/updates the vector index from the corpus
├── chat_cli.py          # Interactive terminal client for manual testing
├── scripts/
│   └── capture_agent_trace.py  # Runs a real Groq request through the agent and validates the trace
├── llm/
│   ├── prompts.py      # Versioned prompts: V1.0, V2.0 (Wk2), RAG-v1.0 (Wk3), TOOLS-v1.0 (Wk4)
│   ├── client.py        # Thin wrapper around the Groq SDK, incl. tool-calling completions
│   └── service.py        # Orchestrates retrieval + the bounded tool-calling loop (single round-trip)
├── agent/
│   ├── contract.py      # AgentTaskContract: goal, approved tools, budgets (docs/agent-task-contract.md)
│   ├── orchestrator.py    # Week 5: the bounded plan->act->observe loop (POST /api/v1/agent/student-support)
│   ├── state.py            # Week 6: 6-stage lifecycle state model, terminal-sink enforcement
│   ├── state_store.py       # Week 6: SQLite-backed persistence for agent run state
│   ├── memory.py             # Week 6: bounded one-turn-per-session memory, TTL-based expiry
│   ├── case_history.py        # Week 6: privacy-filtered case-history store (rejects raw transcripts/PII)
│   └── traces.py               # Week 6/7: audit log of every memory/state read/write/delete
├── rag/
│   ├── corpus_manifest.py  # Stable DOC### id -> filename/provenance mapping
│   ├── loader.py            # Extracts text per PDF page via pypdf
│   ├── chunker.py            # Splits page text into overlapping chunks
│   ├── embeddings.py          # Embedding model boundary (Chroma default ONNX MiniLM)
│   ├── vector_store.py         # Persistent ChromaDB wrapper: ingest + query
│   ├── retriever.py             # question -> ranked, score-filtered evidence chunks
│   └── context_builder.py        # retrieved chunks -> prompt evidence block + API sources
├── tools/
│   ├── schemas.py       # Pydantic input/output models for every tool
│   ├── registry.py       # Allow-list, Groq tool-call JSON schemas, dispatch_tool_call()
│   ├── timetable.py        # check_timetable - reads data/timetable/timetable.json
│   └── tickets.py            # create_support_ticket + SQLite draft/approve/reject store
├── data/
│   ├── timetable/timetable.json  # Synthetic, committed (see file's own _disclaimer field)
│   ├── chroma/                    # RAG vector index, gitignored - rebuild with ingest.py
│   └── *.db                        # Tickets/sessions/state/case-history/traces stores, gitignored runtime state
├── tests/            # Automated tests (LLM/embeddings/Groq boundary mocked/local; see
│                       tests/test_integration_groq.py for the real-API opt-in test)
├── requirements.txt
└── .env.example
```

Note the flat layout: `main.py`, `config.py`, `schemas.py`, and `auth.py`
sit directly in `agent-backend/` rather than under a nested `src/`
package, and all internal imports (`from config import ...`, `from
llm.service import ...`, `from tools.registry import ...`) are plain
top-level imports. Run `uvicorn`, `pytest`, and `ingest.py` from inside
this directory (see root `README.md`).

## Building the RAG index

The corpus lives in `../docs/makerereUniversityPolicyDocs/` (see
`../docs/corpus-source-register.md` for what's in it and known gaps).
Before `/api/v1/student-support` can answer knowledge questions
meaningfully, the vector index must be built once:

```bash
python ingest.py
```

This persists a Chroma collection to `data/chroma/` (gitignored -
regenerate it locally, don't commit it). Re-run it whenever the corpus
changes; it's safe to re-run (chunk IDs are deterministic, so
re-ingesting overwrites rather than duplicates). Without running this
first, the API still runs and responds - it just correctly reports "no
sufficiently relevant sources were found" for every knowledge question,
since the index is empty. Tool calling (timetable/tickets) works
independently of the RAG index.

## Tools and authorization (Week 4)

See `../docs/tool-catalogue.md` for full schemas and failure behavior.
In short: pass `X-User-Role: staff` to approve/reject a ticket (default
is `student` if the header is omitted); this is an explicit, bounded
role simulation for this academic phase, not real authentication.

```bash
# Ask something that triggers a tool, as a student (the default):
curl -X POST http://127.0.0.1:8000/api/v1/student-support \
  -H "Content-Type: application/json" \
  -d '{"message": "When is BSE4104 scheduled?"}'

# Approve a resulting draft ticket, as staff:
curl -X POST http://127.0.0.1:8000/api/v1/support-tickets/DRAFT-001/approve \
  -H "X-User-Role: staff"
```

## The bounded agent (Week 5-6)

`POST /api/v1/agent/student-support` is the full system: retrieval +
tools + a plan→act→observe loop bounded by `AGENT_MAX_ITERATIONS` and
`MAX_TOOL_CALLS`, stopping at one of six terminal statuses (see
`docs/agent-task-contract.md`). Pass `X-Session-Id` and `X-Memory: on`
to enable one-prior-turn memory for that session (`docs/memory-design.md`).
The approval boundary is unchanged from Week 4: `approve_ticket` and
`reject_ticket` are not registered as tools, so neither the agent nor
memory can ever reach them.

## Observability and tracing

Every agent run is traced end to end (model parameters, prompt version
and hash, retrieved chunks with relevance scores, tool arguments and
responses, per-iteration latency, error codes, terminal status). See
`../docs/observability.md`.

```bash
LOG_FORMAT=json uvicorn main:app             # one JSON log line per agent step
curl -H "X-User-Role: staff" \
  http://127.0.0.1:8000/api/v1/agent/traces/<run_id>   # full trace for one run (staff only)
python scripts/capture_observability_traces.py        # regenerate ../evidence/traces/observability/
```

## Known limitations

See the root `README.md`'s "Known Limitations" section and
`docs/failure-catalogue.md` for the full, honest list - most notably,
high-impact topics are currently refused by prompt instruction rather
than a code-level topic filter on the model's text output (the tool
surface itself has no code path to act on them either way).
