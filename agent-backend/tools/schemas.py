"""Input/output schemas for every Week 4 tool.

Every tool's arguments and return value are validated against a
Pydantic model - the application never hands the model (or receives
from it) an unstructured dict. See docs/tool-catalogue.md for the
human-readable version of these schemas.
"""

import re
from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, field_validator

COURSE_CODE_PATTERN = re.compile(r"^[A-Z]{2,5}\d{3,5}$")

ALLOWED_TICKET_CATEGORIES = ("IT Support", "Academic", "Finance", "Other")


# ---------------------------------------------------------------------------
# check_timetable
# ---------------------------------------------------------------------------


class CheckTimetableInput(BaseModel):
    course_code: str = Field(..., min_length=1, description="e.g. 'BSE4104'")
    date: str | None = Field(default=None, description="Optional ISO date, e.g. '2026-09-24'")

    @field_validator("course_code")
    @classmethod
    def course_code_must_be_well_formed(cls, value: str) -> str:
        normalized = value.strip().upper()
        if not normalized:
            raise ValueError("course_code must not be empty")
        if not COURSE_CODE_PATTERN.match(normalized):
            raise ValueError(
                "course_code must look like 2-5 letters followed by 3-5 digits, e.g. 'BSE4104'"
            )
        return normalized

    @field_validator("date")
    @classmethod
    def date_must_be_valid_iso_date(cls, value: str | None) -> str | None:
        if value is None or value == "":
            return None
        try:
            date.fromisoformat(value)
        except ValueError as exc:
            raise ValueError(f"date must be a valid ISO date (YYYY-MM-DD): {value!r}") from exc
        return value


class TimetableSession(BaseModel):
    date: str
    start_time: str
    end_time: str
    venue: str


class CheckTimetableOutput(BaseModel):
    success: bool
    course_code: str | None = None
    sessions: list[TimetableSession] = []
    error: str | None = None


# ---------------------------------------------------------------------------
# create_support_ticket
# ---------------------------------------------------------------------------


class CreateSupportTicketInput(BaseModel):
    category: str = Field(..., min_length=1)
    subject: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=1, max_length=2000)

    @field_validator("category")
    @classmethod
    def category_must_be_recognized(cls, value: str) -> str:
        stripped = value.strip()
        if stripped not in ALLOWED_TICKET_CATEGORIES:
            raise ValueError(
                f"category must be one of {ALLOWED_TICKET_CATEGORIES}, got {stripped!r}"
            )
        return stripped

    @field_validator("subject", "description")
    @classmethod
    def must_not_be_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be empty or whitespace-only")
        return stripped


TicketStatus = Literal["PENDING_APPROVAL", "SUBMITTED", "REJECTED"]


class CreateSupportTicketOutput(BaseModel):
    success: bool
    ticket_id: str | None = None
    status: TicketStatus | None = None
    category: str | None = None
    subject: str | None = None
    error: str | None = None


class TicketRecord(BaseModel):
    ticket_id: str
    category: str
    subject: str
    description: str
    status: TicketStatus
    created_at: str
    updated_at: str
