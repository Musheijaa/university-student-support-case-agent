"""Tests for Task 4: Privacy-preserving case history store and memory functions."""

import pytest

from agent.case_history import (
    APPROVED_FIELDS,
    CaseSummary,
    PrivacyViolationError,
    delete_case_history,
    get_case_history,
    save_case_summary,
)


def test_save_and_get_case_summary_approved_fields(tmp_path):
    """Verify that case summaries with approved Task 4 fields are saved and retrieved correctly."""
    db_path = str(tmp_path / "case_history.db")
    student_id = "2200705432"

    case1 = {
        "case_id": "CASE-001",
        "student_id": student_id,
        "category": "Timetable Query",
        "summary": "Student inquired about BSE4104 schedule and room venue.",
        "status": "completed",
        "action_taken": "Looked up timetable and provided dates and venue details.",
        "ticket_id": None,
    }
    saved = save_case_summary(case1, db_path=db_path)
    assert saved.case_id == "CASE-001"
    assert saved.student_id == student_id
    assert saved.category == "Timetable Query"

    # Retrieve history for the student
    history = get_case_history(student_id, db_path=db_path)
    assert len(history) == 1
    assert history[0].case_id == "CASE-001"
    assert history[0].summary == "Student inquired about BSE4104 schedule and room venue."


def test_reject_raw_chat_transcripts(tmp_path):
    """Task 4 Rule: Storing raw chat transcripts is strictly prohibited."""
    db_path = str(tmp_path / "case_history.db")
    forbidden_keys = [
        "raw_transcript",
        "chat_transcript",
        "transcript",
        "messages",
        "chat_history",
        "raw_chat",
        "conversation",
    ]

    for key in forbidden_keys:
        case_with_transcript = {
            "case_id": "CASE-RAW",
            "student_id": "2200701111",
            "category": "IT Support",
            "summary": "Portal login failed",
            "status": "completed",
            "action_taken": "Draft ticket created",
            key: [{"role": "user", "content": "Help me, here is my password..."}],
        }
        with pytest.raises(PrivacyViolationError) as exc_info:
            save_case_summary(case_with_transcript, db_path=db_path)
        assert "Raw chat transcripts are strictly forbidden" in str(exc_info.value)


def test_reject_personal_data_beyond_student_id(tmp_path):
    """Task 4 Rule: Storing personal data beyond student ID is strictly prohibited."""
    db_path = str(tmp_path / "case_history.db")
    forbidden_pii = [
        ("student_name", "John Doe"),
        ("email", "john.doe@students.mak.ac.ug"),
        ("phone", "+256700000000"),
        ("national_id", "CM98000000"),
        ("grades", {"BSE4104": "A"}),
        ("dob", "2002-05-14"),
    ]

    for pii_key, pii_val in forbidden_pii:
        case_with_pii = {
            "case_id": "CASE-PII",
            "student_id": "2200702222",
            "category": "General",
            "summary": "Inquiry about course registration",
            "status": "completed",
            "action_taken": "Provided registration guide",
            pii_key: pii_val,
        }
        with pytest.raises(PrivacyViolationError) as exc_info:
            save_case_summary(case_with_pii, db_path=db_path)
        assert "Personal data beyond student ID is strictly forbidden" in str(exc_info.value)


def test_reject_arbitrary_unapproved_fields(tmp_path):
    """Task 4 Rule: Reject arbitrary fields not on the approved schema."""
    db_path = str(tmp_path / "case_history.db")
    case_with_extra = {
        "case_id": "CASE-EXTRA",
        "student_id": "2200703333",
        "category": "General",
        "summary": "Question about fees",
        "status": "completed",
        "action_taken": "Provided fee schedule",
        "internal_server_metadata": "unauthorized debug blob",
    }
    with pytest.raises(PrivacyViolationError) as exc_info:
        save_case_summary(case_with_extra, db_path=db_path)
    assert "Unapproved field(s) detected" in str(exc_info.value)


def test_delete_case_history(tmp_path):
    """Verify delete_case_history(student_id) removes all records for the student."""
    db_path = str(tmp_path / "case_history.db")
    student_a = "STD-100"
    student_b = "STD-200"

    save_case_summary(
        {
            "case_id": "C1",
            "student_id": student_a,
            "category": "Cat1",
            "summary": "Sum1",
            "status": "completed",
            "action_taken": "Act1",
        },
        db_path=db_path,
    )
    save_case_summary(
        {
            "case_id": "C2",
            "student_id": student_a,
            "category": "Cat2",
            "summary": "Sum2",
            "status": "completed",
            "action_taken": "Act2",
        },
        db_path=db_path,
    )
    save_case_summary(
        {
            "case_id": "C3",
            "student_id": student_b,
            "category": "Cat3",
            "summary": "Sum3",
            "status": "completed",
            "action_taken": "Act3",
        },
        db_path=db_path,
    )

    assert len(get_case_history(student_a, db_path=db_path)) == 2
    assert len(get_case_history(student_b, db_path=db_path)) == 1

    # Delete student A's history
    deleted_count = delete_case_history(student_a, db_path=db_path)
    assert deleted_count == 2

    # Verify student A's history is empty, but student B's history is preserved
    assert len(get_case_history(student_a, db_path=db_path)) == 0
    assert len(get_case_history(student_b, db_path=db_path)) == 1
