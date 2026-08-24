"""
Model Gateway Router — provider selection, fallback routing chain, guardrail inspection, and circuit breaker evaluation.
"""

from __future__ import annotations

import asyncio
import time
from typing import TYPE_CHECKING

from vortex.config import get_settings
from vortex.gateway.cache import GatewayCache
from vortex.gateway.circuit_breaker import CircuitBreaker
from vortex.gateway.providers import get_provider
from vortex.gateway.rate_limiter import ProviderRateLimiter
from vortex.guardrails import GuardrailsEngine
from vortex.observability.logger import get_logger
from vortex.observability.metrics import (
    LLM_CACHE_HITS_TOTAL,
    LLM_CACHE_MISSES_TOTAL,
    LLM_COST_USD_TOTAL,
    LLM_LATENCY_SECONDS,
    LLM_REQUESTS_TOTAL,
    LLM_TOKENS_TOTAL,
)

if TYPE_CHECKING:
    from vortex.gateway.providers.base import CompletionRequest, CompletionResponse

logger = get_logger(__name__)


class ModelRouter:
    """Central router for LLM completion requests."""

    def __init__(self):
        self.circuit_breakers: dict[str, CircuitBreaker] = {}
        self.guardrails_engine = GuardrailsEngine()

    def _get_circuit_breaker(self, provider_name: str) -> CircuitBreaker:
        if provider_name not in self.circuit_breakers:
            self.circuit_breakers[provider_name] = CircuitBreaker()
        return self.circuit_breakers[provider_name]

    async def complete(
        self,
        request: CompletionRequest,
        fallback_chain: list[str] | None = None,
        use_cache: bool = True,
    ) -> CompletionResponse:
        settings = get_settings()

        # Run Inline Guardrails
        if settings.guardrails_enabled:
            scrubbed_messages = []
            action = settings.guardrails_default_action  # warn | block
            for msg in request.messages:
                content = msg.get("content", "")
                scrubbed_content, _ = await self.guardrails_engine.inspect(content, action=action)  # type: ignore
                scrubbed_messages.append({"role": msg.get("role", "user"), "content": scrubbed_content})
            request = request.model_copy(update={"messages": scrubbed_messages})

        # Check Cache
        if use_cache and settings.cache_enabled:
            cached_resp = await GatewayCache.get(request)
            if cached_resp:
                LLM_CACHE_HITS_TOTAL.labels(cache_type="exact").inc()
                return cached_resp
            LLM_CACHE_MISSES_TOTAL.labels(cache_type="exact").inc()

        # Build fallback list
        models_to_try = [request.model]
        if fallback_chain:
            models_to_try.extend(fallback_chain)
        else:
            default_fallbacks = [m.strip() for m in settings.default_fallback_models.split(",") if m.strip()]
            for f_model in default_fallbacks:
                if f_model != request.model:
                    models_to_try.append(f_model)

        last_error = None
        for target_model in models_to_try:
            provider_name = target_model.split("/")[0] if "/" in target_model else "openai"
            cb = self._get_circuit_breaker(provider_name)

            if not cb.allow_request():
                logger.warning("Circuit breaker OPEN, skipping provider", provider=provider_name)
                continue

            # Check rate limiter
            if not await ProviderRateLimiter.acquire(provider_name):
                logger.warning("Provider rate limit reached, trying next model in chain", provider=provider_name)
                continue

            # Retry loop per provider
            max_retries = settings.gateway_max_retries
            base_delay = settings.gateway_base_delay_seconds

            for attempt in range(1, max_retries + 1):
                start_time = time.perf_counter()
                try:
                    # Prepare provider
                    api_key = getattr(settings, f"{provider_name}_api_key", "")
                    provider = get_provider(provider_name, api_key)

                    from vortex.gateway.affinity import KVCacheAffinityRouter, compute_prefix_hash

                    prefix_hash = compute_prefix_hash(request.messages)
                    req = request.model_copy(update={"model": target_model})
                    response = await provider.complete(req)
                    elapsed_seconds = time.perf_counter() - start_time
                    latency_ms = int(elapsed_seconds * 1000)

                    cb.record_success()

                    # Record metrics & logs
                    LLM_REQUESTS_TOTAL.labels(provider=provider_name, model=target_model, status="success").inc()
                    LLM_LATENCY_SECONDS.labels(provider=provider_name, model=target_model).observe(elapsed_seconds)
                    LLM_TOKENS_TOTAL.labels(provider=provider_name, model=target_model, direction="input").inc(response.tokens_input)
                    LLM_TOKENS_TOTAL.labels(provider=provider_name, model=target_model, direction="output").inc(response.tokens_output)
                    LLM_COST_USD_TOTAL.labels(provider=provider_name, model=target_model).inc(response.cost_usd)

                    logger.info(
                        "LLM completion call succeeded",
                        provider=provider_name,
                        model=target_model,
                        tokens_in=response.tokens_input,
                        tokens_out=response.tokens_output,
                        cost_usd=response.cost_usd,
                        latency_ms=latency_ms,
                    )

                    # Register KV-cache affinity binding
                    await KVCacheAffinityRouter.register_affinity(prefix_hash, target_model)

                    # Cache response
                    if use_cache and settings.cache_enabled:
                        await GatewayCache.set(request, response, ttl=settings.cache_ttl_seconds)

                    return response

                except Exception as e:
                    elapsed_seconds = time.perf_counter() - start_time
                    logger.warning(
                        "Provider call attempt failed",
                        provider=provider_name,
                        model=target_model,
                        attempt=attempt,
                        max_retries=max_retries,
                        error=str(e),
                    )
                    last_error = e

                    if attempt < max_retries:
                        await asyncio.sleep(base_delay * (2 ** (attempt - 1)))
                    else:
                        cb.record_failure()
                        LLM_REQUESTS_TOTAL.labels(provider=provider_name, model=target_model, status="error").inc()

        raise RuntimeError(f"All model providers failed in router chain. Last error: {last_error}")
