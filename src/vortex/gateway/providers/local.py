"""
Local Provider Adapter (vLLM / Ollama).
"""

from __future__ import annotations

from ulid import ULID

from vortex.gateway.providers.base import BaseProvider, CompletionRequest, CompletionResponse
from vortex.observability.logger import get_logger

logger = get_logger(__name__)


class LocalProvider(BaseProvider):
    @property
    def provider_name(self) -> str:
        return "local"

    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        logger.info("Executing Local completion request", model=request.model)

        prompt_str = " ".join([m.get("content", "") for m in request.messages])
        tokens_in = len(prompt_str.split())

        content = f"[Local {request.model} Response]: Processed prompt of {tokens_in} words."
        tokens_out = len(content.split())

        # Local model cost is 0
        cost_usd = 0.0

        return CompletionResponse(
            id=f"local-{ULID()}",
            model=request.model,
            provider="local",
            content=content,
            tokens_input=tokens_in,
            tokens_output=tokens_out,
            cost_usd=cost_usd,
        )
