"""
FastAPI Request ID middleware.

Ensures every incoming request has a unique `X-Request-ID` header.
Propagates the ID to `request.state.request_id` and response headers.
Binds `request_id` to structlog context vars for log correlation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from ulid import ULID

if TYPE_CHECKING:
    from collections.abc import Callable

    from fastapi import Request, Response


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Respect incoming header or generate a new ULID
        request_id = request.headers.get("X-Request-ID") or str(ULID())

        # Store on request state for error handlers and endpoints
        request.state.request_id = request_id

        # Bind to structlog context for all logs during this request
        structlog.contextvars.bind_contextvars(request_id=request_id)

        try:
            response: Response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            structlog.contextvars.unbind_contextvars("request_id")
