"""Base class and execution contracts for agentic tools.

Every tool implements:
- Purpose: Clear description and tool intent
- Input Schema: Pydantic model enforcing type safety and validation
- Output Schema: Structured return contract with status and metadata
- Authorization: Explicit permission check prior to execution
- Failure Behaviour: Graceful handling of missing parameters, authorization rejection,
  and runtime errors without application crashes.
"""

from abc import ABC, abstractmethod
from typing import Any, Generic, Type, TypeVar
from pydantic import BaseModel, ValidationError

InT = TypeVar("InT", bound=BaseModel)
OutT = TypeVar("OutT", bound=BaseModel)


class BaseTool(ABC, Generic[InT, OutT]):
    """Abstract base class for deterministic, safe tools."""

    name: str
    description: str
    input_schema_class: Type[InT]
    output_schema_class: Type[OutT]

    @property
    def tool_purpose(self) -> str:
        """Return human-readable tool purpose statement."""
        return self.description

    def get_json_schema(self) -> dict[str, Any]:
        """Generate standard OpenAI/Groq function calling specification."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.input_schema_class.model_json_schema(),
            },
        }

    @abstractmethod
    def authorize(self, input_data: InT) -> tuple[bool, str]:
        """Verify caller permissions before running tool logic.

        Returns:
            (is_authorized, rationale_or_error_reason)
        """
        ...

    @abstractmethod
    def _run(self, input_data: InT) -> OutT:
        """Execute core tool logic assuming input is valid and authorized."""
        ...

    def execute(self, raw_input: dict[str, Any] | InT) -> OutT:
        """Tool execution pipeline with strict failure handling.

        Pipeline steps:
        1. Validate raw input against Pydantic schema -> catch ValidationError
        2. Verify authorization permissions -> catch permission denied
        3. Execute tool logic -> catch unhandled runtime errors
        """
        # Step 1: Input Validation
        if isinstance(raw_input, dict):
            try:
                validated_input = self.input_schema_class(**raw_input)
            except ValidationError as val_err:
                return self._handle_validation_error(str(val_err))
            except Exception as exc:
                return self._handle_validation_error(f"Invalid input payload: {exc}")
        else:
            validated_input = raw_input

        # Step 2: Authorization Check
        is_authorized, auth_reason = self.authorize(validated_input)
        if not is_authorized:
            return self._handle_authorization_failure(auth_reason)

        # Step 3: Execution with error containment
        try:
            return self._run(validated_input)
        except Exception as exc:
            return self._handle_execution_error(exc)

    @abstractmethod
    def _handle_validation_error(self, error_msg: str) -> OutT:
        """Return structured failure response for schema validation errors."""
        ...

    @abstractmethod
    def _handle_authorization_failure(self, reason: str) -> OutT:
        """Return structured failure response for permission denial."""
        ...

    @abstractmethod
    def _handle_execution_error(self, exc: Exception) -> OutT:
        """Return structured failure response for internal runtime errors."""
        ...
