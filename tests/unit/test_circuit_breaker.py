"""
Unit tests for Model Gateway Circuit Breaker.
"""

from vortex.gateway.circuit_breaker import CircuitBreaker, CircuitState


def test_circuit_breaker_tripping():
    cb = CircuitBreaker(threshold=3, recovery_seconds=1.0)
    assert cb.state == CircuitState.CLOSED
    assert cb.allow_request() is True

    cb.record_failure()
    cb.record_failure()
    assert cb.state == CircuitState.CLOSED

    # 3rd failure trips to OPEN
    cb.record_failure()
    assert cb.state == CircuitState.OPEN
    assert cb.allow_request() is False


def test_circuit_breaker_recovery():
    cb = CircuitBreaker(threshold=2, recovery_seconds=0.01)
    cb.record_failure()
    cb.record_failure()
    assert cb.state == CircuitState.OPEN

    import time

    time.sleep(0.02)

    # Should enter HALF_OPEN on next call
    assert cb.allow_request() is True
    assert cb.state == CircuitState.HALF_OPEN

    # Success resets to CLOSED
    cb.record_success()
    assert cb.state == CircuitState.CLOSED
