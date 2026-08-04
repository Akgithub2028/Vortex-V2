"""
Unit tests for Google, Groq, and Local providers using mock API clients.
Coverage boost for vortex.gateway.providers module.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import openai
import pytest
from google.genai.errors import APIError

from vortex.gateway.providers.base import CompletionRequest
from vortex.gateway.providers.google import GoogleProvider
from vortex.gateway.providers.groq import GroqProvider
from vortex.gateway.providers.local import LocalProvider


@pytest.mark.asyncio
async def test_google_provider_success():
    provider = GoogleProvider(api_key="mock-key")
    assert provider.provider_name == "google"

    mock_resp = MagicMock()
    mock_resp.text = "Mocked Google output"

    with patch.object(provider.client.aio.models, "generate_content", new_callable=AsyncMock, return_value=mock_resp):
        req = CompletionRequest(
            model="gemini-2.0-flash",
            messages=[
                {"role": "system", "content": "You are helpful"},
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi there"},
            ],
            temperature=0.7,
            max_tokens=100,
        )
        res = await provider.complete(req)
        assert res.provider == "google"
        assert res.content == "Mocked Google output"
        assert res.cost_usd > 0


@pytest.mark.asyncio
async def test_google_provider_rate_limit_retry():
    provider = GoogleProvider(api_key="mock-key")

    mock_resp = MagicMock()
    mock_resp.text = "Eventual Google output"

    err_429 = APIError("Rate limit hit", response_json={"error": {"code": 429}})
    err_429.code = 429

    with (
        patch.object(provider.client.aio.models, "generate_content", new_callable=AsyncMock, side_effect=[err_429, mock_resp]),
        patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep,
    ):
        req = CompletionRequest(
            model="gemini-2.0-flash",
            messages=[{"role": "user", "content": "Test"}],
        )
        res = await provider.complete(req)
        assert res.content == "Eventual Google output"
        mock_sleep.assert_called_once_with(20)


@pytest.mark.asyncio
async def test_groq_provider_success():
    provider = GroqProvider(api_key="mock-groq-key")
    assert provider.provider_name == "groq"

    mock_msg = MagicMock()
    mock_msg.content = "Groq Llama 3 output"

    mock_choice = MagicMock()
    mock_choice.message = mock_msg

    mock_usage = MagicMock()
    mock_usage.prompt_tokens = 20
    mock_usage.completion_tokens = 30

    mock_completion = MagicMock()
    mock_completion.choices = [mock_choice]
    mock_completion.usage = mock_usage
    mock_completion.id = "groq-test-123"

    with patch.object(provider.client.chat.completions, "create", new_callable=AsyncMock, return_value=mock_completion):
        req = CompletionRequest(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": "Explain AI"}],
        )
        res = await provider.complete(req)
        assert res.provider == "groq"
        assert res.content == "Groq Llama 3 output"
        assert res.tokens_input == 20
        assert res.tokens_output == 30
        assert res.cost_usd > 0


@pytest.mark.asyncio
async def test_groq_provider_rate_limit_retry():
    provider = GroqProvider(api_key="mock-groq-key")

    mock_msg = MagicMock()
    mock_msg.content = "Groq output after retry"

    mock_choice = MagicMock()
    mock_choice.message = mock_msg

    mock_completion = MagicMock()
    mock_completion.choices = [mock_choice]
    mock_completion.usage = None
    mock_completion.id = None

    rate_limit_err = openai.RateLimitError(message="Rate limit exceeded", response=MagicMock(status_code=429), body=None)

    with (
        patch.object(provider.client.chat.completions, "create", new_callable=AsyncMock, side_effect=[rate_limit_err, mock_completion]),
        patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep,
    ):
        req = CompletionRequest(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": "Test"}],
        )
        res = await provider.complete(req)
        assert res.content == "Groq output after retry"
        mock_sleep.assert_called_once()


@pytest.mark.asyncio
async def test_local_provider_complete():
    provider = LocalProvider("mock-key")
    assert provider.provider_name == "local"

    req = CompletionRequest(
        model="llama3-local",
        messages=[{"role": "user", "content": "Hello local LLM"}],
    )
    res = await provider.complete(req)
    assert res.provider == "local"
    assert res.cost_usd == 0.0
    assert "Processed prompt of 3 words" in res.content
