import json

import pytest

from auth import Actor
from tools import registry
from tools.registry import ToolContext, dispatch_tool_call
from tools.schemas import CheckTimetableOutput


def _ctx(tmp_path, sessions=None):
    data_path = tmp_path / "timetable.json"
    data_path.write_text(json.dumps({"sessions": sessions or []}))
    return ToolContext(timetable_data_path=str(data_path), tickets_db_path=str(tmp_path / "t.db"))


STUDENT = Actor(role="student", user_id="s1")
STAFF = Actor(role="staff", user_id="staff1")
GUEST = Actor(role="guest", user_id="anon")


def test_unregistered_tool_name_is_rejected(tmp_path):
    result = dispatch_tool_call("delete_database", "{}", STUDENT, _ctx(tmp_path))
    assert result["success"] is False
    assert "not available" in result["error"]


def test_malformed_json_arguments_are_rejected(tmp_path):
    result = dispatch_tool_call("check_timetable", "{not valid json", STUDENT, _ctx(tmp_path))
    assert result["success"] is False
    assert "JSON" in result["error"]


def test_missing_required_argument_is_rejected(tmp_path):
    result = dispatch_tool_call("check_timetable", "{}", STUDENT, _ctx(tmp_path))
    assert result["success"] is False
    assert "Invalid input" in result["error"]


def test_guest_is_unauthorized_for_check_timetable(tmp_path):
    result = dispatch_tool_call(
        "check_timetable", json.dumps({"course_code": "BSE4104"}), GUEST, _ctx(tmp_path)
    )
    assert result["success"] is False
    assert "not authorized" in result["error"]


def test_guest_is_unauthorized_for_create_support_ticket(tmp_path):
    args = json.dumps({"category": "IT Support", "subject": "s", "description": "d"})
    result = dispatch_tool_call("create_support_ticket", args, GUEST, _ctx(tmp_path))
    assert result["success"] is False
    assert "not authorized" in result["error"]


def test_student_can_call_check_timetable(tmp_path):
    ctx = _ctx(
        tmp_path,
        sessions=[{"course_code": "BSE4104", "date": "2026-09-24", "start_time": "10:00", "end_time": "12:00", "venue": "Room 204"}],
    )
    result = dispatch_tool_call(
        "check_timetable", json.dumps({"course_code": "BSE4104"}), STUDENT, ctx
    )
    assert result["success"] is True
    assert result["sessions"][0]["venue"] == "Room 204"


def test_staff_can_also_call_check_timetable(tmp_path):
    result = dispatch_tool_call(
        "check_timetable", json.dumps({"course_code": "BSE4104"}), STAFF, _ctx(tmp_path)
    )
    assert result["success"] is False  # no data, but authorized to ask


def test_timetable_service_unavailable_is_caught_safely(tmp_path):
    ctx = ToolContext(
        timetable_data_path=str(tmp_path / "missing.json"), tickets_db_path=str(tmp_path / "t.db")
    )
    result = dispatch_tool_call(
        "check_timetable", json.dumps({"course_code": "BSE4104"}), STUDENT, ctx
    )
    assert result["success"] is False
    assert "temporarily unavailable" in result["error"]


def test_unexpected_tool_response_is_caught_safely(tmp_path, monkeypatch):
    def bad_executor(input_data, ctx):
        return {"this": "does not match CheckTimetableOutput at all"}

    monkeypatch.setitem(
        registry.TOOL_REGISTRY,
        "check_timetable",
        registry.ToolSpec(
            input_model=registry.CheckTimetableInput,
            output_model=CheckTimetableOutput,
            allowed_roles=frozenset({"student", "staff"}),
            executor=bad_executor,
        ),
    )

    result = dispatch_tool_call(
        "check_timetable", json.dumps({"course_code": "BSE4104"}), STUDENT, _ctx(tmp_path)
    )
    assert result["success"] is False
    assert "unexpected response" in result["error"]


def test_create_support_ticket_end_to_end_via_dispatch(tmp_path):
    args = json.dumps({"category": "IT Support", "subject": "Portal down", "description": "Can't log in"})
    result = dispatch_tool_call("create_support_ticket", args, STUDENT, _ctx(tmp_path))

    assert result["success"] is True
    assert result["status"] == "PENDING_APPROVAL"
    assert result["ticket_id"].startswith("DRAFT-")
