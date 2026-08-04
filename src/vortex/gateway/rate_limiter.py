"""
Token Bucket Rate Limiter using Redis.
"""

from __future__ import annotations

import time

from vortex.storage.redis import get_redis


class RateLimiter:
    @staticmethod
    async def is_rate_limited(key_prefix: str, identifier: str, limit_rpm: int) -> tuple[bool, int]:
        """
        Check if an identifier has exceeded its rate limit.

        Returns (is_limited, retry_after_seconds).
        """
        redis = get_redis()
        current_minute = int(time.time() // 60)
        redis_key = f"rate:{key_prefix}:{identifier}:{current_minute}"

        current_count = await redis.incr(redis_key)
        if current_count == 1:
            await redis.expire(redis_key, 60)

        if current_count > limit_rpm:
            retry_after = 60 - int(time.time() % 60)
            return True, retry_after

        return False, 0
