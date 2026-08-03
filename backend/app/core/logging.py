"""
Structured logging configuration using structlog + OpenTelemetry.

Provides JSON-formatted logs in production and human-readable
colored output in development. Every log entry includes:
  - timestamp
  - log level
  - logger name
  - request_id (injected by middleware)
  - tenant_id (injected by middleware)
  - user_id (injected by middleware)
"""

from __future__ import annotations

import logging
import sys
from typing import Any

import structlog
from structlog.types import EventDict, Processor


def _add_log_level(
    logger: Any,
    method: str,
    event_dict: EventDict,
) -> EventDict:
    """Add the standard log level to every event dict."""
    event_dict["level"] = method.upper()
    return event_dict


def _drop_color_message_key(
    logger: Any,
    method: str,
    event_dict: EventDict,
) -> EventDict:
    """Remove uvicorn's color_message key to avoid duplicate messages."""
    event_dict.pop("color_message", None)
    return event_dict


def configure_logging(log_level: str = "INFO", log_format: str = "json") -> None:
    """
    Configure structlog and stdlib logging.

    Args:
        log_level: Python logging level string (DEBUG, INFO, WARNING, ERROR).
        log_format: "json" for production, "console" for development.
    """
    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        _add_log_level,
        _drop_color_message_key,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.stdlib.add_logger_name,
        structlog.processors.StackInfoRenderer(),
    ]

    if log_format == "console":
        processors: list[Processor] = [
            *shared_processors,
            structlog.dev.ConsoleRenderer(colors=True),
        ]
    else:
        processors = [
            *shared_processors,
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.getLevelName(log_level.upper())
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )

    # Redirect stdlib logging (uvicorn, sqlalchemy, etc.) through structlog
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.getLevelName(log_level.upper()),
    )

    # Quieten noisy libraries in production
    for noisy_logger in (
        "uvicorn.access",
        "sqlalchemy.engine",
        "httpx",
        "celery",
        "openai",
    ):
        logging.getLogger(noisy_logger).setLevel(logging.WARNING)


def get_logger(name: str | None = None) -> structlog.BoundLogger:
    """
    Return a structlog bound logger.

    Usage::

        logger = get_logger(__name__)
        logger.info("User logged in", user_id=str(user.id))
    """
    return structlog.get_logger(name)
