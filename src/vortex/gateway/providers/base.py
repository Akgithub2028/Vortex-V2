"""
Abstract Base Provider interface for Model Gateway.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from typing import Any

from pydantic import BaseModel


class CompletionRequest(BaseModel):
    model: str
    messages: list[dict[str, str]]
    temperature: float = 0.7
    max_tokens: int | None = None
    stream: bool = False
    response_format: dict[str, Any] | None = None


class CompletionResponse(BaseModel):
    id: str
    model: str
    provider: str
    content: str
    tokens_input: int
    tokens_output: int
    cost_usd: float
    finish_reason: str = "stop"


class BaseProvider(ABC):
    """Abstract interface for LLM provider adapters."""

    def __init__(self, api_key: str):
        self.api_key = api_key

    @property
    @abstractmethod
    def provider_name(self) -> str:
        pass

    @abstractmethod
    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        """Send completion request to provider API."""
        pass
