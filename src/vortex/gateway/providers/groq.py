"""
Groq Provider Adapter.
Uses the OpenAI SDK since Groq provides an OpenAI-compatible API.
"""

from __future__ import annotations

import asyncio

import openai
from ulid import ULID

from vortex.gateway.providers.base import BaseProvider, CompletionRequest, CompletionResponse
from vortex.observability.logger import get_logger

logger = get_logger(__name__)


class GroqProvider(BaseProvider):
    def __init__(self, api_key: str):
        super().__init__(api_key)
        self.client = openai.AsyncOpenAI(
            api_key=self.api_key,
            base_url="https://api.groq.com/openai/v1",
        )

    @property
    def provider_name(self) -> str:
        return "groq"

    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        logger.info("Executing Groq completion request", model=request.model)

        max_retries = 5
        for attempt in range(max_retries):
            try:
                # Groq-specific OpenAI compat response
                res = await self.client.chat.completions.create(
                    model=request.model,
                    messages=request.messages,  # type: ignore
                    temperature=request.temperature,
                    max_tokens=request.max_tokens,
                    stream=request.stream,
                )
                break
            except openai.RateLimitError:
                if attempt < max_retries - 1:
                    wait_time = (2**attempt) * 2  # Exponential backoff
                    logger.warning("Groq rate limit hit, retrying", attempt=attempt, delay=wait_time)
                    await asyncio.sleep(wait_time)
                else:
                    logger.error("Groq rate limit exhausted after retries.")
                    raise

        content = res.choices[0].message.content or ""
        tokens_in = getattr(res.usage, "prompt_tokens", 0)
        tokens_out = getattr(res.usage, "completion_tokens", 0)

        # Groq Llama 3 8B Instant rough cost ($0.05 / 1M tokens in, $0.08 / 1M tokens out)
        cost_usd = (tokens_in * 0.05 / 1_000_000.0) + (tokens_out * 0.08 / 1_000_000.0)

        return CompletionResponse(
            id=res.id if res.id else f"groq-{ULID()}",
            model=request.model,
            provider="groq",
            content=content,
            tokens_input=tokens_in,
            tokens_output=tokens_out,
            cost_usd=cost_usd,
        )
