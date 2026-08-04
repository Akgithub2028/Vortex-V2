# Vortex Architecture & System Design

**Vortex** is a production-grade AI Execution Engine built for durable LLM workflow execution, gateway model routing, semantic caching, safety guardrails, and evaluation gates.

---

## 1. CQRS Event-Sourced Orchestration

Vortex decouples state mutation from state querying using the **Command Query Responsibility Segregation (CQRS)** pattern.

- **Append-Only EventStore**: All workflow transitions, node executions, and tool calls are recorded as immutable events in the PostgreSQL `events` table. This provides a complete cryptographic audit trail and the ability to time-travel debug executions.
- **Dynamic DAG Executor**: The execution engine acts as the command handler. It reads the current state, executes the next topological node in the Directed Acyclic Graph (DAG), and emits new events.
- **CQRS State Projector**: A background materialization process consumes the event stream and projects it into heavily indexed read models (`WorkflowRun` and `NodeRun`). This allows sub-millisecond query performance for the API and Web Console without locking the execution engine.

---

## 2. Dynamic Execution Engine

The core `DynamicExecutor` orchestrates tasks as a Directed Acyclic Graph (DAG).
- Uses `asyncio.gather()` to run independent nodes in parallel.
- Streams events sequentially or in real-time via `SSE (Server-Sent Events)`.
- Handles `Human-in-the-Loop (HITL)` workflows by checkpointing DAG state and awaiting user approval.

## 3. Two-Stage Guardrail Architecture

To securely handle untrusted multi-tenant inputs, Vortex implements a high-performance **Two-Stage Guardrail System**:
1. **Fast Regex Pre-filter (Stage 1):** Processes prompts in `< 0.05ms` using highly optimized heuristic pattern matching to block obvious jailbreaks, SQL injections, and system overrides.
2. **Semantic LLM Filter (Stage 2):** Routes complex, adversarial prompts to a dedicated `LLMPromptInjectionValidator`. By querying an LLM in a strict zero-shot classifier template, Vortex catches 90%+ of novel jailbreaks (such as DAN roleplay or instruction leakage) that bypass standard regex.

## 4. Evaluation Gates & Caching

Vortex ensures quality and performance through structured gates:

- **Built-in Deterministic Scorers**: Evaluates LLM outputs for Faithfulness, Toxicity, and PII leakage before returning results to the user.
- **Redis Semantic Caching**: Dual-tier caching bypasses LLM calls entirely for identical or semantically similar prompts.

---

## 5. Distributed Resilience (Worker & LeaseManager)

To ensure fault tolerance and prevent "lost wakeups" or duplicate executions, Vortex utilizes a distributed leasing architecture:

- **Redis TTL LeaseManager**: Before a worker can process a workflow task, it must acquire an atomic Lua-scripted TTL lock (`vortex:lease:{run_id}`) from Redis. This guarantees strictly exactly-once execution per node, even across a horizontally scaled cluster of hundreds of worker nodes.
- **Dead Letter Queue (DLQ)**: If a worker encounters an unrecoverable exception (e.g., OOM, network partition), the `WorkflowWorker` uses exponential backoff. If max retries are exceeded, the task is routed to the DLQ stream in Redis for manual review or automated recovery protocols.

---

## 3. DynamicGraphExecutor & State Transitions

The core execution engine is not a simple linear script; it is a durable state machine (`src/vortex/engine/executor.py`):

1. **Topological Sort**: Vortex validates the DAG via Kahn's algorithm to prevent cycles and determine parallel execution paths.
2. **State Transitions**: `PENDING` → `RUNNING` → `COMPLETED` / `FAILED` / `AWAITING_APPROVAL`.
3. **Yielding & Interrupts**: Workflows can `yield_task` mid-execution. This freezes the state and checkpoints it to PostgreSQL JSONB. The worker node is freed to process other tasks. When a callback or HITL (Human-in-the-Loop) approval resumes the workflow, the engine rehydrates the exact state and continues execution from the exact interrupted node.

---

## 4. Multi-Tenant Enterprise Security

Vortex is designed to serve as the backbone for multi-tenant SaaS applications:

- **Auth & RBAC**: The FastAPI gateway enforces API Key validation with Role-Based Access Control (Owner, Member, Viewer) at the edge.
- **Tenant Isolation**: Every database query implicitly scopes to the authenticated `tenant_id`.
- **Payload Encryption**: Sensitive workflow variables and outputs are encrypted at rest using AES-256-GCM. 
- **HKDF Key Derivation**: Tenant encryption keys are isolated using HMAC-based Extract-and-Expand Key Derivation Function (HKDF). A system master key derives unique cryptographic keys for each individual tenant, ensuring a breach of one tenant's data cannot compromise another.

---

## 5. Model Gateway & Provider Routing

Vortex sits between your application and the LLM providers to handle scale and safety:

- **Multi-Provider Fallover**: Seamlessly route traffic across OpenAI, Anthropic, Google Gemini, and local vLLM instances. If OpenAI throws a 529 (Overloaded), Vortex automatically fails over to Claude 3.5 without dropping the request.
- **Circuit Breakers**: Vortex tracks provider health and trips circuit breakers to prevent cascading timeouts.
- **Redis Semantic Caching**: Dual-tier caching bypasses LLM calls entirely for identical or semantically similar prompts.
- **Guardrails Engine**: Inline protection against prompt injection (DAN attacks) and PII leakage.
- **Evaluation Gates**: Built-in deterministic scorers to evaluate LLM outputs for Faithfulness and Toxicity before returning them to the user.
