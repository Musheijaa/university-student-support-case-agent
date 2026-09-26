import sqlite3

import pytest
from pydantic import ValidationError

from tools import tickets
from tools.schemas import CreateSupportTicketInput


def _db(tmp_path):
    return str(tmp_path / "tickets.db")


def test_create_ticket_returns_draft_pending_approval(tmp_path):
    result = tickets.create_support_ticket(
        CreateSupportTicketInput(
            category="IT Support", subject="Portal login broken", description="Cannot log in."
        ),
        db_path=_db(tmp_path),
    )

    assert result.success is True
    assert result.ticket_id.startswith("DRAFT-")
    assert result.status == "PENDING_APPROVAL"


def test_ticket_ids_increment(tmp_path):
    db_path = _db(tmp_path)
    input_data = CreateSupportTicketInput(category="Academic", subject="s", description="d")

    first = tickets.create_support_ticket(input_data, db_path=db_path)
    second = tickets.create_support_ticket(input_data, db_path=db_path)

    assert first.ticket_id != second.ticket_id


def test_missing_category_is_a_validation_error():
    with pytest.raises(ValidationError):
        CreateSupportTicketInput(subject="s", description="d")


def test_missing_subject_is_a_validation_error():
    with pytest.raises(ValidationError):
        CreateSupportTicketInput(category="IT Support", description="d")


def test_missing_description_is_a_validation_error():
    with pytest.raises(ValidationError):
        CreateSupportTicketInput(category="IT Support", subject="s")


def test_invalid_category_is_a_validation_error():
    with pytest.raises(ValidationError):
        CreateSupportTicketInput(category="Not A Real Category", subject="s", description="d")


def test_blank_subject_is_a_validation_error():
    with pytest.raises(ValidationError):
        CreateSupportTicketInput(category="IT Support", subject="   ", description="d")


def test_approve_pending_ticket_transitions_to_submitted(tmp_path):
    db_path = _db(tmp_path)
    created = tickets.create_support_ticket(
        CreateSupportTicketInput(category="IT Support", subject="s", description="d"),
        db_path=db_path,
    )

    result = tickets.approve_ticket(created.ticket_id, db_path=db_path)

    assert result == {"success": True, "ticket_id": created.ticket_id, "status": "SUBMITTED"}
    assert tickets.get_ticket(created.ticket_id, db_path=db_path).status == "SUBMITTED"


def test_reject_pending_ticket_transitions_to_rejected(tmp_path):
    db_path = _db(tmp_path)
    created = tickets.create_support_ticket(
        CreateSupportTicketInput(category="IT Support", subject="s", description="d"),
        db_path=db_path,
    )

    result = tickets.reject_ticket(created.ticket_id, db_path=db_path)

    assert result["success"] is True
    assert result["status"] == "REJECTED"


def test_approve_nonexistent_ticket_fails_safely(tmp_path):
    result = tickets.approve_ticket("DRAFT-999", db_path=_db(tmp_path))
    assert result["success"] is False
    assert "not found" in result["error"].lower()


def test_approve_already_approved_ticket_fails_safely(tmp_path):
    db_path = _db(tmp_path)
    created = tickets.create_support_ticket(
        CreateSupportTicketInput(category="IT Support", subject="s", description="d"),
        db_path=db_path,
    )
    tickets.approve_ticket(created.ticket_id, db_path=db_path)

    result = tickets.approve_ticket(created.ticket_id, db_path=db_path)

    assert result["success"] is False
    assert "already" in result["error"].lower()


def test_reject_already_rejected_ticket_fails_safely(tmp_path):
    db_path = _db(tmp_path)
    created = tickets.create_support_ticket(
        CreateSupportTicketInput(category="IT Support", subject="s", description="d"),
        db_path=db_path,
    )
    tickets.reject_ticket(created.ticket_id, db_path=db_path)

    result = tickets.reject_ticket(created.ticket_id, db_path=db_path)

    assert result["success"] is False


def test_get_nonexistent_ticket_returns_none(tmp_path):
    assert tickets.get_ticket("DRAFT-999", db_path=_db(tmp_path)) is None


def test_service_unavailable_raises_rather_than_fabricating(monkeypatch, tmp_path):
    def broken_connect(_db_path):
        raise sqlite3.OperationalError("disk I/O error")

    monkeypatch.setattr(tickets, "_connect", broken_connect)

    with pytest.raises(sqlite3.OperationalError):
        tickets.create_support_ticket(
            CreateSupportTicketInput(category="IT Support", subject="s", description="d"),
            db_path=_db(tmp_path),
        )
