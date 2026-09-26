# Agent Backend

A FastAPI backend for the University Student-Support Case Agent.
Week 2 added a foundation-model baseline (Groq + versioned prompts).
Week 3 added retrieval-augmented generation (RAG): questions are
answered from a controlled corpus of Makerere University policy
documents, with sources returned alongside every answer. Week 4 adds
explicit tool calling: the model can request `check_timetable` or
`create_support_ticket`, executed by the application (never by the
model) after validation and authorization, with ticket submission
requiring a separate human approval step. See the root `README.md` for
full setup instructions.

## Layout

```text
agent-backend/
├── main.py           # FastAPI app: /health, /api/v1/student-support, /api/v1/support-tickets/*
├── config.py         # Environment-based settings (GROQ_API_KEY, RAG_TOP_K, MAX_TOOL_CALLS, ...)
├── schemas.py        # Pydantic request/response models and validation
├── auth.py            # Minimal, explicit role header (X-User-Role) - not real authentication
├── ingest.py           # CLI: builds/updates the vector index from the corpus
├── chat_cli.py          # Interactive terminal client for manual testing
├── llm/
│   ├── prompts.py      # Versioned prompts: V1.0, V2.0 (Wk2), RAG-v1.0 (Wk3), TOOLS-v1.0 (Wk4)
│   ├── client.py        # Thin wrapper around the Groq SDK, incl. tool-calling completions
│   └── service.py        # Orchestrates retrieval + (if enabled) the bounded tool-calling loop
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
│   └── tickets.db                  # Ticket store, gitignored runtime state
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

## Planned for later weeks

- LangGraph-based agent orchestration
- Persistent memory of an active support case
- LangSmith observability/evaluation

None of the above is implemented yet by design — see
`../docs/architecture.md`, `../docs/tool-catalogue.md`,
`../docs/prompt-specification.md`, `../docs/model-selection.md`, and
`../docs/corpus-source-register.md` for the reasoning behind the
current scope.
