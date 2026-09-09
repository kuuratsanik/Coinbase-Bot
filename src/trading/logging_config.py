"""Structured logging for the toolkit.

Emits either human-readable or JSON lines (``CBDCA_LOG_FORMAT=json``) at a level
controlled by ``CBDCA_LOG_LEVEL``. A money-moving system benefits from a machine
-parseable audit trail, so JSON mode is first-class rather than an afterthought.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

_CONFIGURED = False


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        for key, value in getattr(record, "extra_fields", {}).items():
            payload[key] = value
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload)


def configure_logging(level: str | None = None, fmt: str | None = None) -> None:
    """Idempotently configure the root logger from args or environment."""

    global _CONFIGURED
    level = (level or os.getenv("CBDCA_LOG_LEVEL") or "INFO").upper()
    fmt = (fmt or os.getenv("CBDCA_LOG_FORMAT") or "text").lower()

    handler = logging.StreamHandler()
    if fmt == "json":
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)-7s %(name)s: %(message)s"))

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(getattr(logging, level, logging.INFO))
    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    if not _CONFIGURED:
        configure_logging()
    return logging.getLogger(name)


def log_event(logger: logging.Logger, level: int, msg: str, **fields: Any) -> None:
    """Log ``msg`` with structured ``fields`` (surfaced in JSON mode)."""

    logger.log(level, msg, extra={"extra_fields": fields})
