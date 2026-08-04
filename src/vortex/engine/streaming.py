"""
Vortex Inter-Node Real-time Streaming Pub/Sub.

Enables downstream workflow nodes to consume intermediate token stream chunks
from upstream nodes in real-time before upstream execution completes.
"""

from __future__ import annotations

import asyncio
import json
import uuid
from typing import TYPE_CHECKING, Any, ClassVar

from vortex.observability.logger import get_logger
from vortex.storage.redis import get_redis

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

logger = get_logger(__name__)


class StreamChannel:
    """Inter-node real-time pub/sub streaming manager."""

    _buffers: ClassVar[dict[str, list[dict[str, Any]]]] = {}
    _subscribers: ClassVar[dict[str, list[asyncio.Queue]]] = {}
    _lock: ClassVar[asyncio.Lock] = asyncio.Lock()

    @classmethod
    async def publish_chunk(
        cls,
        run_id: str | uuid.UUID,
        node_id: str,
        chunk: str | dict[str, Any],
        is_final: bool = False,
    ) -> None:
        """
        Publish a streaming chunk to Redis Pub/Sub and in-memory channel subscribers.
        """
        key = f"{run_id}:{node_id}"
        payload = {
            "node_id": node_id,
            "chunk": chunk,
            "is_final": is_final,
        }

        # Redis Pub/Sub attempt
        try:
            client = get_redis()
            channel = f"vortex:stream:{key}"
            await client.publish(channel, json.dumps(payload))
        except Exception:
            pass

        # In-memory buffer & queue notification
        async with cls._lock:
            if key not in cls._buffers:
                cls._buffers[key] = []
            cls._buffers[key].append(payload)

            if key in cls._subscribers:
                for q in cls._subscribers[key]:
                    await q.put(payload)

    @classmethod
    async def subscribe_chunks(
        cls,
        run_id: str | uuid.UUID,
        node_id: str,
        timeout_seconds: float = 10.0,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """
        Yield real-time stream chunks emitted by `node_id`.
        """
        key = f"{run_id}:{node_id}"
        queue: asyncio.Queue = asyncio.Queue()

        async with cls._lock:
            # Yield buffered chunks first
            if key in cls._buffers:
                for item in cls._buffers[key]:
                    await queue.put(item)

            if key not in cls._subscribers:
                cls._subscribers[key] = []
            cls._subscribers[key].append(queue)

        try:
            while True:
                try:
                    payload = await asyncio.wait_for(queue.get(), timeout=timeout_seconds)
                    yield payload
                    if payload.get("is_final"):
                        break
                except TimeoutError:
                    break
        finally:
            async with cls._lock:
                if key in cls._subscribers and queue in cls._subscribers[key]:
                    cls._subscribers[key].remove(queue)

    @classmethod
    def clear_streams(cls) -> None:
        """Clear local stream buffers (for unit tests)."""
        cls._buffers.clear()
        cls._subscribers.clear()
