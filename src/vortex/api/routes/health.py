"""
Health and readiness probe endpoints.

GET /healthz — Liveness probe (is API running?)
GET /readyz — Readiness probe (are DB & Redis connected?)
"""

from __future__ import annotations

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import text

from vortex.config import get_settings
from vortex.observability.logger import get_logger
from vortex.storage.database import get_engine
from vortex.storage.redis import get_redis

logger = get_logger(__name__)
router = APIRouter(tags=["System"])


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    environment: str


class ReadinessResponse(BaseModel):
    status: str
    database: str
    redis: str


@router.get("/healthz", response_model=HealthResponse, summary="Liveness probe")
async def healthz() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(
        status="ok",
        service=settings.service_name,
        version=settings.service_version,
        environment=settings.environment.value,
    )


@router.get("/readyz", response_model=ReadinessResponse, summary="Readiness probe")
async def readyz() -> JSONResponse:
    db_status = "ok"
    redis_status = "ok"
    is_ready = True

    # Check Database
    try:
        engine = get_engine()
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as e:
        logger.warning("Readiness probe DB check failed", error=str(e))
        db_status = f"error: {e!s}"
        is_ready = False

    # Check Redis
    try:
        redis_client = get_redis()
        await redis_client.ping()
    except Exception as e:
        logger.warning("Readiness probe Redis check failed", error=str(e))
        redis_status = f"error: {e!s}"
        is_ready = False

    status_code = status.HTTP_200_OK if is_ready else status.HTTP_531_SERVICE_UNAVAILABLE if hasattr(status, "HTTP_531_SERVICE_UNAVAILABLE") else status.HTTP_503_SERVICE_UNAVAILABLE

    return JSONResponse(
        status_code=status_code,
        content={
            "status": "ready" if is_ready else "not_ready",
            "database": db_status,
            "redis": redis_status,
        },
    )
