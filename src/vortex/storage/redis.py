"""
Async Redis connection singleton and helper utilities for Vortex.

Handles:
- Distributed locks
- Task queues (Redis Streams)
- Event pub/sub
- Rate limiting counters
- Semantic / exact cache storage
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from redis.asyncio import Redis

from vortex.config import get_settings
from vortex.observability.logger import get_logger

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

logger = get_logger(__name__)

_redis_client: Redis | None = None


def get_redis() -> Redis:
    """Return the async Redis client singleton."""
    global _redis_client
    if _redis_client is None:
        settings = get_settings()
        _redis_client = Redis.from_url(
            settings.redis_url,
            max_connections=settings.redis_max_connections,
            socket_timeout=settings.redis_socket_timeout,
            retry_on_timeout=settings.redis_retry_on_timeout,
            decode_responses=True,
        )
        logger.info("Redis client initialized", url=settings.redis_url.split("@")[-1])
    return _redis_client


async def init_redis() -> None:
    """Verify Redis connection during app startup."""
    client = get_redis()
    try:
        await client.ping()
        logger.info("Redis connection verified")
    except Exception as e:
        logger.warning("Redis connection failed during startup — running in degraded mode", error=str(e))


async def close_redis() -> None:
    """Close Redis client during app shutdown."""
    global _redis_client
    if _redis_client is not None:
        await _redis_client.aclose()
        _redis_client = None
        logger.info("Redis client closed")


@asynccontextmanager
async def lock(
    name: str,
    timeout: float = 10.0,
    blocking_timeout: float = 5.0,
) -> AsyncGenerator[bool, None]:
    """
    Distributed lock helper using Redis.

    Usage:
        async with lock(f"workflow:{run_id}"):
            # Critical section
    """
    client = get_redis()
    lock_obj = client.lock(
        f"lock:{name}",
        timeout=timeout,
        blocking_timeout=blocking_timeout,
    )
    acquired = await lock_obj.acquire()
    try:
        yield acquired
    finally:
        if acquired:
            try:
                await lock_obj.release()
            except Exception as e:
                logger.warning("Failed to release lock", lock=name, error=str(e))
