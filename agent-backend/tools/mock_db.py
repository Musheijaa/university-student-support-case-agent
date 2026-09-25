"""Simulated state store for student support cases, tickets, and course timetables.

Provides a thread-safe mock storage for Week 4 tool execution.
"""

from datetime import datetime, timezone
import random
from typing import Any

from tools.schemas import CaseNote, TicketCategory, TicketPriority, TimetableEntry

# Pre-populated mock timetables for Makerere University courses
MOCK_TIMETABLES: dict[str, list[TimetableEntry]] = {
    "BSE4104": [
        TimetableEntry(
            course_code="BSE4104",
            course_title="Emerging Trends in Software Engineering",
            entry_type="LECTURE",
            day="Wednesday",
            start_time="08:00 AM",
            end_time="11:00 AM",
            venue="Block B Lab 3 / SCIT",
            instructor="Dr. Grace Kamulegeya",
        ),
        TimetableEntry(
            course_code="BSE4104",
            course_title="Emerging Trends in Software Engineering",
            entry_type="EXAM",
            day="Monday",
            start_time="09:00 AM",
            end_time="12:00 PM",
            venue="Main Library Computer Lab 1",
            instructor="Chief Invigilator - COCIS",
        ),
    ],
    "BIT2101": [
        TimetableEntry(
            course_code="BIT2101",
            course_title="Database Management Systems",
            entry_type="LECTURE",
            day="Tuesday",
            start_time="02:00 PM",
            end_time="05:00 PM",
            venue="SCIT Room 102",
            instructor="Dr. Agnes Nakakawa",
        ),
    ],
    "CSC3100": [
        TimetableEntry(
            course_code="CSC3100",
            course_title="Operating Systems & Architecture",
            entry_type="LAB",
            day="Thursday",
            start_time="11:00 AM",
            end_time="01:00 PM",
            venue="SCIT Lab 2",
            instructor="Eng. Joel Ocen",
        ),
    ],
}

# Pre-populated mock student cases
MOCK_CASES: dict[str, dict[str, Any]] = {
    "TICK-2026-1001": {
        "case_id": "TICK-2026-1001",
        "student_id": "2100701234",
        "category": TicketCategory.ACADEMIC_REGISTRAR.value,
        "subject": "Missing Marks for Semester 2 Examinations",
        "description": "Student sat for BSE3201 exam but grade shows missing on portal.",
        "priority": TicketPriority.HIGH.value,
        "status": "UNDER_REVIEW",
        "assigned_officer": "Mr. Joseph Okello (Academic Registrar - Exams)",
        "created_at": "2026-09-10T10:15:00Z",
        "last_updated": "2026-09-12T14:30:00Z",
        "notes": [
            CaseNote(
                timestamp="2026-09-10T10:15:00Z",
                author="System Agent",
                note="Ticket logged and routed to Academic Registrar.",
            ),
            CaseNote(
                timestamp="2026-09-12T14:30:00Z",
                author="Mr. Joseph Okello",
                note="Mark sheet requested from Course Coordinator.",
            ),
        ],
    },
    "TICK-2026-1002": {
        "case_id": "TICK-2026-1002",
        "student_id": "2100705678",
        "category": TicketCategory.FINANCIAL_AID.value,
        "subject": "Tuition Clearance Verification for Examination Permit",
        "description": "Payment made via bank draft on Monday, portal not updated.",
        "priority": TicketPriority.MEDIUM.value,
        "status": "RESOLVED",
        "assigned_officer": "Ms. Sarah Namubiru (Bursar Office)",
        "created_at": "2026-09-08T09:00:00Z",
        "last_updated": "2026-09-09T11:20:00Z",
        "notes": [
            CaseNote(
                timestamp="2026-09-08T09:00:00Z",
                author="System Agent",
                note="Ticket logged and routed to Finance Department.",
            ),
            CaseNote(
                timestamp="2026-09-09T11:20:00Z",
                author="Ms. Sarah Namubiru",
                note="Bank payment verified and examination permit activated.",
            ),
        ],
    },
}


class MockDatabase:
    """In-memory database for support cases and timetables."""

    def __init__(self) -> None:
        self.cases: dict[str, dict[str, Any]] = dict(MOCK_CASES)
        self.timetables: dict[str, list[TimetableEntry]] = dict(MOCK_TIMETABLES)

    def create_ticket(
        self,
        student_id: str,
        category: str,
        subject: str,
        description: str,
        priority: str,
    ) -> dict[str, Any]:
        random_num = random.randint(1000, 9999)
        ticket_id = f"TICK-2026-{random_num}"
        now_iso = datetime.now(timezone.utc).isoformat()

        # Department routing map
        dept_map = {
            TicketCategory.ACADEMIC_REGISTRAR.value: "Academic Registrar Department",
            TicketCategory.FINANCIAL_AID.value: "University Bursar & Financial Aid Office",
            TicketCategory.HALL_ALLOCATION.value: "Dean of Students - Accommodation",
            TicketCategory.LIBRARY_SERVICES.value: "University Main Library Services",
            TicketCategory.IT_SUPPORT.value: "DICTS IT Helpdesk",
            TicketCategory.GENERAL.value: "General Student Affairs Office",
        }
        assigned_dept = dept_map.get(category, "General Student Affairs Office")

        case_record = {
            "case_id": ticket_id,
            "student_id": student_id,
            "category": category,
            "subject": subject,
            "description": description,
            "priority": priority,
            "status": "CREATED",
            "assigned_officer": f"Duty Officer ({assigned_dept})",
            "assigned_department": assigned_dept,
            "created_at": now_iso,
            "last_updated": now_iso,
            "notes": [
                CaseNote(
                    timestamp=now_iso,
                    author="System Agent",
                    note=f"Ticket created and assigned to {assigned_dept}.",
                )
            ],
        }
        self.cases[ticket_id] = case_record
        return case_record

    def get_case(self, case_id: str) -> dict[str, Any] | None:
        return self.cases.get(case_id)

    def get_timetable(
        self, student_id: str, course_code: str | None = None
    ) -> list[TimetableEntry]:
        if course_code:
            code_upper = course_code.strip().upper()
            return self.timetables.get(code_upper, [])

        # Default fallback: return sample courses if no specific course requested
        all_entries: list[TimetableEntry] = []
        for entries in self.timetables.values():
            all_entries.extend(entries)
        return all_entries


# Global instance
_mock_db_instance = MockDatabase()


def get_mock_db() -> MockDatabase:
    return _mock_db_instance
