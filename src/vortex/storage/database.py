"""
Async SQLAlchemy engine and session factory.

Provides a single async engine singleton and a dependency-injectable
async session factory for FastAPI routes and background workers.
"""

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from vortex.config import get_settings, sanitize_asyncpg_url
from vortex.observability.logger import get_logger

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

logger = get_logger(__name__)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""

    pass


# ─── Engine Singleton ─────────────────────────────────────────────────────────

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    """Return the async engine singleton. Creates it on first call."""
    global _engine
    if _engine is None:
        settings = get_settings()
        kwargs = {
            "pool_recycle": settings.database_pool_recycle,
            "echo": settings.database_echo,
            "pool_pre_ping": True,
        }
        if "sqlite" in settings.database_url:
            from sqlalchemy.pool import StaticPool

            kwargs["poolclass"] = StaticPool
            kwargs["connect_args"] = {"check_same_thread": False}
        else:
            kwargs["pool_size"] = settings.database_pool_size
            kwargs["max_overflow"] = settings.database_max_overflow

        db_url = sanitize_asyncpg_url(settings.database_url)
        _engine = create_async_engine(db_url, **kwargs)
        logger.info("Database engine created", pool_size=settings.database_pool_size)
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Return the async session factory singleton."""
    global _session_factory
    if _session_factory is None:
        engine = get_engine()
        _session_factory = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _session_factory


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Provide a transactional async database session.

    Usage:
        async with get_session() as session:
            result = await session.execute(...)
    """
    factory = get_session_factory()
    session = factory()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


async def init_db() -> None:
    """
    Initialize database schema and seed default records.

    Creates tables if missing and seeds default tenant.
    """
    engine = get_engine()
    async with engine.begin() as conn:
        from vortex.storage.models import Base

        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database connection and schema verified")

    try:
        from vortex.storage.models import Tenant

        default_tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000001")

        async with get_session() as session:
            tenant = await session.get(Tenant, default_tenant_id)
            if not tenant:
                session.add(Tenant(id=default_tenant_id, name="Default Dev Tenant"))
                await session.commit()
                logger.info("Default tenant seeded")
    except Exception as e:
        logger.warning("Default tenant seed warning (non-fatal)", error=str(e))


async def close_db() -> None:
    """
    Gracefully close the database engine and connection pool.

    Called during FastAPI lifespan shutdown.
    """
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _session_factory = None
        logger.info("Database engine disposed")
