# VoRTeX — Enterprise AI Execution Engine & Model Gateway

[![CI Pipeline](https://img.shields.io/badge/CI%2FCD-Passing-10b981?style=for-the-badge&logo=githubactions)](https://github.com/Akgithub2028/vortex/actions)
[![Coverage](https://img.shields.io/badge/Coverage-90.35%25-10b981?style=for-the-badge)](https://github.com/Akgithub2028/VoRTeX/blob/main/tests)
[![Python Version](https://img.shields.io/badge/Python-3.12%2B-3776ab?style=for-the-badge&logo=python)](https://github.com/Akgithub2028/VoRTeX/blob/main/pyproject.toml)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg?style=for-the-badge)](https://github.com/Akgithub2028/VoRTeX/blob/main/LICENSE)

> **Tech Stack**: FastAPI | PostgreSQL 16 | Redis 7 | React + Vite | OpenTelemetry | NVIDIA NIM

**VoRTeX** (`vortex-ai`) is a high-performance execution engine for durable agentic LLM workflows, built in Python 3.12. It unifies production-grade AI infrastructure into one coherent platform: CQRS event-sourced orchestration, dynamic DAG graph execution with runtime task yielding, multi-provider LLM gateway routing (NVIDIA NIM, OpenAI, Anthropic, Gemini, Groq), token-bucket rate limiting, exact-match prompt caching, inline safety guardrails, type-safe tool execution, and automated evaluation gating.

---

## 🌟 Architectural Highlights

- **NVIDIA NIM & Multi-Provider LLM Gateway:** Native `httpx` integration with NVIDIA NIM (`nvidia/meta/llama-3.1-70b-instruct`) supporting sliding-window token bucket rate limiting (40 RPM limit), exponential backoff retries, and multi-provider failover chains.
- **Durable Event-Sourced Orchestration (CQRS):** Append-only PostgreSQL event log paired with background state projections. Workflows survive worker crashes with atomic Redis TTL locks (`LeaseManager`).
- **Dynamic Graph Execution & Reliability Controls:** Kahn's topological sort DAG engine supporting runtime task yielding (`yield_task`), step limit execution guards (max 50 steps), node execution timeouts (`asyncio.wait_for`), and cost budget caps (`max_budget_usd`).
- **Type-Safe Tool Registry:** Central registry (`ToolRegistry`) with parameter schema validation for custom and built-in tools (`text_processor`, `json_extractor`, `web_search_stub`).
- **Inline Guardrails & Quality Evaluation:** Two-stage prompt injection defense, PII redaction, and inline evaluation gates (`FaithfulnessScorer`, `RelevanceScorer`, `ToxicityScorer`).
- **Enterprise Security & Observability:** Tenant isolation, HKDF payload envelope encryption, OpenTelemetry tracing, and Prometheus metrics (`LLM_REQUESTS`, `LLM_LATENCY`, `LLM_TOKENS`, `LLM_COST_USD`).

---

## 🏛️ System Architecture

```text
                        ┌──────────────────────────────┐
                        │    SDK / REST Client / CLI   │
                        └──────────────┬───────────────┘
                                       │ (FastAPI REST / SSE)
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           VoRTeX REST API Gateway                           │
│  - API Key & RBAC Authentication (Owner / Admin / Member / Viewer)           │
│  - Tracing Middleware & Request ID Correlation                              │
└──────────────────────────────┬──────────────────────────────┬───────────────┘
                               │                              │
                               ▼                              ▼
┌──────────────────────────────────────────┐     ┌────────────────────────────┐
│      Dynamic Graph Execution Engine      │     │    CQRS Event Projector    │
│  - Topological Sort (Kahn's Algorithm)   │     │  - Append-Only Event Store │
│  - Runtime Yielding & Step Limits        │     │  - Read Model Materializer │
│  - Node Timeouts & Cost Budget Caps      │     │  - HKDF Envelope Encrypt.  │
└──────────────────────┬───────────────────┘     └────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Model Gateway Router                              │
│  - Provider Token-Bucket Rate Limiter (40 RPM NIM Limit)                     │
│  - Inline Guardrails Engine (Prompt Injection & PII Redaction)              │
│  - Exact-Match Response Cache (Redis SHA-256)                         │
│  - Provider Adapters: NVIDIA NIM, OpenAI, Anthropic, Google, Groq           │
│  - Structured Output Enforcement (JSON Schema)                              │
└──────────────────────┬──────────────────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                       Evaluation & Telemetry Suite                          │
│  - Faithfulness / Relevance / Toxicity Scorers (`EvalNode`)                 │
│  - Prometheus Metrics (`LLM_REQUESTS`, `LLM_TOKENS`, `LLM_COST_USD`)        │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 📊 Benchmark & Quality Metrics

All numbers below are generated from `benchmarks/run_benchmarks.py` and verified by the automated CI test suite:

| Metric / Component | Measured Score / Result | Methodology / Environment |
|---|---|---|
| **Prompt Injection Defense** | **100.0% Detection Accuracy** | Evaluated on 50 synthetic & real injection benchmarks (`injection_v1.jsonl`) |
| **Guardrail Latency (p50)** | **< 1.0 ms** | Fast regex & heuristic pattern scanning |
| **Guardrail Latency (p95)** | **< 2.5 ms** | Sub-millisecond pre-filter overhead |
| **NIM Router Throughput** | **40 RPM (Rate Limited)** | Token-bucket sliding window rate limiter |
| **Response Cache Hit** | **< 2.0 ms** | Redis GET + SHA-256 exact prompt key match |
| **Full Unit & Eval Test Suite** | **145 Passed, 1 Skipped** | Executed via `pytest` (1 skipped requires live key) |
| **Code Coverage** | **90.35% (CI-Enforced Gate)** | Line + Branch coverage (`pytest-cov`) |

> **Reproduce Benchmarks:** Run `.venv/bin/python benchmarks/run_benchmarks.py` locally to re-generate `benchmarks/benchmark_results.md`.

---

## 🚀 Quick Start

### 1. Installation

```bash
git clone https://github.com/Akgithub2028/vortex.git
cd vortex

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install package dependencies
pip install -e ".[dev]"
```

### 2. Environment Configuration

Copy the sample environment file and set your API keys:

```bash
cp .env.example .env
```

Configure your key in `.env`:
```ini
VORTEX_NVIDIA_API_KEY=nvapi-...
VORTEX_NVIDIA_BASE_URL=https://integrate.api.nvidia.com/v1
```

### 3. Build & Run a Workflow (Python SDK)

```python
import asyncio
from vortex.sdk import VortexClient, Workflow

async def main():
    # 1. Define fluent workflow DAG
    wf = Workflow(name="ai-research-pipeline")

    # 2. Add LLM node using NVIDIA NIM
    wf.add_llm_node(
        "research",
        prompt="Analyze vector indexing techniques for: {topic}.",
        model="nvidia/meta/llama-3.1-70b-instruct",
    )
    
    # 3. Add inline Faithfulness Evaluation Gate
    wf.add_eval_node(
        "quality_gate",
        metric="faithfulness",
        threshold=0.8,
        dependencies=["research"],
    )

    # 4. Execute via async VortexClient
    client = VortexClient(base_url="http://localhost:8000", api_key="vtx_live_dev")
    run = await client.run_workflow(wf, input={"topic": "HNSW Vector Graphs"})

    print(f"Run ID: {run.id} | Status: {run.status}")
    print(f"Tokens Used: {run.total_tokens} | Cost: ${run.total_cost_usd:.6f}")
    print("Output:", run.output)

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 🧪 Running the Test Suite

```bash
# Run unit tests and evaluation suite with coverage report
.venv/bin/python -m pytest tests/unit tests/eval -v --tb=short

# Run benchmark suite
.venv/bin/python benchmarks/run_benchmarks.py
```

---

## ☁️ Production Deployment

VoRTeX deploys as a **Vercel + Railway hybrid** — frontend on Vercel's global edge CDN, backend on Railway's persistent Docker containers, with Neon.tech PostgreSQL and Upstash Redis.

```text
Vercel (Console SPA)  ──HTTPS──▶  Railway (FastAPI API + Worker)
                                      │              │
                                      ▼              ▼
                                Neon PostgreSQL   Upstash Redis
```

| Component | Service | Tier |
|---|---|---|
| **Frontend Console** | Vercel | Free |
| **Backend API** | Railway | Hobby ($5/mo) |
| **PostgreSQL 16** | Neon.tech | Free (0.5 GB) |
| **Redis 7** | Upstash | Free (10K cmd/day) |

**Total monthly cost: $0–$5**

See the full [Deployment Guide →](docs/deployment.md)

---

## 📚 Documentation & Deep-Dives

- 🏛️ [Architecture Deep-Dive](docs/architecture.md)
- 📊 [Evaluation Framework & Quality Gating](docs/evaluation.md)
- 📈 [Benchmark Metrics & Results](docs/benchmarks.md)
- 🔌 [API Reference](docs/api-reference.md)
- 🐍 [Python SDK Guide](docs/sdk-guide.md)
- ☁️ [Production Deployment Guide](docs/deployment.md)
- 🔒 [Security Model](docs/security.md)
- 📝 [Architecture Decision Records](docs/adr/)

---

## 📜 License

Licensed under the [Apache 2.0 License](LICENSE).
