# VoRTeX — Open-Source AI Workflow Execution Engine

[![CI Pipeline](https://img.shields.io/badge/CI%2FCD-Passing-10b981?style=for-the-badge&logo=githubactions)](https://github.com/Akgithub2028/vortex/actions)
[![Coverage](https://img.shields.io/badge/Coverage-90%25%2B-10b981?style=for-the-badge)](https://github.com/Akgithub2028/VoRTeX/blob/main/tests)
[![Python Version](https://img.shields.io/badge/Python-3.12%2B-3776ab?style=for-the-badge&logo=python)](https://github.com/Akgithub2028/VoRTeX/blob/main/pyproject.toml)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg?style=for-the-badge)](https://github.com/Akgithub2028/VoRTeX/blob/main/LICENSE)
[![Status](https://img.shields.io/badge/Status-Alpha%20%2F%20Portfolio%20Project-f59e0b?style=for-the-badge)](#roadmap)

> **Tech Stack**: FastAPI | PostgreSQL 16 | Redis 7 | React + Vite | OpenTelemetry

**Vortex** (`vortex-ai`) is a self-hostable execution engine for durable, multi-step LLM and agent workflows, built in Python 3.12 with FastAPI, PostgreSQL, Redis, and OpenTelemetry. It brings together the infrastructure patterns that power production-grade agent platforms — event-sourced durable orchestration, distributed crash-safe workers, a multi-provider LLM gateway, inline guardrails and evaluation gates, and full observability — in one coherent codebase instead of five separate tools stitched together.

**Why it's worth a look:**

- **You own the infrastructure.** Runs entirely on your own PostgreSQL + Redis stack — no external control plane, no third-party dependency to keep a workflow alive.
- **Workflows survive crashes.** Event-sourced state plus Redis TTL leases mean a worker restart or container crash never loses in-flight execution — a fresh worker just picks the lease back up.
- **No provider lock-in.** Route and fail over across OpenAI, Anthropic, Gemini, Groq, or local models without touching workflow code.
- **Safety is part of the graph, not an afterthought.** Prompt-injection defense, PII scrubbing, and quality-eval gates run as first-class nodes that can block a bad output before it ever returns.

---

## 🌟 Project Vision & Core Concepts

Vortex was built to get hands-on with the architecture patterns that make LLM workflows reliable at scale:

- **Fault-Tolerant Execution**: Event-sourced state (CQRS) plus Redis TTL leases mean a worker crash or container restart doesn't lose in-flight workflow state — a new worker picks the lease back up.
- **Access-Scoped Data Model**: Every API call is authenticated through hashed, per-key rate-limited API keys, with role-based access control (owner/member/viewer) enforced at the API layer.
- **Multi-Provider Model Gateway**: Route and fail over between OpenAI, Anthropic, Gemini, Groq, and local models without changing workflow code, with circuit breakers and dual-tier (exact + semantic) caching in front of every call.
- **Evaluation as a First-Class Citizen**: Faithfulness, relevance, and toxicity scorers run as graph nodes, not an afterthought — a workflow can gate on its own output quality before returning a result.

### 🎯 What This Project Demonstrates

Vortex is a demonstration of infrastructure engineering for LLM systems, most relevant if you're evaluating:

1. **Durable agent/workflow orchestration** — event sourcing, DAG execution, human-in-the-loop pauses, crash recovery.
2. **LLM gateway design** — provider abstraction, failover, circuit breaking, cost tracking, semantic caching.
3. **Inline safety and quality gates** — prompt-injection defense, PII scrubbing, and eval-gated outputs as part of the execution graph itself.

---

## 🏛️ System Architecture

```mermaid
flowchart TD
    %% Define styles
    classDef client fill:#2a2a2a,stroke:#666,stroke-width:2px,color:#fff
    classDef core fill:#1e40af,stroke:#60a5fa,stroke-width:2px,color:#fff
    classDef store fill:#065f46,stroke:#34d399,stroke-width:2px,color:#fff
    classDef worker fill:#9a3412,stroke:#fb923c,stroke-width:2px,color:#fff
    classDef llm fill:#4c1d95,stroke:#a78bfa,stroke-width:2px,color:#fff

    Client(["💻 SDK / REST / Web Console"]):::client

    subgraph "🌐 Control Plane"
        API["FastAPI Router Gateway"]:::core
        Auth["Auth & Access Middleware"]:::core
    end

    subgraph "⚙️ Orchestration & State"
        Engine["Dynamic DAG Executor"]:::core
        EventStore[("Append-Only EventStore")]:::store
        Projector["CQRS State Projector"]:::core
        ReadDB[("PostgreSQL Read Models")]:::store
    end

    subgraph "🛡️ Resilience Layer"
        Worker["Distributed Stream Worker"]:::worker
        Lease[("Redis TTL LeaseManager")]:::store
        DLQ[("Dead Letter Queue")]:::store
    end

    subgraph "🧠 Model Gateway & Safety"
        Gateway["Multi-Provider Router"]:::llm
        Guard["Guardrails & Evals"]:::llm
        Cache[("Redis Semantic Cache")]:::store
    end

    Providers(["☁️ OpenAI / Anthropic / Gemini / Groq / Local"]):::llm

    %% Connections
    Client --> API
    API --> Auth
    Auth --> Engine

    Engine --> EventStore
    EventStore --> Projector
    Projector --> ReadDB

    Engine <--> Worker
    Worker --> Lease
    Worker --> DLQ

    Engine --> Gateway
    Gateway --> Guard
    Gateway --> Cache
    Gateway --> Providers
```

---

## ✨ Platform Features

### ⚡ Event-Sourced CQRS Dynamic Engine

- **Append-Only Event Store**: Every workflow transition and node execution is logged as an immutable event, giving a full, replayable execution history — invaluable for debugging and for reconstructing exactly what a workflow did and why.
- **Read Projections**: A background `StateProjector` materializes the event log into indexed `WorkflowRun` / `NodeRun` PostgreSQL tables, so the API serves fast reads without ever querying the raw event stream directly.
- **Runtime Graph Expansion**: Supports dynamic task yielding (`yield_task`), sub-workflow spawning, and conditional branching, so graphs can grow and adapt mid-execution instead of being fixed at definition time.

### 🔒 Distributed Resilient Worker Nodes

- **Atomic Redis Leases**: Lua-scripted TTL locks (`LeaseManager`) prevent duplicate execution and enable seamless crash recovery — covered by a dedicated fault-injection test suite (`tests/simulation/test_fault_injection.py`) that simulates worker deaths mid-run.
- **Dead Letter Queue (DLQ)**: Exponential-backoff retries with DLQ fallback for unrecoverable node errors, so one bad node doesn't take down an entire workflow silently.

### 🎯 Model Gateway

- **KV-Cache Prefix Affinity**: A consistent-hashing router (`KVCacheAffinityRouter`) directs matching prompt prefixes to the same replica, taking advantage of warm KV caches for lower latency and cost.
- **Multi-Provider Failover**: Adapters for OpenAI, Anthropic, Google Gemini, Groq, and local endpoints, with automatic fallback when a provider degrades or errors out.
- **Circuit Breakers & Rate Limits**: Trip on repeated provider errors to stop cascading timeouts from taking down the whole gateway.
- **Dual-Tier Semantic Caching**: Exact hash match plus embedding-similarity caching via Redis/pgvector, cutting redundant model calls.

### 🛡️ Inline Guardrails & Evaluation Gates

- **Two-Stage Prompt Injection Defense**: A sub-millisecond regex pre-filter, backed by an LLM-based semantic classifier for prompts that pass the first stage — see measured precision/recall in the [benchmark table](#-measured-performance) below.
- **PII Detection & Scrubbing**: Detects and masks common personal identifiers before they reach an external model provider.
- **Quality Evaluation Gates**: Faithfulness, relevance, and toxicity scorers that can block a workflow from returning a low-quality generation.

### 🔐 Access Control & Workspace Isolation

- **Scoped API Keys**: Every request is authenticated through a hashed, per-key rate-limited API key.
- **Role-Based Access Control (RBAC)**: Owner / member / viewer roles enforced at the API layer.
- **Payload Encryption Envelope**: Workflow payloads can be wrapped in a per-key derived encryption envelope before being written to the event store, keeping sensitive data protected at rest.

### 🔭 OpenTelemetry Observability

- **Distributed Tracing**: OTLP spans across the full prompt-to-response lifecycle.
- **Prometheus Metrics**: A `/metrics` endpoint exposing latency, cost, and cache hit-rate.

---

## 📊 Measured Performance

Numbers below come straight from `benchmarks/run_benchmarks.py` and the CI-enforced test suite — every figure is reproducible from source, not a headline pulled out of thin air.

| Metric / Evaluator             | Measured Score                 | Benchmark Source / Methodology                                       | Environment                         |
| ------------------------------ | ------------------------------- | ---------------------------------------------------------------------- | -------------------------------------- |
| **Stage 1 Regex Pre-filter**   | 99.8% Precision / 74.5% Recall  | Heuristic regex on `deepset/prompt-injections` (5k samples)            | < 0.05 ms execution                    |
| **Stage 2 LLM Guardrail**      | 92.4% Precision / 91.8% Recall  | Semantic classifier via Groq `llama-3.1-8b-instant`, same 5k prompts   | Fail-open on provider error            |
| **LLM Faithfulness Agreement** | 91.5% Label Agreement           | Claim verification on `pminervini/HaluEval` vs. ground truth           | LLM-as-judge (Groq Llama 3.1)          |
| **Node Execution Overhead**    | 0.048 ms / node                 | Averaged over 10,000 execution-graph loops                             | Target: < 50 ms                        |
| **Test Suite**                 | 130 passed, 1 skipped\*         | `pytest`, run in CI on every push                                      | Python 3.12                            |
| **Code Coverage**              | ≥ 90% (CI-enforced gate)        | `pytest-cov`, line + branch                                            | Threshold fails the build below 90%    |

\* The one skip requires a live provider API key and simply doesn't run without one.

> **Reproduce it**: `PYTHONPATH=./src .venv/bin/python benchmarks/run_benchmarks.py` (guardrail/faithfulness benchmarks need a `GROQ_API_KEY`; the core test suite does not).
>
> Benchmarks are run against two public HuggingFace datasets (`deepset/prompt-injections`, `pminervini/HaluEval`) — a solid signal of real-world behavior, worth validating further against your own prompt distribution.

---

## 🚀 Quick Start

### 1. Installation

```bash
git clone https://github.com/Akgithub2028/vortex.git
cd vortex

# Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install Python package and development dependencies
pip install -e ".[dev]"
```

### 2. Launch Stack Services

```bash
# Start PostgreSQL & Redis infrastructure
docker compose -f docker/docker-compose.yml up -d

# Generate and run database migrations
alembic revision --autogenerate -m "initial"
alembic upgrade head

# Start Vortex API Gateway server
export PYTHONPATH=./src
uvicorn --factory src.vortex.api.main:create_app --port 8000
```

### 3. Build & Run a Workflow (Python SDK)

```python
import asyncio
from vortex.sdk import VortexClient, Workflow

async def main():
    # 1. Define fluent workflow DAG
    wf = Workflow(name="enterprise-summarizer")

    # 2. Add LLM node with guardrails and evaluation gates
    wf.add_llm_node("draft", prompt="Synthesize key metrics for topic: {topic}.", model="openai/gpt-4o")
    wf.add_eval_node("quality_gate", metric="faithfulness", threshold=0.8, dependencies=["draft"])

    # 3. Execute via async VortexClient
    client = VortexClient(base_url="http://localhost:8000", api_key="vtx_live_...")
    run = await client.run_workflow(wf, input={"topic": "High-Throughput AI Engines"})

    print(f"Run ID: {run.id} | Status: {run.status}")
    print(f"Tokens Used: {run.total_tokens} | Cost: ${run.total_cost_usd:.4f}")
    print("Output:", run.output)

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 💻 Web Console

`console/` is a React + Vite front-end that brings the engine to life visually: workflow runs, a worker/queue view, model gateway stats, and eval/guardrail logs. It's the intended dashboard experience for operating Vortex day-to-day, currently running on representative sample data while it's wired up to the live API.

```bash
cd console
npm install
npm run dev
```

---

## 📚 Documentation & Resources

- ⚡ [Quickstart Guide](https://github.com/Akgithub2028/VoRTeX/blob/main/docs/quickstart.md)
- 🏛️ [Architecture Deep-Dive](https://github.com/Akgithub2028/VoRTeX/blob/main/docs/architecture.md)
- 🔌 [API Reference](https://github.com/Akgithub2028/VoRTeX/blob/main/docs/api-reference.md)
- 🐍 [Python SDK Guide](https://github.com/Akgithub2028/VoRTeX/blob/main/docs/sdk-guide.md)
- 🚀 [Self-Hosted Deployment Guide](https://github.com/Akgithub2028/VoRTeX/blob/main/docs/deployment.md)
- 🤝 [Contributing Guidelines](https://github.com/Akgithub2028/VoRTeX/blob/main/CONTRIBUTING.md)

---

## 🗺️ Roadmap

Vortex is under active development. Current focus areas:

- `[x]` Multi-Provider Gateway & Fallbacks
- `[x]` LLM Guardrails & Semantic Evals (Faithfulness/Toxicity)
- `[x]` CQRS EventStore Execution Engine
- `[ ]` Upgrade payload encryption to AES-GCM via the `cryptography` library
- `[ ]` Wire the web console to live API data
- `[ ]` Kubernetes Helm charts for production deployment
- `[ ]` Advanced Prompt Registry & A/B Testing

---

## 📜 License

Licensed under the [Apache 2.0 License](https://github.com/Akgithub2028/VoRTeX/blob/main/LICENSE).
