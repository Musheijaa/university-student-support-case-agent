# Agent Backend

Week 2 implementation: a FastAPI baseline that sends student questions
to an external foundation model (Groq) using a versioned prompt, and
returns a structured response. See the root `README.md` for full setup
instructions.

## Layout

```text
agent-backend/
├── main.py       # FastAPI app: /health and /api/v1/student-support
├── config.py     # Environment-based settings (GROQ_API_KEY, GROQ_MODEL, ...)
├── schemas.py    # Pydantic request/response models and validation
├── llm/
│   ├── prompts.py  # Versioned prompt templates (V1.0, V2.0)
│   ├── client.py   # Thin wrapper around the Groq SDK
│   └── service.py  # Orchestrates prompt selection + client call
├── tests/        # Automated tests (LLM boundary mocked; see tests/test_integration_groq.py for the real-API opt-in test)
├── requirements.txt
└── .env.example
```

Note the flat layout: `main.py`, `config.py`, and `schemas.py` sit
directly in `agent-backend/` rather than under a nested `src/` package,
and all internal imports (`from config import ...`, `from llm.service
import ...`) are plain top-level imports. Run `uvicorn` and `pytest`
from inside this directory (see root `README.md`).

## Planned for later weeks

- Retrieval over approved university/course documents (Week 3, RAG)
- Tools / function calling (case-status lookup, ticket creation)
- LangGraph-based agent orchestration
- Persistent memory of an active support case
- LangSmith observability/evaluation

None of the above is implemented yet by design — see
`../docs/prompt-specification.md` and `../docs/model-selection.md` for
the reasoning behind the current scope.
