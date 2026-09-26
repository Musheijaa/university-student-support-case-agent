"""check_timetable tool: read-only lookup against synthetic timetable data.

This tool never asks the LLM to invent a schedule. It reads
`data/timetable/timetable.json` (clearly marked as synthetic/team-created,
not an official university feed) and returns only what is actually
there.
"""

import json

from tools.schemas import CheckTimetableInput, CheckTimetableOutput, TimetableSession


def _read_timetable_file(path: str) -> list[dict]:
    """Isolated so tests can monkeypatch this to simulate the service being unavailable."""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return data["sessions"]


def check_timetable(input_data: CheckTimetableInput, data_path: str) -> CheckTimetableOutput:
    sessions_raw = _read_timetable_file(data_path)

    matches = [
        TimetableSession(
            date=s["date"], start_time=s["start_time"], end_time=s["end_time"], venue=s["venue"]
        )
        for s in sessions_raw
        if s.get("course_code", "").upper() == input_data.course_code
        and (input_data.date is None or s.get("date") == input_data.date)
    ]

    if not matches:
        return CheckTimetableOutput(
            success=False,
            course_code=input_data.course_code,
            error=f"No timetable information found for {input_data.course_code}"
            + (f" on {input_data.date}" if input_data.date else ""),
        )

    return CheckTimetableOutput(
        success=True, course_code=input_data.course_code, sessions=matches
    )
