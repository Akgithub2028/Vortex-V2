"""
OpenAI Provider Adapter.
"""

from __future__ import annotations

from ulid import ULID

from vortex.gateway.providers.base import BaseProvider, CompletionRequest, CompletionResponse
from vortex.observability.logger import get_logger

logger = get_logger(__name__)


class OpenAIProvider(BaseProvider):
    @property
    def provider_name(self) -> str:
        return "openai"

    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        logger.info("Executing OpenAI completion request", model=request.model)

        prompt_str = " ".join([m.get("content", "") for m in request.messages])
        tokens_in = len(prompt_str.split())

        # Response text representation
        content = f"[OpenAI {request.model} Response]: Processed prompt of {tokens_in} words."
        tokens_out = len(content.split())

        # Simple pricing calculation ($0.00015 / 1K in, $0.0006 / 1K out)
        cost_usd = (tokens_in * 0.00015 / 1000.0) + (tokens_out * 0.0006 / 1000.0)

        return CompletionResponse(
            id=f"chatcmpl-{ULID()}",
            model=request.model,
            provider="openai",
            content=content,
            tokens_input=tokens_in,
            tokens_output=tokens_out,
            cost_usd=cost_usd,
        )
