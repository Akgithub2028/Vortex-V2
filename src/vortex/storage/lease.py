"""
Vortex Distributed Lease Manager — Redis-backed strict TTL leases with in-memory fallback.

Provides atomic, lock-free lease acquisition, renewal, and release using Lua scripts to prevent
race conditions during worker execution and enable instant fault-recovery on worker crashes.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta, timezone
from typing import ClassVar

from vortex.observability.logger import get_logger
from vortex.storage.redis import get_redis

logger = get_logger(__name__)

# Lua Script for Atomic Renew: Only extend TTL if owner matches
RENEW_LUA_SCRIPT = """
if redis.call("get", KEYS[1]) == ARGV[1] then
    return redis.call("expire", KEYS[1], ARGV[2])
else
    return 0
end
"""

# Lua Script for Atomic Release: Only delete key if owner matches
RELEASE_LUA_SCRIPT = """
if redis.call("get", KEYS[1]) == ARGV[1] then
    return redis.call("del", KEYS[1])
else
    return 0
end
"""


class LeaseManager:
    """Manages distributed task leases for worker fault tolerance."""

    _in_memory_leases: ClassVar[dict[str, tuple[str, datetime]]] = {}
    _lock: ClassVar[asyncio.Lock] = asyncio.Lock()

    @classmethod
    async def acquire_lease(
        cls,
        resource_id: str,
        owner_id: str,
        ttl_seconds: float = 10.0,
    ) -> bool:
        """
        Atomically acquire a lease for a resource_id.

        Returns True if lease was successfully acquired by owner_id, False otherwise.
        """
        key = f"vortex:lease:{resource_id}"
        ttl_ms = int(ttl_seconds * 1000)

        try:
            client = get_redis()
            # SET key owner_id NX PX ttl_ms
            acquired = await client.set(key, owner_id, nx=True, px=ttl_ms)
            if acquired:
                logger.debug("Acquired distributed lease", resource=resource_id, owner=owner_id, ttl=ttl_seconds)
                return True
            return False
        except Exception as e:
            logger.debug("Redis unavailable, using in-memory lease store", error=str(e))

        # In-memory fallback for testing / isolated environments
        async with cls._lock:
            now = datetime.now(UTC)
            if resource_id in cls._in_memory_leases:
                curr_owner, expiry = cls._in_memory_leases[resource_id]
                if curr_owner != owner_id and now < expiry:
                    return False

            cls._in_memory_leases[resource_id] = (owner_id, now + timedelta(seconds=ttl_seconds))
            return True

    @classmethod
    async def renew_lease(
        cls,
        resource_id: str,
        owner_id: str,
        ttl_seconds: float = 10.0,
    ) -> bool:
        """
        Renew an active lease if owned by owner_id.

        Returns True if successfully renewed, False if lease was lost or expired.
        """
        key = f"vortex:lease:{resource_id}"
        ttl_sec_int = int(ttl_seconds)

        try:
            client = get_redis()
            res = await client.eval(RENEW_LUA_SCRIPT, 1, key, owner_id, ttl_sec_int)
            return bool(res == 1)
        except Exception as e:
            logger.debug("Redis unavailable during lease renew, checking in-memory fallback", error=str(e))

        async with cls._lock:
            now = datetime.now(UTC)
            if resource_id in cls._in_memory_leases:
                curr_owner, expiry = cls._in_memory_leases[resource_id]
                if curr_owner == owner_id and now < expiry:
                    cls._in_memory_leases[resource_id] = (owner_id, now + timedelta(seconds=ttl_seconds))
                    return True
            return False

    @classmethod
    async def release_lease(
        cls,
        resource_id: str,
        owner_id: str,
    ) -> bool:
        """
        Safely release a lease if owned by owner_id.
        """
        key = f"vortex:lease:{resource_id}"

        try:
            client = get_redis()
            res = await client.eval(RELEASE_LUA_SCRIPT, 1, key, owner_id)
            logger.debug("Released distributed lease", resource=resource_id, owner=owner_id)
            return bool(res == 1)
        except Exception as e:
            logger.debug("Redis unavailable during lease release", error=str(e))

        async with cls._lock:
            if resource_id in cls._in_memory_leases:
                curr_owner, _ = cls._in_memory_leases[resource_id]
                if curr_owner == owner_id:
                    del cls._in_memory_leases[resource_id]
                    return True
            return False

    @classmethod
    async def is_lease_active(cls, resource_id: str) -> bool:
        """Check if a lease is currently held."""
        key = f"vortex:lease:{resource_id}"

        try:
            client = get_redis()
            val = await client.get(key)
            return val is not None
        except Exception:
            pass

        async with cls._lock:
            now = datetime.now(UTC)
            if resource_id in cls._in_memory_leases:
                _, expiry = cls._in_memory_leases[resource_id]
                return now < expiry
            return False

    @classmethod
    def clear_in_memory_leases(cls) -> None:
        """Clear local in-memory lease dictionary (for unit test reset)."""
        cls._in_memory_leases.clear()
