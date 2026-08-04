"""
Anthropic Claude Provider Adapter.
"""

from __future__ import annotations

from ulid import ULID

from vortex.gateway.providers.base import BaseProvider, CompletionRequest, CompletionResponse
from vortex.observability.logger import get_logger

logger = get_logger(__name__)


class AnthropicProvider(BaseProvider):
    @property
    def provider_name(self) -> str:
        return "anthropic"

    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        logger.info("Executing Anthropic completion request", model=request.model)

        prompt_str = " ".join([m.get("content", "") for m in request.messages])
        tokens_in = len(prompt_str.split())

        content = f"[Anthropic {request.model} Response]: Processed prompt of {tokens_in} words."
        tokens_out = len(content.split())

        cost_usd = (tokens_in * 0.003 / 1000.0) + (tokens_out * 0.015 / 1000.0)

        return CompletionResponse(
            id=f"msg-{ULID()}",
            model=request.model,
            provider="anthropic",
            content=content,
            tokens_input=tokens_in,
            tokens_output=tokens_out,
            cost_usd=cost_usd,
        )
