"""
Vortex structured logging — built on structlog.

Produces JSON in production, human-readable output in development.
Automatically binds trace_id, span_id, service, and environment to every log entry.
"""

from __future__ import annotations

import logging
import sys
from typing import Any

import structlog

from vortex.config import Environment, get_settings


def _add_service_context(logger: Any, method_name: str, event_dict: dict[str, Any]) -> dict[str, Any]:
    """Inject service-level context into every log entry."""
    settings = get_settings()
    event_dict.setdefault("service", settings.service_name)
    event_dict.setdefault("version", settings.service_version)
    event_dict.setdefault("environment", settings.environment.value)
    return event_dict


def _add_otel_context(logger: Any, method_name: str, event_dict: dict[str, Any]) -> dict[str, Any]:
    """Inject OpenTelemetry trace context if a span is active."""
    try:
        from opentelemetry import trace

        span = trace.get_current_span()
        ctx = span.get_span_context()
        if ctx and ctx.trace_id != 0:
            event_dict["trace_id"] = f"{ctx.trace_id:032x}"
            event_dict["span_id"] = f"{ctx.span_id:016x}"
    except ImportError:
        pass
    return event_dict


def setup_logging() -> None:
    """
    Configure structlog for the entire application.

    Call once at startup (in the FastAPI lifespan or CLI entrypoint).
    """
    settings = get_settings()
    log_level = getattr(logging, settings.log_level.value, logging.INFO)

    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        _add_service_context,
        _add_otel_context,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

    if settings.environment == Environment.PRODUCTION:
        # JSON output for production log aggregation (Loki, CloudWatch, etc.)
        renderer: structlog.types.Processor = structlog.processors.JSONRenderer()
    else:
        # Human-readable colored output for local development
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.processors.format_exc_info,
            renderer,
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Configure stdlib logging to route through structlog
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )

    # Quiet noisy libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.DEBUG if settings.database_echo else logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """
    Get a structured logger instance.

    Usage:
        logger = get_logger(__name__)
        logger.info("workflow started", workflow_id="abc", tenant_id="xyz")
    """
    return structlog.get_logger(name)
