# Agent Backend

A FastAPI backend for the University Student-Support Case Agent.
Week 2 added a foundation-model baseline (Groq + versioned prompts).
Week 3 adds retrieval-augmented generation (RAG): student questions are
answered from a controlled corpus of Makerere University policy
documents instead of the model's own memory, with sources returned
alongside every answer. See the root `README.md` for full setup
instructions.

## Layout

```text
agent-backend/
├── main.py           # FastAPI app: /health and /api/v1/student-support
├── config.py         # Environment-based settings (GROQ_API_KEY, RAG_TOP_K, ...)
├── schemas.py        # Pydantic request/response models and validation
├── ingest.py          # CLI: builds/updates the vector index from the corpus
├── chat_cli.py         # Interactive terminal client for manual testing
├── llm/
│   ├── prompts.py      # Versioned prompts: V1.0, V2.0 (Week 2), RAG-v1.0 (Week 3)
│   ├── client.py        # Thin wrapper around the Groq SDK
│   └── service.py       # Orchestrates retrieval (if RAG) + prompt + client call
├── rag/
│   ├── corpus_manifest.py  # Stable DOC### id -> filename/provenance mapping
│   ├── loader.py            # Extracts text per PDF page via pypdf
│   ├── chunker.py            # Splits page text into overlapping chunks
│   ├── embeddings.py          # Embedding model boundary (Chroma default ONNX MiniLM)
│   ├── vector_store.py         # Persistent ChromaDB wrapper: ingest + query
│   ├── retriever.py             # question -> ranked, score-filtered evidence chunks
│   └── context_builder.py        # retrieved chunks -> prompt evidence block + API sources
├── tests/            # Automated tests (LLM + embeddings boundary mocked/local; see
│                       tests/test_integration_groq.py for the real-API opt-in test)
├── requirements.txt
└── .env.example
```

Note the flat layout: `main.py`, `config.py`, and `schemas.py` sit
directly in `agent-backend/` rather than under a nested `src/` package,
and all internal imports (`from config import ...`, `from llm.service
import ...`, `from rag.retriever import ...`) are plain top-level
imports. Run `uvicorn`, `pytest`, and `ingest.py` from inside this
directory (see root `README.md`).

## Building the RAG index

The corpus lives in `../docs/makerereUniversityPolicyDocs/` (see
`../docs/corpus-source-register.md` for what's in it and known gaps).
Before `/api/v1/student-support` can answer anything meaningfully, the
vector index must be built once:

```bash
python ingest.py
```

This persists a Chroma collection to `data/chroma/` (gitignored -
regenerate it locally, don't commit it). Re-run it whenever the corpus
changes; it's safe to re-run (chunk IDs are deterministic, so
re-ingesting overwrites rather than duplicates). Without running this
first, the API still runs and responds - it just correctly reports "no
sufficiently relevant sources were found" for every question, since the
index is empty.

## Planned for later weeks

- Tools / function calling (case-status lookup, ticket creation)
- LangGraph-based agent orchestration
- Persistent memory of an active support case
- LangSmith observability/evaluation

None of the above is implemented yet by design — see
`../docs/prompt-specification.md`, `../docs/model-selection.md`, and
`../docs/corpus-source-register.md` for the reasoning behind the
current scope.
