"""Optional real-API smoke test.

This test makes a genuine call to the Groq API and therefore requires a
valid GROQ_API_KEY. It is skipped (not faked, not marked as passing) when
no key is configured, so the rest of the suite stays free to run without
network access or paid API usage.

Run explicitly with a configured .env / environment to verify real
end-to-end connectivity:

    pytest tests/test_integration_groq.py -v
"""

import pytest

from config import get_settings
from llm.service import get_student_support_response

settings = get_settings()


@pytest.mark.skipif(
    not settings.groq_configured,
    reason="BLOCKED: GROQ_API_KEY is not configured.",
)
def test_real_groq_call_returns_a_response():
    result = get_student_support_response("What is the process for changing my major?")
    assert result.response
    assert result.prompt_version == settings.active_prompt_version
    assert result.model == settings.groq_model
