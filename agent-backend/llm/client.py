"""Thin wrapper around the Groq API.

This module isolates all direct dependency on the `groq` SDK so the rest
of the application (routes, service layer) never has to know how the
foundation model is actually invoked. Swapping providers later only
requires changes here.
"""

import logging
from typing import Any

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
        message = self.create_completion(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]
        )
        content = message.content
        if content is None or not content.strip():
            raise LLMRequestError("The model provider returned an empty response.")
        return content.strip()

    def create_completion(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | None = None,
    ):
        """Send a full message list (optionally with tool definitions) to Groq.

        Returns the raw assistant message object (`.content`, `.tool_calls`)
        so callers can implement a tool-calling loop. Kept separate from
        `generate()` so plain prompt/response callers (V1.0/V2.0/RAG) don't
        need to know about tool calling at all.
        """
        kwargs: dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "temperature": 0.2,
            "max_tokens": 1500,
        }
        if tools is not None:
            kwargs["tools"] = tools
        if tool_choice is not None:
            kwargs["tool_choice"] = tool_choice

        try:
            completion = self._client.chat.completions.create(**kwargs)
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

        return completion.choices[0].message
