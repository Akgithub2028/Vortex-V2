"""
Unit tests for NVIDIA NIM Provider, RateLimiter, and LLMNode-ModelRouter integration.
"""

from __future__ import annotations

import uuid

import pytest

from vortex.engine.nodes import create_node
from vortex.engine.state import NodeDefinition, WorkflowState
from vortex.gateway.providers.base import CompletionRequest
from vortex.gateway.providers.nvidia_nim import NVIDIANIMProvider
from vortex.gateway.rate_limiter import ProviderRateLimiter
from vortex.gateway.router import ModelRouter

TEST_RUN_ID = uuid.uuid4()
TEST_TENANT_ID = uuid.uuid4()


@pytest.mark.asyncio
async def test_nvidia_nim_provider_completion():
    provider = NVIDIANIMProvider(api_key="mock-key")
    req = CompletionRequest(
        model="nvidia/meta/llama-3.1-70b-instruct",
        messages=[{"role": "user", "content": "Explain vector indexing"}],
    )
    resp = await provider.complete(req)

    assert resp.provider == "nvidia"
    assert resp.model == "nvidia/meta/llama-3.1-70b-instruct"
    assert "NVIDIA NIM" in resp.content
    assert resp.tokens_input > 0
    assert resp.cost_usd >= 0.0


@pytest.mark.asyncio
async def test_provider_rate_limiter():
    ProviderRateLimiter.reset()

    # Should allow up to max_rpm calls
    allowed_count = 0
    for _ in range(40):
        if await ProviderRateLimiter.acquire("nvidia", max_rpm=40):
            allowed_count += 1

    assert allowed_count == 40

    # 41st call should be blocked by rate limit
    blocked = not await ProviderRateLimiter.acquire("nvidia", max_rpm=40)
    assert blocked

    ProviderRateLimiter.reset()


@pytest.mark.asyncio
async def test_llm_node_wired_to_model_router():
    ProviderRateLimiter.reset()
    node_def = NodeDefinition(
        id="llm1",
        type="llm",
        config={
            "prompt": "Summarize {topic}",
            "model": "nvidia/meta/llama-3.1-70b-instruct",
            "system_prompt": "You are a research assistant.",
        },
    )
    node = create_node(node_def)
    state = WorkflowState(
        run_id=TEST_RUN_ID,
        tenant_id=TEST_TENANT_ID,
        variables={"topic": "Quantum Computing"},
    )

    output = await node.execute(state)

    assert "text" in output
    assert output["provider"] == "nvidia"
    assert output["model"] == "nvidia/meta/llama-3.1-70b-instruct"
    assert state.total_tokens > 0
    assert state.total_cost_usd >= 0.0
