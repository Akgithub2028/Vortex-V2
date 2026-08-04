"""
Semantic and Exact Cache for Model Gateway.

Gracefully degrades on Redis connection errors so gateway execution never crashes.
"""

from __future__ import annotations

import hashlib
import json

from vortex.gateway.providers.base import CompletionRequest, CompletionResponse
from vortex.observability.logger import get_logger
from vortex.storage.redis import get_redis

logger = get_logger(__name__)


class GatewayCache:
    @staticmethod
    def _compute_key(request: CompletionRequest) -> str:
        prompt_str = json.dumps(request.messages, sort_keys=True)
        raw = f"{request.model}:{prompt_str}:{request.temperature}"
        return f"cache:llm:{hashlib.sha256(raw.encode('utf-8')).hexdigest()}"

    @classmethod
    async def get(cls, request: CompletionRequest) -> CompletionResponse | None:
        try:
            redis = get_redis()
            key = cls._compute_key(request)
            data = await redis.get(key)
            if data:
                logger.info("Cache hit for LLM request", key=key)
                resp_dict = json.loads(data)
                return CompletionResponse.model_validate(resp_dict)
        except Exception as e:
            logger.warning("Cache get error (degrading to cache miss)", error=str(e))
        return None

    @classmethod
    async def set(cls, request: CompletionRequest, response: CompletionResponse, ttl: int = 3600) -> None:
        try:
            redis = get_redis()
            key = cls._compute_key(request)
            await redis.set(key, json.dumps(response.model_dump(mode="json")), ex=ttl)
        except Exception as e:
            logger.warning("Cache set error", error=str(e))
