"""Thin wrapper around the Groq API.

This module isolates all direct dependency on the `groq` SDK so the rest
of the application (routes, service layer) never has to know how the
foundation model is actually invoked. Swapping providers later only
requires changes here.
"""

import logging
from typing import Any

import groq

from observability import error_codes

logger = logging.getLogger(__name__)


class LLMConfigurationError(Exception):
    """Raised when the LLM provider is not configured (e.g. missing API key)."""


class LLMRequestError(Exception):
    """Raised when the external model call fails or returns something unusable.

    `code` is a stable identifier from observability/error_codes.py for
    traces and logs; the message stays safe to show to a student.
    """

    def __init__(self, message: str, code: str = error_codes.LLM_API_ERROR):
        super().__init__(message)
        self.code = code


class GroqClient:
    """Minimal synchronous client for chat-completion calls against Groq."""

    def __init__(
        self,
        api_key: str,
        model: str,
        timeout_seconds: float = 20.0,
        temperature: float = 0.2,
        max_tokens: int = 1500,
        max_retries: int = 2,
    ):
        if not api_key or not api_key.strip():
            raise LLMConfigurationError("GROQ_API_KEY is not configured.")
        self._model = model
        self._temperature = temperature
        self._max_tokens = max_tokens
        self._client = groq.Groq(api_key=api_key, timeout=timeout_seconds, max_retries=max_retries)
        # Metadata about the most recent create_completion call (provider
        # request id, finish reason, token usage), for tracing. None until
        # a call returns.
        self.last_call: dict[str, Any] | None = None

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
            raise LLMRequestError(
                "The model provider returned an empty response.", code=error_codes.LLM_EMPTY_RESPONSE
            )
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
            "temperature": self._temperature,
            "max_tokens": self._max_tokens,
        }
        if tools is not None:
            kwargs["tools"] = tools
        if tool_choice is not None:
            kwargs["tool_choice"] = tool_choice

        self.last_call = None
        try:
            completion = self._client.chat.completions.create(**kwargs)
        except groq.APITimeoutError as exc:
            logger.warning("Groq API request timed out.")
            raise LLMRequestError(
                "The model provider timed out. Please try again.", code=error_codes.LLM_TIMEOUT
            ) from exc
        except groq.APIConnectionError as exc:
            logger.warning("Groq API connection error: %s", type(exc).__name__)
            raise LLMRequestError(
                "Could not reach the model provider. Please try again shortly.",
                code=error_codes.LLM_CONNECTION_ERROR,
            ) from exc
        except groq.RateLimitError as exc:
            logger.warning("Groq API rate limit hit.")
            raise LLMRequestError(
                "The model provider is rate-limiting requests. Please try again shortly.",
                code=error_codes.LLM_RATE_LIMITED,
            ) from exc
        except groq.APIStatusError as exc:
            logger.warning("Groq API returned an error status: %s", exc.status_code)
            raise LLMRequestError(
                "The model provider returned an error.",
                code=error_codes.llm_http_error(exc.status_code),
            ) from exc
        except groq.APIError as exc:
            logger.warning("Unexpected Groq API error: %s", type(exc).__name__)
            raise LLMRequestError("The model provider returned an unexpected error.") from exc

        usage = getattr(completion, "usage", None)
        self.last_call = {
            "provider_request_id": getattr(completion, "id", None),
            "finish_reason": completion.choices[0].finish_reason if completion.choices else None,
            "usage": {
                "prompt_tokens": usage.prompt_tokens,
                "completion_tokens": usage.completion_tokens,
                "total_tokens": usage.total_tokens,
            }
            if usage is not None
            else None,
        }

        if not completion.choices:
            raise LLMRequestError(
                "The model provider returned an empty response.", code=error_codes.LLM_EMPTY_RESPONSE
            )

        return completion.choices[0].message
