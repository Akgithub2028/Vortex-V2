"""
Unit tests for Model Gateway Router and Provider Adapters.
"""

import pytest

from vortex.gateway.cost_tracker import calculate_cost
from vortex.gateway.providers import (
    AnthropicProvider,
    GoogleProvider,
    LocalProvider,
    OpenAIProvider,
    get_provider,
)
from vortex.gateway.providers.base import CompletionRequest
from vortex.gateway.router import ModelRouter


def test_cost_calculation():
    cost_gpt4o = calculate_cost("openai/gpt-4o", 1000, 1000)
    assert cost_gpt4o == pytest.approx(0.0125)

    cost_mini = calculate_cost("openai/gpt-4o-mini", 1000, 1000)
    assert cost_mini == pytest.approx(0.00075)


def test_provider_factory():
    openai = get_provider("openai", "mock-key")
    assert isinstance(openai, OpenAIProvider)

    anthropic = get_provider("anthropic", "mock-key")
    assert isinstance(anthropic, AnthropicProvider)

    google = get_provider("google", "mock-key")
    assert isinstance(google, GoogleProvider)

    local = get_provider("local", "mock-key")
    assert isinstance(local, LocalProvider)


@pytest.mark.skip(reason="Requires API Keys")
@pytest.mark.asyncio
async def test_all_providers_completion():
    req = CompletionRequest(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "Explain quantum physics"}],
    )

    openai_resp = await OpenAIProvider("mock-key").complete(req)
    assert openai_resp.provider == "openai"
    assert openai_resp.cost_usd > 0

    anthropic_resp = await AnthropicProvider("mock-key").complete(req)
    assert anthropic_resp.provider == "anthropic"
    assert anthropic_resp.cost_usd > 0

    google_resp = await GoogleProvider("mock-key").complete(req)
    assert google_resp.provider == "google"
    assert google_resp.cost_usd > 0

    local_resp = await LocalProvider("mock-key").complete(req)
    assert local_resp.provider == "local"
    assert local_resp.cost_usd == 0.0


@pytest.mark.asyncio
async def test_model_router_completion():
    router = ModelRouter()
    req = CompletionRequest(
        model="openai/gpt-4o-mini",
        messages=[{"role": "user", "content": "Explain quantum computing."}],
    )

    response = await router.complete(req, use_cache=False)
    assert response.provider == "openai"
    assert "Response" in response.content
    assert response.cost_usd > 0


@pytest.mark.asyncio
async def test_model_router_circuit_breaker_open():
    """When circuit breaker is OPEN, router should skip that provider and use fallback."""
    router = ModelRouter()
    req = CompletionRequest(
        model="openai/gpt-4o-mini",
        messages=[{"role": "user", "content": "Test"}],
    )

    # Trip the circuit breaker for openai
    cb = router._get_circuit_breaker("openai")
    for _ in range(10):
        cb.record_failure()

    # Should still work via fallback providers
    response = await router.complete(req, use_cache=False)
    assert response is not None


@pytest.mark.asyncio
async def test_model_router_cache_hit():
    """Cache hit should return cached response without calling provider."""
    from unittest.mock import AsyncMock, patch

    from vortex.gateway.providers.base import CompletionResponse

    router = ModelRouter()
    req = CompletionRequest(
        model="openai/gpt-4o-mini",
        messages=[{"role": "user", "content": "Cache test"}],
    )

    cached_resp = CompletionResponse(
        id="test-cache-id",
        content="Cached!",
        provider="openai",
        model="gpt-4o-mini",
        tokens_input=5,
        tokens_output=10,
        cost_usd=0.001,
    )

    with patch("vortex.gateway.router.GatewayCache.get", new_callable=AsyncMock, return_value=cached_resp):
        response = await router.complete(req, use_cache=True)
        assert response.content == "Cached!"


@pytest.mark.asyncio
async def test_model_router_all_providers_fail():
    """When all providers fail, router should raise RuntimeError."""
    from unittest.mock import AsyncMock, patch

    router = ModelRouter()
    req = CompletionRequest(
        model="unknown/fake-model",
        messages=[{"role": "user", "content": "Test"}],
    )

    with patch("vortex.gateway.router.get_provider") as mock_prov:
        mock_instance = AsyncMock()
        mock_instance.complete = AsyncMock(side_effect=RuntimeError("Provider down"))
        mock_prov.return_value = mock_instance

        with pytest.raises(RuntimeError, match="All model providers failed"):
            await router.complete(req, use_cache=False, fallback_chain=[])
