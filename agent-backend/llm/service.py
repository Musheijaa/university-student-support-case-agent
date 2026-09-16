"""LLM service: orchestrates retrieval, prompt selection, and the Groq client.

This is the seam the API route talks to. It knows nothing about HTTP;
it just turns a student message into a grounded model reply plus the
sources that reply is grounded in. Week 3 adds a retrieval step ahead
of the client call: when the active prompt version is a RAG version,
the student's message is used to retrieve relevant evidence from the
vector store, which is passed to the model explicitly instead of the
model answering from its own training knowledge.
"""

from dataclasses import dataclass, field

from config import Settings, get_settings
from llm.client import GroqClient, LLMConfigurationError, LLMRequestError
from llm.prompts import build_rag_user_message, get_prompt
from rag.context_builder import Source, build_evidence_block, build_sources
from rag.retriever import retrieve
from rag.vector_store import get_vector_store

__all__ = [
    "LLMConfigurationError",
    "LLMRequestError",
    "StudentSupportResult",
    "get_student_support_response",
]


@dataclass(frozen=True)
class StudentSupportResult:
    response: str
    prompt_version: str
    model: str
    sources: list[Source] = field(default_factory=list)


def get_student_support_response(
    student_message: str, settings: Settings | None = None
) -> StudentSupportResult:
    """Generate a student-support reply for the given message.

    Raises LLMConfigurationError if the provider is not configured, and
    LLMRequestError if the provider call fails. Callers (the API route)
    are responsible for translating these into safe HTTP responses.
    """
    settings = settings or get_settings()

    prompt = get_prompt(settings.active_prompt_version)
    client = GroqClient(api_key=settings.groq_api_key, model=settings.groq_model)

    sources: list[Source] = []
    if prompt.version.startswith("rag-"):
        vector_store = get_vector_store(
            persist_directory=settings.chroma_persist_directory,
            collection_name=settings.rag_collection_name,
        )
        retrieved_chunks = retrieve(
            vector_store=vector_store,
            question=student_message,
            top_k=settings.rag_top_k,
            min_score=settings.rag_min_score,
        )
        evidence_block = build_evidence_block(retrieved_chunks)
        sources = build_sources(retrieved_chunks)
        user_prompt = prompt.build_user_prompt(
            build_rag_user_message(question=student_message, evidence_block=evidence_block)
        )
    else:
        user_prompt = prompt.build_user_prompt(student_message)

    reply = client.generate(system_prompt=prompt.system_prompt, user_prompt=user_prompt)

    return StudentSupportResult(
        response=reply,
        prompt_version=prompt.version,
        model=settings.groq_model,
        sources=sources,
    )
