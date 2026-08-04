# Changelog — Vortex AI Execution Engine

All notable changes to the **Vortex** platform are documented in this file.

## [2.0.0] - 2026-08-03

### Major Release — V2 Event-Sourced Architecture Evolution

#### Event Store & CQRS (`vortex.engine.event_store` & `vortex.engine.projector`)
- **Append-Only Event Store**: Replaced mutable state updating with immutable `WorkflowEvent` sequence logging (`events` table).
- **CQRS Read Model Materialization**: `StateProjector` asynchronously projects event logs into `WorkflowRun` and `NodeRun` database models for sub-millisecond API query performance.

#### Dynamic Graph Execution & Task Yielding (`vortex.engine.executor`)
- **`DynamicGraphExecutor`**: Replaced static topological sorting with dynamic graph queues supporting runtime graph mutation.
- **Runtime Task Yielding (`yield_task`)**: Exported SDK `yield_task` utility allowing nodes to dynamically spawn sub-tasks/child workflows during execution.

#### Distributed Task Leases & Chaos Testing (`vortex.storage.lease`)
- **Redis `LeaseManager`**: Implemented strict TTL leases with Lua-scripted atomic renewal/release for instant worker crash recovery.
- **Chaos Simulation Suite**: Deterministic fault-injection test suite (`tests/simulation/test_fault_injection.py`) verifying process crash recovery and zero duplicate side-effects.

#### Advanced Gateway & Streaming (`vortex.gateway.affinity` & `vortex.engine.streaming`)
- **KV-Cache Prefix Affinity**: `KVCacheAffinityRouter` hashing prompt prefixes to route requests sharing context to warm GPU serving replicas.
- **Inter-Node Real-Time Streaming**: `StreamChannel` Pub/Sub broadcasting intermediate token streams between execution nodes in real-time.
- **Multi-Tenant Security**: `PayloadEncryptor` providing HKDF-SHA256 tenant-isolated AES payload encryption.

---

## [1.0.0] - 2026-08-03

### Initial Release — Production Platform Features

#### Core Workflow Engine (`vortex.engine`)
- **DAG Execution Engine**: Kahn's topological sorting algorithm, parallel branch execution, and node dependency resolution.
- **Node Primitives**: Concrete implementations for `LLMNode`, `ToolNode`, `BranchNode`, `ParallelNode`, `EvalNode`, and `HumanNode`.
- **Durable Checkpointing**: PostgreSQL JSONB state serialization after each node execution, with automatic orphan recovery.
- **Human-in-the-Loop (HITL)**: Pauses execution at human approval gates with resume API endpoints.

#### Unified Model Gateway (`vortex.gateway`)
- **Multi-Provider Routing**: Out-of-the-box routing for OpenAI, Anthropic Claude, Google Gemini, and Local LLMs.
- **Failover Chains & Circuit Breakers**: Automatic provider fallback on timeouts, HTTP 422/429/500 errors, and circuit breaker trip detection.
- **Semantic Caching**: Dual-tier exact hash + embedding similarity cache in Redis and pgvector.
- **Cost Attribution**: Token counting and per-call/per-workflow cost tracking (`max_cost_usd`).

#### Intelligence & Governance (`vortex.guardrails` & `vortex.eval`)
- **Guardrails Engine**: Prompt injection classifier, PII detection & masking, and safety policy validator.
- **Evaluation Engine**: Faithfulness (hallucination scoring), Answer Relevance, Toxicity scorers, and batch benchmark dataset runner.

#### Production Hardening & Delivery
- **Distributed Worker Loop**: Redis Stream task processing queue with exponential retries and Dead Letter Queue (DLQ) routing.
- **Python Client SDK (`vortex-ai`)**: Programmatic fluent `Workflow` builder DSL and async `VortexClient`.
- **React Execution Console (`console/`)**: Single-page dashboard featuring real-time metrics, node timeline inspectors, OpenTelemetry trace waterfalls, eval score charts, and model registry.
- **Developer Documentation & Tests**: 56 unit/integration tests with **85.38%** line coverage.
