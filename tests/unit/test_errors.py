"""
Unit tests for Vortex API exception classes.
"""

from vortex.api.errors import (
    BudgetExceededError,
    ForbiddenError,
    GuardrailBlockError,
    NotFoundError,
    RateLimitExceededError,
    UnauthorizedError,
    ValidationError,
)


def test_vortex_exceptions():
    err = NotFoundError("WorkflowRun", "run-123")
    assert err.status_code == 404
    assert err.code == "WORKFLOWRUN_NOT_FOUND"

    unauth = UnauthorizedError("Invalid key")
    assert unauth.status_code == 401

    forb = ForbiddenError()
    assert forb.status_code == 403

    rate = RateLimitExceededError(retry_after=30)
    assert rate.status_code == 429

    val = ValidationError("Invalid DAG")
    assert val.status_code == 422

    bud = BudgetExceededError(1.5, 1.0)
    assert bud.status_code == 402

    guard = GuardrailBlockError("injection", "High risk detected")
    assert guard.status_code == 422
