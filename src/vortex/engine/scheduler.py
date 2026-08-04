"""
Vortex Task Scheduler — priority queue management, delayed retries, and task dispatch via Redis.
"""

from __future__ import annotations

import json
import uuid
from typing import TYPE_CHECKING, Any

from vortex.observability.logger import get_logger
from vortex.storage.redis import get_redis

logger = get_logger(__name__)


class TaskScheduler:
    """Redis-backed task scheduler for workflow execution dispatch."""

    STREAM_KEY = "vortex:tasks:queue"
    DLQ_STREAM_KEY = "vortex:tasks:dlq"

    @classmethod
    async def enqueue_workflow(
        cls,
        run_id: uuid.UUID,
        tenant_id: uuid.UUID,
        priority: int = 0,
    ) -> str:
        """Enqueue a workflow run task to Redis Stream."""
        redis = get_redis()
        message = {
            "run_id": str(run_id),
            "tenant_id": str(tenant_id),
            "priority": str(priority),
        }
        msg_id = await redis.xadd(cls.STREAM_KEY, message)
        logger.info("Enqueued workflow task to Redis Stream", run_id=str(run_id), msg_id=msg_id)
        return msg_id

    @classmethod
    async def enqueue_dlq(
        cls,
        run_id: uuid.UUID,
        node_id: str,
        error: str,
        payload: dict[str, Any],
    ) -> str:
        """Move an exhausted failed task to Dead Letter Queue."""
        redis = get_redis()
        message = {
            "run_id": str(run_id),
            "node_id": node_id,
            "error": error,
            "payload": json.dumps(payload),
        }
        msg_id = await redis.xadd(cls.DLQ_STREAM_KEY, message)
        logger.warning("Moved task to Dead Letter Queue", run_id=str(run_id), node_id=node_id, msg_id=msg_id)
        return msg_id
