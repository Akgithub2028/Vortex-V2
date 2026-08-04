"""
Vortex KV-Cache Affinity Router.

Provides prefix hashing and consistent hash routing to send requests sharing common prompt prefixes
(system prompts, context documents) to the same LLM replica endpoint to leverage warm KV caches.
"""

from __future__ import annotations

import hashlib
import zlib
from typing import ClassVar

from vortex.observability.logger import get_logger
from vortex.storage.redis import get_redis

logger = get_logger(__name__)


def compute_prefix_hash(messages: list[dict[str, str]], prefix_chars: int = 64) -> str:
    """
    Compute a SHA-256 hash of the prompt prefix across messages.

    Normalizes system prompts and prompt prefix text up to `prefix_chars`.
    """
    prefix_parts = []
    for msg in messages:
        role = msg.get("role", "")
        content = msg.get("content", "")
        if role == "system":
            prefix_parts.append(f"system:{content}")
        elif role == "user":
            prefix_parts.append(f"user:{content[:30]}")

    combined = "\n".join(prefix_parts)[:prefix_chars]
    return hashlib.sha256(combined.encode("utf-8")).hexdigest()[:16]


class KVCacheAffinityRouter:
    """Manages KV-Cache prefix affinity bindings using consistent hashing and Redis cache."""

    _local_affinity_cache: ClassVar[dict[str, str]] = {}

    @classmethod
    async def get_affinity_route(
        cls,
        prefix_hash: str,
        available_replicas: list[str],
    ) -> str | None:
        """
        Select a target replica using consistent hashing or stored affinity binding.
        """
        if not available_replicas:
            return None

        key = f"vortex:kv_affinity:{prefix_hash}"

        try:
            client = get_redis()
            bound_replica = await client.get(key)
            if bound_replica and bound_replica in available_replicas:
                logger.debug("KV-Cache affinity hit", prefix_hash=prefix_hash, replica=bound_replica)
                return bound_replica
        except Exception:
            pass

        # In-memory check
        if prefix_hash in cls._local_affinity_cache:
            bound = cls._local_affinity_cache[prefix_hash]
            if bound in available_replicas:
                return bound

        # Consistent Hash selection fallback
        hash_val = zlib.crc32(prefix_hash.encode("utf-8"))
        selected = available_replicas[hash_val % len(available_replicas)]
        return selected

    @classmethod
    async def register_affinity(
        cls,
        prefix_hash: str,
        replica_endpoint: str,
        ttl_seconds: int = 300,
    ) -> None:
        """Register KV-cache prefix binding for subsequent requests."""
        key = f"vortex:kv_affinity:{prefix_hash}"
        cls._local_affinity_cache[prefix_hash] = replica_endpoint

        try:
            client = get_redis()
            await client.set(key, replica_endpoint, ex=ttl_seconds)
            logger.debug("Registered KV-Cache affinity", prefix_hash=prefix_hash, replica=replica_endpoint)
        except Exception:
            pass

    @classmethod
    def clear_cache(cls) -> None:
        """Clear local affinity cache."""
        cls._local_affinity_cache.clear()
