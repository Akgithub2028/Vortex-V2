"""
Vortex API error handling — structured exceptions and handlers.

All API errors return consistent JSON responses:
{
    "error": {
        "code": "WORKFLOW_NOT_FOUND",
        "message": "Workflow run run-123 was not found.",
        "details": {},
        "request_id": "req-abc"
    }
}
"""

from __future__ import annotations

from typing import Any

from fastapi import Request, status
from fastapi.responses import JSONResponse

from vortex.observability.logger import get_logger

logger = get_logger(__name__)


class VortexError(Exception):
    """Base exception for all Vortex application errors."""

    def __init__(
        self,
        message: str,
        code: str = "INTERNAL_ERROR",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}


class NotFoundError(VortexError):
    def __init__(self, resource: str, identifier: str):
        super().__init__(
            message=f"{resource} '{identifier}' was not found.",
            code=f"{resource.upper()}_NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND,
        )


class UnauthorizedError(VortexError):
    def __init__(self, message: str = "Authentication required."):
        super().__init__(
            message=message,
            code="UNAUTHORIZED",
            status_code=status.HTTP_401_UNAUTHORIZED,
        )


class ForbiddenError(VortexError):
    def __init__(self, message: str = "Permission denied."):
        super().__init__(
            message=message,
            code="FORBIDDEN",
            status_code=status.HTTP_403_FORBIDDEN,
        )


class RateLimitExceededError(VortexError):
    def __init__(self, retry_after: int = 60):
        super().__init__(
            message=f"Rate limit exceeded. Try again in {retry_after} seconds.",
            code="RATE_LIMIT_EXCEEDED",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            details={"retry_after": retry_after},
        )


class ValidationError(VortexError):
    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details,
        )


class BudgetExceededError(VortexError):
    def __init__(self, current_cost: float, max_cost: float):
        super().__init__(
            message=f"Workflow budget exceeded (${current_cost:.4f} > ${max_cost:.4f}).",
            code="BUDGET_EXCEEDED",
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            details={"current_cost": current_cost, "max_cost": max_cost},
        )


class GuardrailBlockError(VortexError):
    def __init__(self, guardrail_type: str, reason: str):
        super().__init__(
            message=f"Request blocked by guardrail '{guardrail_type}': {reason}",
            code="GUARDRAIL_BLOCKED",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details={"guardrail_type": guardrail_type, "reason": reason},
        )


async def vortex_error_handler(request: Request, exc: VortexError) -> JSONResponse:
    """Handler for all custom Vortex exceptions."""
    request_id = getattr(request.state, "request_id", "unknown")
    logger.warning(
        "Application error",
        code=exc.code,
        message=exc.message,
        status_code=exc.status_code,
        request_id=request_id,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
                "request_id": request_id,
            }
        },
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handler for unexpected unhandled exceptions (500)."""
    request_id = getattr(request.state, "request_id", "unknown")
    logger.error("Unhandled exception", error=str(exc), exc_info=exc, request_id=request_id)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred on the server.",
                "details": {},
                "request_id": request_id,
            }
        },
    )
