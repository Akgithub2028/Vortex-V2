"""
Vortex Provider Rate Limiter.

Implements token-bucket rate limiting for model provider endpoints (e.g. 40 RPM limit for NVIDIA NIM).
Uses Redis with in-memory fallback for local dev & testing.
"""

from __future__ import annotations

import asyncio
import time
from typing import ClassVar

from vortex.config import get_settings
from vortex.observability.logger import get_logger
from vortex.storage.redis import get_redis

logger = get_logger(__name__)


class ProviderRateLimiter:
    """Manages rate limits per provider endpoint."""

    _in_memory_buckets: ClassVar[dict[str, tuple[float, float]]] = {}  # key -> (tokens, last_update)
    _lock: ClassVar[asyncio.Lock] = asyncio.Lock()

    @classmethod
    async def acquire(cls, provider_name: str, max_rpm: int = 40) -> bool:
        """
        Check and consume 1 rate limit token for provider_name.
        Returns True if request is within rate limit, False if limit exceeded.
        """
        settings = get_settings()
        if provider_name.lower() in ("nvidia", "nvidia_nim", "nim"):
            max_rpm = settings.nvidia_rate_limit_rpm

        key = f"vortex:ratelimit:provider:{provider_name.lower()}"
        now = time.time()

        # Try Redis Rate Limiting (sliding window counter)
        try:
            client = get_redis()
            pipe = client.pipeline()
            # Window key per minute
            minute_key = f"{key}:{int(now // 60)}"
            pipe.incr(minute_key)
            pipe.expire(minute_key, 120)
            res = await pipe.execute()
            count = res[0]
            if count > max_rpm:
                logger.warning("Provider rate limit exceeded", provider=provider_name, rpm=max_rpm, current=count)
                return False
            return True
        except Exception:
            pass

        # In-memory Token Bucket fallback
        async with cls._lock:
            capacity = float(max_rpm)
            refill_rate = capacity / 60.0  # tokens per second

            if key not in cls._in_memory_buckets:
                cls._in_memory_buckets[key] = (capacity - 1.0, now)
                return True

            tokens, last_update = cls._in_memory_buckets[key]
            elapsed = now - last_update
            tokens = min(capacity, tokens + elapsed * refill_rate)

            if tokens >= 1.0:
                cls._in_memory_buckets[key] = (tokens - 1.0, now)
                return True
            else:
                logger.warning("In-memory provider rate limit exceeded", provider=provider_name, rpm=max_rpm)
                return False

    @classmethod
    async def reset(cls) -> None:
        """Reset local and Redis rate limit state (for unit testing)."""
        cls._in_memory_buckets.clear()
        try:
            client = get_redis()
            keys = await client.keys("vortex:ratelimit:provider:*")
            if keys:
                await client.delete(*keys)
        except Exception:
            pass
