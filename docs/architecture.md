# VoRTeX System Architecture & Technical Deep-Dive

**VoRTeX** is an enterprise-grade AI Systems Execution Engine designed for durable agentic workflows, multi-provider LLM gateway routing, token rate limiting, exact-match prompt caching, safety guardrails, and evaluation gating.

---

## 1. System Architecture Overview

```text
                        ┌──────────────────────────────┐
                        │      Client Application      │
                        └──────────────┬───────────────┘
                                       │ (REST / SSE SDK)
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           VoRTeX REST API Gateway                           │
│  - API Key & RBAC Authentication (Owner / Admin / Member / Viewer)           │
│  - Middleware: Request Tracing & Correlation ID Injection                    │
└──────────────────────────────┬──────────────────────────────┬───────────────┘
                               │                              │
                               ▼                              ▼
┌──────────────────────────────────────────┐     ┌────────────────────────────┐
│      Dynamic Graph Execution Engine      │     │    CQRS Event Projector    │
│  - Kahn's Topological Sort & Validation  │     │  - Append-Only Event Store │
│  - Dynamic Runtime Yielding              │     │  - Read Model Materializer │
│  - Step Limit & Node Timeout Guards      │     │  - HKDF Envelope Encrypt.  │
│  - Cost Budget Limit Enforcement         │     └────────────────────────────┘
└──────────────────────┬───────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Model Gateway Router                              │
│  - Token-Bucket Provider Rate Limiter (40 RPM NIM Limit)                     │
│  - Inline Guardrails Engine (Prompt Injection & PII Redaction)              │
│  - Exact-Match Prompt Response Cache (Redis SHA-256)                         │
│  - Circuit Breakers & Exponential Backoff Fallback Chain                    │
│  - Multi-Provider Adapters: NVIDIA NIM, OpenAI, Anthropic, Google, Groq     │
│  - Structured Output Enforcement (JSON Schema)                              │
└──────────────────────┬──────────────────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                       Evaluation & Telemetry Suite                          │
│  - Faithfulness / Relevance / Toxicity Scorers & Gating (`EvalNode`)        │
│  - Prometheus Metrics (`LLM_REQUESTS`, `LLM_TOKENS`, `LLM_COST_USD`)        │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. CQRS Event-Sourced Orchestration

VoRTeX decouples state mutation from state querying using **Command Query Responsibility Segregation (CQRS)**:

- **Append-Only EventStore (`src/vortex/engine/event_store.py`):** All workflow transitions, node executions, and tool calls are recorded as immutable events in the PostgreSQL `events` table. This provides a complete audit trail and execution time-travel debugging.
- **CQRS State Projector (`src/vortex/engine/projector.py`):** A background materialization process consumes the event stream and projects it into indexed read models (`WorkflowRun` and `NodeRun`).
- **HKDF Payload Encryption (`src/vortex/engine/security.py`):** Sensitive workflow variables and node outputs are encrypted at rest using tenant-isolated HMAC-based Extract-and-Expand Key Derivation Function (HKDF) envelope encryption.

---

## 3. Dynamic Execution Engine & Reliability Controls

The `DynamicGraphExecutor` (`src/vortex/engine/executor.py`) acts as a durable state machine:

1. **Topological Sort:** Validates DAG definitions via Kahn's algorithm to prevent cycles.
2. **Runtime Task Yielding:** Workflows can yield mid-execution (`yield_task`), freezing and checkpointing state to PostgreSQL JSONB while freeing worker threads.
3. **Reliability Gates:**
   - **Step Limit:** Enforces a maximum step cap (default 50) to prevent infinite loops in dynamic DAGs.
   - **Cost Budget Cap:** Enforces cost cap (`max_budget_usd`) halting execution if token cost accumulates beyond budget.
   - **Node Execution Timeout:** Wraps node executions with `asyncio.wait_for(node.execute(state), timeout=node_timeout)`.

---

## 4. Model Gateway & Provider Routing

VoRTeX sits between application logic and LLM provider endpoints:

- **NVIDIA NIM Integration (`NVIDIANIMProvider`):** Executes completions via `httpx` REST calls against NVIDIA NIM's OpenAI-compatible endpoint (`https://integrate.api.nvidia.com/v1/chat/completions`).
- **Token-Bucket Rate Limiter (`ProviderRateLimiter`):** Sliding-window rate limiter enforcing rate limits (e.g. 40 RPM limit for NIM) using Redis with in-memory fallback.
- **Circuit Breakers & Exponential Backoff:** Trips circuit breakers on consecutive provider errors and executes exponential backoff retries.
- **Exact-Match Response Caching (`GatewayCache`):** SHA-256 prompt hashing returns cached LLM responses in `< 2ms`.
- **Structured Output Support:** Enforces JSON Schema parameters (`response_format={"type": "json_schema", ...}`) on provider completions.

---

## 5. Type-Safe Tool Registry

The `ToolRegistry` (`src/vortex/engine/tools/registry.py`) manages tool registration and execution:

- **Registration:** Accepts functions with metadata descriptions and JSON parameter schemas.
- **Built-in Tools:**
  - `text_processor`: String formatting and length metrics.
  - `json_extractor`: Safe JSON parsing and key extraction.
  - `web_search_stub`: Mock factual web search returning structured result objects.
- **ToolNode Wiring:** Resolves variable placeholders (`$var`) against workflow state and executes registered tools asynchronously.

---

## 6. Evaluation Framework & Quality Gating

Evaluation is an inline execution primitive inside VoRTeX (`EvalNode`):

- **Scorers:** `FaithfulnessScorer`, `RelevanceScorer`, `ToxicityScorer`.
- **Gate Actions:** `warn` (log metrics) or `block` (raise `EvalGateError`).
- **Batch Evaluation Runner:** Process JSONL benchmark datasets (`EvaluationRunner`) and materializes summaries to `eval_results` table.
- **Prometheus Metrics:** Emits `LLM_REQUESTS_TOTAL`, `LLM_LATENCY_SECONDS`, `LLM_TOKENS_TOTAL`, `LLM_COST_USD_TOTAL`, and `EVAL_GATE_RESULTS_TOTAL`.
