"""Structured logging: one log line per trace event, as JSON or readable text.

Trace events are logged with `extra={"trace_event": {...}}`. In "json"
mode every line is a single JSON object (ready for jq, Loki, ELK, ...);
in "text" mode the event fields are appended to the usual log line so
local development stays readable.
"""

import json
import logging
from datetime import datetime, timezone

_RESERVED = {"ts", "level", "logger", "event"}


class StructuredFormatter(logging.Formatter):
    def __init__(self, json_output: bool):
        super().__init__("%(asctime)s %(levelname)s %(name)s: %(message)s")
        self._json = json_output

    def format(self, record: logging.LogRecord) -> str:
        fields = getattr(record, "trace_event", None)
        if not self._json:
            line = super().format(record)
            if fields:
                line += " " + json.dumps(fields, default=str, ensure_ascii=False)
            return line

        payload = {
            "ts": datetime.fromtimestamp(record.created, timezone.utc).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "event": record.getMessage(),
        }
        if fields:
            payload.update({k: v for k, v in fields.items() if k not in _RESERVED})
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str, ensure_ascii=False)


def configure_logging(level: str = "INFO", log_format: str = "text") -> None:
    """Install the structured formatter on the root logger (no-op if already configured)."""
    handler = logging.StreamHandler()
    handler.setFormatter(StructuredFormatter(json_output=log_format.lower() == "json"))
    logging.basicConfig(level=level, handlers=[handler])
