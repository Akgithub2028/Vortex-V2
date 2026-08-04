"""
FastAPI application factory and CLI entrypoint.

Assembles middleware, routes, exception handlers, and lifespan lifecycle management.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app

from vortex.api.errors import VortexError, unhandled_exception_handler, vortex_error_handler
from vortex.api.middleware.request_id import RequestIDMiddleware
from vortex.api.routes import evals, health, keys, models, prompts, workflows
from vortex.config import get_settings
from vortex.observability import setup_logging, setup_metrics, setup_tracing
from vortex.observability.logger import get_logger
from vortex.storage.database import close_db, init_db
from vortex.storage.redis import close_redis, init_redis

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """App startup and shutdown lifecycle management."""
    settings = get_settings()

    # 1. Setup logging, metrics, tracing
    setup_logging()
    setup_tracing()
    setup_metrics()

    logger.info(
        "Starting Vortex API server",
        version=settings.service_version,
        environment=settings.environment.value,
    )

    # 2. Init database & redis connections
    await init_db()
    await init_redis()

    yield

    # 3. Shutdown cleanup
    logger.info("Shutting down Vortex API server")
    await close_redis()
    await close_db()


def create_app() -> FastAPI:
    """FastAPI Application Factory."""
    settings = get_settings()

    app = FastAPI(
        title="Vortex AI Execution Engine",
        description="Open-source AI Execution Engine — durable workflows, model gateway, semantic caching, guardrails, and evaluation gates.",
        version=settings.service_version,
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
        lifespan=lifespan,
    )

    # ─── Middleware ────────────────────────────────────────────────────────────

    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.api_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ─── Exception Handlers ────────────────────────────────────────────────────

    app.add_exception_handler(VortexError, vortex_error_handler)  # type: ignore
    app.add_exception_handler(Exception, unhandled_exception_handler)

    # ─── Include Routes ────────────────────────────────────────────────────────

    app.include_router(health.router)
    app.include_router(workflows.router)
    app.include_router(models.router)
    app.include_router(evals.router)
    app.include_router(keys.router)
    app.include_router(prompts.router)

    # Prometheus metrics endpoint
    if settings.metrics_enabled:
        metrics_app = make_asgi_app()
        app.mount("/metrics", metrics_app)

    return app


def cli() -> None:  # pragma: no cover
    """CLI entrypoint (`vortex`). Launches Uvicorn dev server."""
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "vortex.api.main:create_app",
        factory=True,
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
        log_level=settings.log_level.value.lower(),
    )


if __name__ == "__main__":  # pragma: no cover
    cli()
