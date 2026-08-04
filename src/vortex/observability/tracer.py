"""
Vortex OpenTelemetry tracing setup.

Configures the OTel TracerProvider and exports spans via OTLP/gRPC.
Instruments FastAPI, httpx, and SQLAlchemy automatically.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from vortex.config import get_settings
from vortex.observability.logger import get_logger

if TYPE_CHECKING:
    from opentelemetry.trace import Tracer

logger = get_logger(__name__)


def setup_tracing() -> None:
    """
    Initialize OpenTelemetry tracing.

    No-op if VORTEX_OTEL_ENABLED is False.
    """
    settings = get_settings()

    if not settings.otel_enabled:
        logger.info("OpenTelemetry tracing disabled")
        return

    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        resource = Resource.create(
            {
                "service.name": settings.service_name,
                "service.version": settings.service_version,
                "deployment.environment": settings.environment.value,
            }
        )

        provider = TracerProvider(resource=resource)

        exporter = OTLPSpanExporter(
            endpoint=settings.otel_exporter_endpoint,
            insecure=not settings.is_production,
        )

        processor = BatchSpanProcessor(
            exporter,
            schedule_delay_millis=settings.otel_export_interval_ms,
        )
        provider.add_span_processor(processor)

        trace.set_tracer_provider(provider)

        # Auto-instrument FastAPI
        try:
            from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

            FastAPIInstrumentor.instrument()
        except ImportError:
            pass

        # Auto-instrument httpx (for outbound LLM calls)
        try:
            from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

            HTTPXClientInstrumentor.instrument()
        except ImportError:
            pass

        # Auto-instrument SQLAlchemy
        try:
            from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

            SQLAlchemyInstrumentor.instrument()
        except ImportError:
            pass

        logger.info(
            "OpenTelemetry tracing initialized",
            endpoint=settings.otel_exporter_endpoint,
        )

    except ImportError as e:
        logger.warning("OpenTelemetry dependencies not available", error=str(e))


def get_tracer(name: str = "vortex") -> Tracer | Any:
    """Get an OTel tracer instance for creating custom spans."""
    try:
        from opentelemetry import trace

        return trace.get_tracer(name)
    except ImportError:
        return None
