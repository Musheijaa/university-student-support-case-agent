import pytest

from llm.client import GroqClient, LLMConfigurationError


def test_groq_client_requires_api_key():
    with pytest.raises(LLMConfigurationError):
        GroqClient(api_key="", model="openai/gpt-oss-20b")


def test_groq_client_rejects_whitespace_only_api_key():
    with pytest.raises(LLMConfigurationError):
        GroqClient(api_key="   ", model="openai/gpt-oss-20b")
