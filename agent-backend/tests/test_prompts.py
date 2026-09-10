import pytest

from llm.prompts import PROMPT_V1, PROMPT_V2, get_prompt


def test_prompt_v1_version_and_content():
    assert PROMPT_V1.version == "v1.0"
    assert "student-support assistant" in PROMPT_V1.system_prompt
    assert "do not have enough information" in PROMPT_V1.system_prompt


def test_prompt_v2_has_explicit_sections():
    for section in ("ROLE", "PRIMARY TASK", "CONSTRAINTS", "RESPONSE FORMAT", "FAILURE BEHAVIOR"):
        assert section in PROMPT_V2.system_prompt


def test_prompt_v2_forbids_high_impact_claims():
    for phrase in (
        "Never make admissions decisions",
        "Never make grading decisions",
        "Never make disciplinary decisions",
        "Never claim to have created a support ticket",
    ):
        assert phrase in PROMPT_V2.system_prompt


def test_get_prompt_returns_requested_version():
    assert get_prompt("v1.0") is PROMPT_V1
    assert get_prompt("v2.0") is PROMPT_V2


def test_get_prompt_rejects_unknown_version():
    with pytest.raises(ValueError):
        get_prompt("v99.0")


def test_build_user_prompt_includes_student_message():
    user_prompt = PROMPT_V2.build_user_prompt("Where do I submit a leave-of-absence form?")
    assert "Where do I submit a leave-of-absence form?" in user_prompt
