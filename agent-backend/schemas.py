"""Pydantic request/response models for the public API."""

from pydantic import BaseModel, Field, field_validator

MAX_MESSAGE_LENGTH = 2000


class StudentSupportRequest(BaseModel):
    message: str = Field(
        ...,
        min_length=1,
        max_length=MAX_MESSAGE_LENGTH,
        description="The student's support question.",
    )

    @field_validator("message")
    @classmethod
    def message_must_not_be_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("message must not be empty or whitespace-only")
        return stripped


class StudentSupportResponse(BaseModel):
    response: str
    prompt_version: str
    model: str


class HealthResponse(BaseModel):
    status: str


class ErrorResponse(BaseModel):
    detail: str
