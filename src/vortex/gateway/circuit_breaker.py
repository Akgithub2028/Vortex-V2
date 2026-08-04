"""
Circuit Breaker pattern for Model Gateway.

States: CLOSED (normal), OPEN (blocking requests), HALF_OPEN (testing recovery).
Prevents cascading failures when an upstream model provider experiences an outage.
"""

from __future__ import annotations

import time
from enum import Enum

from vortex.observability.logger import get_logger

logger = get_logger(__name__)


class CircuitState(str, Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class CircuitBreaker:

    def __init__(
        self,
        threshold: int = 5,
        recovery_seconds: float = 30.0,
    ):
        self.threshold = threshold
        self.recovery_seconds = recovery_seconds
        self.failure_count = 0
        self.state = CircuitState.CLOSED
        self.last_state_change = time.time()

    def allow_request(self) -> bool:
        now = time.time()
        if self.state == CircuitState.OPEN:
            if now - self.last_state_change > self.recovery_seconds:
                logger.info("Circuit breaker entering HALF_OPEN state")
                self.state = CircuitState.HALF_OPEN
                self.last_state_change = now
                return True
            return False
        return True

    def record_success(self) -> None:
        if self.state != CircuitState.CLOSED:
            logger.info("Circuit breaker recovered, entering CLOSED state")
        self.failure_count = 0
        self.state = CircuitState.CLOSED

    def record_failure(self) -> None:
        self.failure_count += 1
        logger.warning("Circuit breaker failure recorded", count=self.failure_count, threshold=self.threshold)
        if self.failure_count >= self.threshold:
            logger.error("Circuit breaker tripped to OPEN state")
            self.state = CircuitState.OPEN
            self.last_state_change = time.time()
