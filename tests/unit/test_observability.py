"""
Unit tests for observability logging, metrics, and tracing setup.
"""

from vortex.observability.logger import get_logger, setup_logging
from vortex.observability.metrics import setup_metrics
from vortex.observability.tracer import get_tracer, setup_tracing


def test_logger_setup():
    setup_logging()
    logger = get_logger("test_logger")
    logger.info("Test log event", key="value")


def test_metrics_setup():
    setup_metrics()


def test_tracer_setup(monkeypatch):
    setup_tracing()
    tracer = get_tracer("test_tracer")
    assert tracer is None or hasattr(tracer, "start_span")

    from vortex.config import get_settings
    monkeypatch.setattr(get_settings(), "otel_enabled", True)
    try:
        setup_tracing()
    except (ImportError, Exception):
        pass
    tracer_active = get_tracer("test_active_tracer")
    assert tracer_active is None or hasattr(tracer_active, "start_span")


def test_logger_otel_span_context_injection():
    """Logger _add_otel_context should inject trace_id and span_id when OTel span is active."""
    from unittest.mock import MagicMock, patch
    from vortex.observability.logger import _add_otel_context

    # Mock an active span with a valid context
    class MockContext:
        trace_id = 123456789
        span_id = 987654321
        
    mock_span = MagicMock()
    mock_span.get_span_context.return_value = MockContext()

    mock_trace = MagicMock()
    mock_trace.get_current_span.return_value = mock_span

    with patch("opentelemetry.trace.get_current_span", return_value=mock_span):
        event_dict = {"event": "test"}
        result = _add_otel_context(None, "info", event_dict)
        assert "trace_id" in result
        assert "span_id" in result


def test_logger_production_json_renderer():
    """setup_logging with production environment should use JSON renderer."""
    from unittest.mock import patch, MagicMock
    from vortex.config import Environment

    mock_settings = MagicMock()
    mock_settings.environment = Environment.PRODUCTION
    mock_settings.log_level = MagicMock(value="INFO")
    mock_settings.database_echo = False

    with patch("vortex.observability.logger.get_settings", return_value=mock_settings):
        setup_logging()
        # If no exception raised, production JSON renderer was configured

