"""
Unit tests for Vortex Phase 9: KV-Cache Affinity Router and Inter-Node Real-time Streaming Pub/Sub.
"""

import asyncio
import pytest
import uuid

from vortex.engine.streaming import StreamChannel
from vortex.gateway.affinity import KVCacheAffinityRouter, compute_prefix_hash


@pytest.mark.asyncio
async def test_kv_cache_prefix_affinity_hashing():
    KVCacheAffinityRouter.clear_cache()

    messages1 = [
        {"role": "system", "content": "You are a helpful assistant specialized in AI systems."},
        {"role": "user", "content": "Explain KV-Cache Affinity routing in detail."},
    ]
    messages2 = [
        {"role": "system", "content": "You are a helpful assistant specialized in AI systems."},
        {"role": "user", "content": "Explain KV-Cache Affinity routing in detail with code examples."},
    ]

    hash1 = compute_prefix_hash(messages1)
    hash2 = compute_prefix_hash(messages2)

    assert len(hash1) == 16
    assert isinstance(hash1, str)
    # Prefixes overlap on system prompt + prompt start
    assert hash1 == hash2

    replicas = ["replica-gpu-1.internal:8000", "replica-gpu-2.internal:8000", "replica-gpu-3.internal:8000"]
    route1 = await KVCacheAffinityRouter.get_affinity_route(hash1, replicas)
    assert route1 in replicas

    # Register affinity binding
    await KVCacheAffinityRouter.register_affinity(hash1, "replica-gpu-2.internal:8000")
    route2 = await KVCacheAffinityRouter.get_affinity_route(hash1, replicas)
    assert route2 == "replica-gpu-2.internal:8000"


@pytest.mark.asyncio
async def test_inter_node_streaming_pubsub():
    StreamChannel.clear_streams()

    run_id = str(uuid.uuid4())
    node_id = "upstream_llm"

    received_chunks = []

    async def subscriber_task():
        async for item in StreamChannel.subscribe_chunks(run_id, node_id, timeout_seconds=1.0):
            received_chunks.append(item["chunk"])

    sub_task = asyncio.create_task(subscriber_task())
    await asyncio.sleep(0.05)

    # Upstream node emits chunks
    await StreamChannel.publish_chunk(run_id, node_id, "Token1 ")
    await StreamChannel.publish_chunk(run_id, node_id, "Token2 ")
    await StreamChannel.publish_chunk(run_id, node_id, "Token3", is_final=True)

    await sub_task

    assert received_chunks == ["Token1 ", "Token2 ", "Token3"]
