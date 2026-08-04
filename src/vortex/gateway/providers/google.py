"""
Google Gemini Provider Adapter.
"""

from __future__ import annotations

from google import genai
from google.genai import types
from ulid import ULID

from vortex.gateway.providers.base import BaseProvider, CompletionRequest, CompletionResponse
from vortex.observability.logger import get_logger

logger = get_logger(__name__)


class GoogleProvider(BaseProvider):
    def __init__(self, api_key: str):
        super().__init__(api_key)
        self.client = genai.Client(api_key=self.api_key)

    @property
    def provider_name(self) -> str:
        return "google"

    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        logger.info("Executing Google completion request", model=request.model)

        contents = []
        for msg in request.messages:
            role = msg.get("role", "user")
            # Convert system role to user for simple implementation, or map appropriately.
            if role == "system":
                role = "user"
            elif role == "assistant":
                role = "model"
            contents.append(types.Content(role=role, parts=[types.Part.from_text(text=msg.get("content", ""))]))

        config = types.GenerateContentConfig(
            temperature=request.temperature,
            max_output_tokens=request.max_tokens,
        )

        import asyncio

        from google.genai.errors import APIError

        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = await self.client.aio.models.generate_content(
                    model=request.model,
                    contents=contents,
                    config=config,
                )
                break
            except APIError as e:
                if e.code == 429 and attempt < max_retries - 1:
                    logger.warning("Rate limit hit, retrying", attempt=attempt, delay=20)
                    await asyncio.sleep(20)
                else:
                    raise

        content = response.text if response.text else ""

        # Very rough cost estimation for Gemini Flash
        tokens_in = len(str(contents)) // 4
        tokens_out = len(content) // 4
        cost_usd = (tokens_in * 0.000075 / 1000.0) + (tokens_out * 0.0003 / 1000.0)

        return CompletionResponse(
            id=f"genai-{ULID()}",
            model=request.model,
            provider="google",
            content=content,
            tokens_input=tokens_in,
            tokens_output=tokens_out,
            cost_usd=cost_usd,
        )
