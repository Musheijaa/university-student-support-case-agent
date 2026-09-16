"""FastAPI application entry point.

Exposes:
  GET  /health                    - liveness check, independent of the LLM provider
  POST /api/v1/student-support    - RAG-grounded student-support interaction (Week 3);
                                     retrieves evidence from the ingested corpus before
                                     calling Groq, and returns the sources used
"""

import logging

from fastapi import FastAPI, HTTPException, status

from config import get_settings
from llm.service import (
    LLMConfigurationError,
    LLMRequestError,
    get_student_support_response,
)
from schemas import (
    HealthResponse,
    SourceResponse,
    StudentSupportRequest,
    StudentSupportResponse,
)

logging.basicConfig(level=get_settings().log_level)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="University Student-Support Case Agent API",
    description=(
        "Week 3: retrieval-augmented student-support interaction, grounded in a "
        "controlled corpus of Makerere University policy documents. "
        "No tools, agents, or persistent memory are implemented yet."
    ),
    version="0.3.0",
)


@app.get("/health", response_model=HealthResponse, tags=["health"])
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@app.post(
    "/api/v1/student-support",
    response_model=StudentSupportResponse,
    tags=["student-support"],
)
def student_support(payload: StudentSupportRequest) -> StudentSupportResponse:
    try:
        result = get_student_support_response(payload.message)
    except LLMConfigurationError as exc:
        logger.error("LLM configuration error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The student-support assistant is not configured. Please contact an administrator.",
        ) from exc
    except LLMRequestError as exc:
        logger.error("LLM request error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    return StudentSupportResponse(
        response=result.response,
        prompt_version=result.prompt_version,
        model=result.model,
        sources=[
            SourceResponse(document_id=s.document_id, document=s.document, page=s.page)
            for s in result.sources
        ],
    )
