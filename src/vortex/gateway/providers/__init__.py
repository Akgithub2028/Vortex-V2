"""
Providers factory and exports.
"""

from __future__ import annotations

from vortex.gateway.providers.anthropic import AnthropicProvider
from vortex.gateway.providers.base import BaseProvider, CompletionRequest, CompletionResponse
from vortex.gateway.providers.google import GoogleProvider
from vortex.gateway.providers.groq import GroqProvider
from vortex.gateway.providers.local import LocalProvider
from vortex.gateway.providers.nvidia_nim import NVIDIANIMProvider
from vortex.gateway.providers.openai import OpenAIProvider


def get_provider(provider_name: str, api_key: str = "") -> BaseProvider:
    provider_name = provider_name.lower()
    if provider_name in ("nvidia", "nvidia_nim", "nim"):
        return NVIDIANIMProvider(api_key)
    elif provider_name == "openai":
        return OpenAIProvider(api_key)
    elif provider_name == "anthropic":
        return AnthropicProvider(api_key)
    elif provider_name == "google":
        return GoogleProvider(api_key)
    elif provider_name == "local":
        return LocalProvider(api_key)
    elif provider_name == "groq":
        return GroqProvider(api_key)
    else:
        # Default fallback to OpenAI provider wrapper
        return OpenAIProvider(api_key)


__all__ = [
    "AnthropicProvider",
    "BaseProvider",
    "CompletionRequest",
    "CompletionResponse",
    "GoogleProvider",
    "GroqProvider",
    "LocalProvider",
    "NVIDIANIMProvider",
    "OpenAIProvider",
    "get_provider",
]
