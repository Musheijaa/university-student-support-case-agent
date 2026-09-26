from fastapi.testclient import TestClient

import main as main_module
from config import Settings
from tools import tickets
from tools.schemas import CreateSupportTicketInput

client = TestClient(main_module.app)


def _settings_with_db(tmp_path) -> Settings:
    return Settings(tickets_db_path=str(tmp_path / "tickets.db"))


def _create_ticket(tmp_path) -> str:
    result = tickets.create_support_ticket(
        CreateSupportTicketInput(category="IT Support", subject="s", description="d"),
        db_path=str(tmp_path / "tickets.db"),
    )
    return result.ticket_id


def test_staff_can_approve_a_pending_ticket(tmp_path, monkeypatch):
    settings = _settings_with_db(tmp_path)
    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    ticket_id = _create_ticket(tmp_path)

    response = client.post(
        f"/api/v1/support-tickets/{ticket_id}/approve", headers={"X-User-Role": "staff"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["status"] == "SUBMITTED"


def test_student_cannot_approve_a_ticket(tmp_path, monkeypatch):
    settings = _settings_with_db(tmp_path)
    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    ticket_id = _create_ticket(tmp_path)

    response = client.post(
        f"/api/v1/support-tickets/{ticket_id}/approve", headers={"X-User-Role": "student"}
    )

    assert response.status_code == 403


def test_missing_role_header_defaults_to_student_and_is_forbidden(tmp_path, monkeypatch):
    settings = _settings_with_db(tmp_path)
    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    ticket_id = _create_ticket(tmp_path)

    response = client.post(f"/api/v1/support-tickets/{ticket_id}/approve")

    assert response.status_code == 403


def test_staff_can_reject_a_pending_ticket(tmp_path, monkeypatch):
    settings = _settings_with_db(tmp_path)
    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    ticket_id = _create_ticket(tmp_path)

    response = client.post(
        f"/api/v1/support-tickets/{ticket_id}/reject", headers={"X-User-Role": "staff"}
    )

    assert response.status_code == 200
    assert response.json()["status"] == "REJECTED"


def test_approving_an_already_approved_ticket_fails(tmp_path, monkeypatch):
    settings = _settings_with_db(tmp_path)
    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    ticket_id = _create_ticket(tmp_path)
    client.post(f"/api/v1/support-tickets/{ticket_id}/approve", headers={"X-User-Role": "staff"})

    response = client.post(
        f"/api/v1/support-tickets/{ticket_id}/approve", headers={"X-User-Role": "staff"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is False
    assert "already" in body["error"].lower()


def test_approving_a_nonexistent_ticket_fails(tmp_path, monkeypatch):
    settings = _settings_with_db(tmp_path)
    monkeypatch.setattr(main_module, "get_settings", lambda: settings)

    response = client.post(
        "/api/v1/support-tickets/DRAFT-999/approve", headers={"X-User-Role": "staff"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is False
    assert "not found" in body["error"].lower()


def test_get_ticket_returns_current_state(tmp_path, monkeypatch):
    settings = _settings_with_db(tmp_path)
    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    ticket_id = _create_ticket(tmp_path)

    response = client.get(f"/api/v1/support-tickets/{ticket_id}")

    assert response.status_code == 200
    assert response.json()["status"] == "PENDING_APPROVAL"


def test_get_nonexistent_ticket_is_404(tmp_path, monkeypatch):
    settings = _settings_with_db(tmp_path)
    monkeypatch.setattr(main_module, "get_settings", lambda: settings)

    response = client.get("/api/v1/support-tickets/DRAFT-999")

    assert response.status_code == 404
