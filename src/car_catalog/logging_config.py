"""Structured JSON logging configuration."""

import json
import logging

from car_catalog.config import Settings, get_settings


class JsonFormatter(logging.Formatter):
    """Format each log record as a single JSON object."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info is not None:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging(settings: Settings | None = None) -> None:
    """Configure the root logger using the selected runtime log level."""
    active_settings = settings or get_settings()
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    logging.basicConfig(
        level=active_settings.log_level,
        handlers=[handler],
        force=True,
    )
