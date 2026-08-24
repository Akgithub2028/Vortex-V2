# ADR 004: Circuit Breaker & Provider Fallback Routing

- **Status:** Accepted
- **Date:** 2026-08-24
- **Context:** LLM provider APIs frequently experience rate limits (HTTP 429), temporary outages (5xx), or high latency. A failure in a primary provider must not crash running production workflows.

## Decision
We implement a **Resilient Provider Fallback Chain with Token-Bucket Rate Limiting & Circuit Breaking**:

1. **Provider Rate Limiter:** `ProviderRateLimiter` enforces sliding-window rate limits (40 RPM limit for NVIDIA NIM).
2. **Circuit Breakers (`CircuitBreaker`):** Tracks consecutive provider failures. After 5 failures, trips to `OPEN` state for a 30-second recovery window, bypassing dead endpoints immediately.
3. **Exponential Backoff:** Requests encountering transient failures undergo exponential retries before triggering fallback provider models in the routing chain.

## Consequences
- **Pros:** High availability, seamless failover from primary models (NVIDIA NIM) to backup providers (OpenAI / Anthropic), prevention of cascading timeouts.
- **Cons:** Fallback models may have slightly different completion characteristics or cost profiles.
