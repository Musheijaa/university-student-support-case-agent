import json

import pytest
from pydantic import ValidationError

from tools import timetable
from tools.schemas import CheckTimetableInput


def _write_timetable(path, sessions):
    path.write_text(json.dumps({"sessions": sessions}))


def test_valid_request_returns_matching_sessions(tmp_path):
    data_path = tmp_path / "timetable.json"
    _write_timetable(
        data_path,
        [{"course_code": "BSE4104", "date": "2026-09-24", "start_time": "10:00", "end_time": "12:00", "venue": "Room 204"}],
    )

    result = timetable.check_timetable(CheckTimetableInput(course_code="BSE4104"), str(data_path))

    assert result.success is True
    assert result.course_code == "BSE4104"
    assert len(result.sessions) == 1
    assert result.sessions[0].venue == "Room 204"


def test_missing_course_code_is_a_validation_error():
    with pytest.raises(ValidationError):
        CheckTimetableInput()


def test_empty_course_code_is_a_validation_error():
    with pytest.raises(ValidationError):
        CheckTimetableInput(course_code="")


def test_invalid_course_code_format_is_a_validation_error():
    with pytest.raises(ValidationError):
        CheckTimetableInput(course_code="not a course code!!")


def test_invalid_date_is_a_validation_error():
    with pytest.raises(ValidationError):
        CheckTimetableInput(course_code="BSE4104", date="24th September")


def test_course_not_found_returns_safe_failure_not_a_guess(tmp_path):
    data_path = tmp_path / "timetable.json"
    _write_timetable(data_path, [{"course_code": "CSC3103", "date": "2026-09-25", "start_time": "08:00", "end_time": "10:00", "venue": "Hall 3"}])

    result = timetable.check_timetable(CheckTimetableInput(course_code="BSE4104"), str(data_path))

    assert result.success is False
    assert result.sessions == []
    assert "BSE4104" in result.error


def test_date_filter_narrows_to_one_session(tmp_path):
    data_path = tmp_path / "timetable.json"
    _write_timetable(
        data_path,
        [
            {"course_code": "BSE4104", "date": "2026-09-24", "start_time": "10:00", "end_time": "12:00", "venue": "Room 204"},
            {"course_code": "BSE4104", "date": "2026-10-01", "start_time": "10:00", "end_time": "12:00", "venue": "Room 204"},
        ],
    )

    result = timetable.check_timetable(
        CheckTimetableInput(course_code="BSE4104", date="2026-10-01"), str(data_path)
    )

    assert len(result.sessions) == 1
    assert result.sessions[0].date == "2026-10-01"


def test_service_unavailable_raises_rather_than_fabricating(tmp_path):
    missing_path = tmp_path / "does-not-exist.json"
    with pytest.raises(OSError):
        timetable.check_timetable(CheckTimetableInput(course_code="BSE4104"), str(missing_path))
