"""Thin wrapper around the Groq API.

This module isolates all direct dependency on the `groq` SDK so the rest
of the application (routes, service layer) never has to know how the
foundation model is actually invoked. Swapping providers later only
requires changes here.
"""

import logging

import groq

logger = logging.getLogger(__name__)


class LLMConfigurationError(Exception):
    """Raised when the LLM provider is not configured (e.g. missing API key)."""


class LLMRequestError(Exception):
    """Raised when the external model call fails or returns something unusable."""


class GroqClient:
    """Minimal synchronous client for chat-completion calls against Groq."""

    def __init__(self, api_key: str, model: str, timeout_seconds: float = 20.0):
        if not api_key or not api_key.strip():
            raise LLMConfigurationError("GROQ_API_KEY is not configured.")
        self._model = model
        self._client = groq.Groq(api_key=api_key, timeout=timeout_seconds)

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Send a system/user message pair to Groq and return the reply text."""
        try:
            completion = self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.2,
                max_tokens=800,
            )
        except groq.APITimeoutError as exc:
            logger.warning("Groq API request timed out.")
            raise LLMRequestError("The model provider timed out. Please try again.") from exc
        except groq.APIConnectionError as exc:
            logger.warning("Groq API connection error: %s", type(exc).__name__)
            raise LLMRequestError(
                "Could not reach the model provider. Please try again shortly."
            ) from exc
        except groq.RateLimitError as exc:
            logger.warning("Groq API rate limit hit.")
            raise LLMRequestError(
                "The model provider is rate-limiting requests. Please try again shortly."
            ) from exc
        except groq.APIStatusError as exc:
            logger.warning("Groq API returned an error status: %s", exc.status_code)
            raise LLMRequestError("The model provider returned an error.") from exc
        except groq.APIError as exc:
            logger.warning("Unexpected Groq API error: %s", type(exc).__name__)
            raise LLMRequestError("The model provider returned an unexpected error.") from exc

        if not completion.choices:
            raise LLMRequestError("The model provider returned an empty response.")

        content = completion.choices[0].message.content
        if content is None or not content.strip():
            raise LLMRequestError("The model provider returned an empty response.")

        return content.strip()
