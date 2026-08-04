"""
FastAPI dependency injection utilities.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from vortex.api.middleware.auth import AuthContext, get_current_auth, require_role
from vortex.storage.database import get_session
from vortex.storage.redis import get_redis

__all__ = [
    "AuthContext",
    "get_current_auth",
    "get_db_session",
    "get_redis_client",
    "require_role",
]


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency to provide a transactional async database session."""
    async with get_session() as session:
        yield session


def get_redis_client() -> Redis:
    """Dependency to provide the Redis client singleton."""
    return get_redis()
