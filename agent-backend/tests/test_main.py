"""API-level tests for the Week 2 baseline.

These tests never call the real Groq API: `main.get_student_support_response`
is monkeypatched in every test that exercises the /api/v1/student-support
route, so the suite runs deterministically without GROQ_API_KEY configured.
"""

import pytest
from fastapi.testclient import TestClient

import main as main_module
from llm.service import LLMConfigurationError, LLMRequestError, StudentSupportResult

client = TestClient(main_module.app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_valid_student_message(monkeypatch):
    fake_result = StudentSupportResult(
        response="1. Direct answer...\n2. Limitation...\n3. Next step...",
        prompt_version="v2.0",
        model="openai/gpt-oss-20b",
    )
    monkeypatch.setattr(main_module, "get_student_support_response", lambda message: fake_result)

    response = client.post(
        "/api/v1/student-support",
        json={"message": "How does course registration work?"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["response"] == fake_result.response
    assert body["prompt_version"] == "v2.0"
    assert body["model"] == "openai/gpt-oss-20b"


def test_missing_message_field():
    response = client.post("/api/v1/student-support", json={})
    assert response.status_code == 422


def test_empty_message():
    response = client.post("/api/v1/student-support", json={"message": ""})
    assert response.status_code == 422


def test_whitespace_only_message():
    response = client.post("/api/v1/student-support", json={"message": "     "})
    assert response.status_code == 422


def test_excessively_long_message():
    long_message = "a" * 5000
    response = client.post("/api/v1/student-support", json={"message": long_message})
    assert response.status_code == 422


def test_malformed_request_body():
    response = client.post(
        "/api/v1/student-support",
        content="not json",
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 422


def test_missing_api_configuration(monkeypatch):
    def raise_configuration_error(message):
        raise LLMConfigurationError("GROQ_API_KEY is not configured.")

    monkeypatch.setattr(main_module, "get_student_support_response", raise_configuration_error)

    response = client.post(
        "/api/v1/student-support",
        json={"message": "Is the campus library open on weekends?"},
    )

    assert response.status_code == 503
    # Ensure the internal configuration detail is not echoed back verbatim.
    assert "GROQ_API_KEY" not in response.text


def test_llm_request_error_returns_bad_gateway(monkeypatch):
    def raise_request_error(message):
        raise LLMRequestError("The model provider timed out. Please try again.")

    monkeypatch.setattr(main_module, "get_student_support_response", raise_request_error)

    response = client.post(
        "/api/v1/student-support",
        json={"message": "Is the campus library open on weekends?"},
    )

    assert response.status_code == 502
