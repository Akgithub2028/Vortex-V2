# ADR 002: Centralized LLM Gateway Abstraction

- **Status:** Accepted
- **Date:** 2026-08-24
- **Context:** Direct integration of model provider SDKs (OpenAI, Anthropic, NVIDIA NIM) within workflow code leads to code duplication, inconsistent error handling, lack of token rate limiting, and zero visibility into costs and safety risks.

## Decision
We decouple model providers from workflow business logic by introducing a central **Model Gateway Router (`ModelRouter`)**:

1. **Unified Completion Request API:** All LLM nodes send `CompletionRequest` objects to `ModelRouter.complete()`.
2. **Provider Adapters:** `NVIDIANIMProvider`, `OpenAIProvider`, `AnthropicProvider`, `GoogleProvider`, `GroqProvider`, `LocalProvider`.
3. **Cross-Cutting Concerns:** Inline guardrail scanning, token-bucket rate limiting (40 RPM limit for NIM), exact-match response caching, circuit breaking, and Prometheus cost/latency metrics.

## Consequences
- **Pros:** Zero provider lock-in, centralized safety enforcement, dynamic fallback chains, real token & cost tracking.
- **Cons:** Central gateway becomes a critical dependency (mitigated by circuit breakers & fallback routing).
