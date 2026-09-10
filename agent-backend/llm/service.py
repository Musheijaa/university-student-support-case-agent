"""LLM service: orchestrates prompt selection and the Groq client.

This is the seam the API route talks to. It knows nothing about HTTP;
it just turns a student message into a model reply plus metadata about
which prompt version and model produced it. Week 3 (RAG) is expected to
slot in here, ahead of the client call, without changing the route.
"""

from dataclasses import dataclass

from config import Settings, get_settings
from llm.client import GroqClient, LLMConfigurationError, LLMRequestError
from llm.prompts import get_prompt

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


def get_student_support_response(
    student_message: str, settings: Settings | None = None
) -> StudentSupportResult:
    """Generate a baseline student-support reply for the given message.

    Raises LLMConfigurationError if the provider is not configured, and
    LLMRequestError if the provider call fails. Callers (the API route)
    are responsible for translating these into safe HTTP responses.
    """
    settings = settings or get_settings()

    prompt = get_prompt(settings.active_prompt_version)
    client = GroqClient(api_key=settings.groq_api_key, model=settings.groq_model)

    user_prompt = prompt.build_user_prompt(student_message)
    reply = client.generate(system_prompt=prompt.system_prompt, user_prompt=user_prompt)

    return StudentSupportResult(
        response=reply,
        prompt_version=prompt.version,
        model=settings.groq_model,
    )
