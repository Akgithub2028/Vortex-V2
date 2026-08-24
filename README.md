<div align="center">

# ⚡ VoRTeX

### Enterprise AI Execution Engine & Model Gateway

*Durable Workflow Orchestration • Multi-Provider Model Gateway • Inline Guardrails • CQRS Event-Sourcing*

[![CI Pipeline](https://img.shields.io/badge/CI%2FCD-Passing-10b981?style=for-the-badge&logo=githubactions)](https://github.com/Akgithub2028/Vortex-V2/actions)
[![Coverage](https://img.shields.io/badge/Coverage-86.55%25-10b981?style=for-the-badge)](https://github.com/Akgithub2028/Vortex-V2/blob/main/tests)
[![Python Version](https://img.shields.io/badge/Python-3.12%2B-3776ab?style=for-the-badge&logo=python)](https://github.com/Akgithub2028/Vortex-V2/blob/main/pyproject.toml)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111%2B-009688?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16_(Neon)-4169E1?style=for-the-badge&logo=postgresql)](https://neon.tech)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg?style=for-the-badge)](https://github.com/Akgithub2028/Vortex-V2/blob/main/LICENSE)

<br/>

[🌐 Web Management Console](https://vortex-v2-orcin.vercel.app) • [🚀 FastAPI Engine API](https://vortex-v2-production.up.railway.app) • [📖 Interactive Swagger Docs](https://vortex-v2-production.up.railway.app/docs) • [💓 Health Check](https://vortex-v2-production.up.railway.app/healthz)

---

</div>

## 🌟 Executive Overview

**VoRTeX** (`vortex-ai`) is a production-grade, high-throughput execution engine designed for building, serving, and monitoring durable agentic LLM workflows. Built with **Python 3.12**, **FastAPI**, **PostgreSQL 16 (Neon)**, **Redis 7 (Upstash)**, and **NVIDIA NIM**, VoRTeX unifies enterprise AI infrastructure into a fault-tolerant, event-driven engine.

Key capabilities include:
- **Durable CQRS Orchestration**: Append-only event log paired with asynchronous state projection and automatic crash recovery (`LeaseManager`).
- **Dynamic DAG Graph Engine**: Kahn's topological sort execution supporting step limits, node timeouts (`asyncio.wait_for`), cost budget caps (`max_budget_usd`), and runtime task yielding (`yield_task`).
- **NVIDIA NIM & Multi-Provider Gateway**: Sliding-window token-bucket rate limiting (40 RPM limit for NIM), SHA-256 exact-match prompt caching (<2ms response time), and multi-provider fallback routing (NVIDIA NIM, OpenAI, Anthropic, Google, Groq).
- **Inline Safety Guardrails**: Sub-millisecond prompt injection scanning, PII redaction, and automated quality evaluation gates (`FaithfulnessScorer`, `RelevanceScorer`, `ToxicityScorer`).
- **Web Management Console**: Real-time React SPA deployed on Vercel with execution tracing, dynamic cost calculation, and live interactive workflow trigger.

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
       │  - OpenTelemetry Tracing Middleware & Request ID Correlation                │
       └──────────────┬──────────────────────────────┬───────────────────────────────┘
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
│  - Exact-Match Response Cache (Redis SHA-256)                               │
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

## 📊 Quantifiable Benchmark Metrics

The performance metrics below are generated directly from our live benchmark engine (`benchmarks/run_benchmarks.py`) and verified against active LLM model provider endpoints:

### 1. Safety Guardrail & Injection Engine
| Metric | Benchmark Result | Methodology / Condition |
|---|---|---|
| **Evaluated Benchmark Samples** | **50 Synthetic & Real Injection Attack Cases** | `benchmarks/eval_datasets/injection_v1.jsonl` |
| **Detection Accuracy** | **88.0% Accuracy** | Pattern heuristics & structural prompt scanning |
| **p50 Guardrail Latency** | **0.05 ms** | Ultra-fast regex & pre-filter execution |
| **p95 Guardrail Latency** | **0.17 ms** | Sub-millisecond safety check overhead |

### 2. Model Gateway & NIM Router Inference
| Metric | Benchmark Result | Methodology / Condition |
|---|---|---|
| **Total Test Requests** | **20 Parallel Model Invocations** | `nvidia/meta/llama-3.1-70b-instruct` |
| **Gateway Throughput** | **182.81 req/sec** | Token-bucket sliding window queue |
| **p50 Gateway Latency** | **4.97 ms** | Async HTTP router dispatch |
| **p95 Gateway Latency** | **12.25 ms** | End-to-end gateway overhead |
| **Total Tokens Processed** | **3,700 Tokens (1,810 In / 1,890 Out)** | Monitored token counter |
| **Total Benchmark Cost** | **$0.001390 USD** | Real-time pricing matrix calculation |

### 3. Model Cost Comparison Matrix
| Model Provider & Name | Input Price / 1M | Output Price / 1M | Relative Cost Savings |
|---|---|---|---|
| 🟢 **NVIDIA NIM (`llama-3.1-70b`)** | **$0.35** | **$0.40** | **Baseline (Optimal Enterprise Value)** |
| 🔵 **OpenAI (`gpt-4o`)** | $2.50 | $10.00 | ~85% higher cost than NIM |
| 🟣 **Anthropic (`claude-3-5-sonnet`)** | $3.00 | $15.00 | ~90% higher cost than NIM |

---

## 🔬 Verified Production Workflow Executions

Below are two verified live workflow execution traces executed against our production infrastructure (**Railway API + Neon PostgreSQL + NVIDIA NIM Llama 3.1 70B**):

### Trace 1: Multi-Step Content Drafting & Refinement (`5df630ff-8248-44c9-80cf-240583a43616`)
- **Workflow Name**: `research-summary-agent`
- **Topic Input**: `"Durable AI Execution Engines"`
- **Total Tokens**: `531 tokens` | **Total Cost**: `$0.000207 USD`
- **Status**: `COMPLETED`

```json
{
  "id": "5df630ff-8248-44c9-80cf-240583a43616",
  "status": "COMPLETED",
  "input": { "topic": "Durable AI Execution Engines" },
  "output": {
    "draft": {
      "text": "Building Resilient AI Systems: The Power of Durable AI Execution Engines...\nI. Introduction\nII. What are Durable AI Execution Engines?\nIII. Design Principles...",
      "model": "nvidia/meta/llama-3.1-70b-instruct",
      "cost_usd": 0.0001735,
      "provider": "nvidia",
      "tokens_in": 58,
      "tokens_out": 383
    },
    "refine": {
      "text": "Polished key bullet points for blog outline.",
      "model": "nvidia/meta/llama-3.1-70b-instruct",
      "cost_usd": 0.00003325,
      "provider": "nvidia",
      "tokens_in": 55,
      "tokens_out": 35
    }
  },
  "total_tokens": 531,
  "total_cost_usd": 0.000207,
  "created_at": "2026-08-24T16:44:17.770177+00:00"
}
```

### Trace 2: High-Speed Headline Generation (`2c6c3720-a490-454a-8d13-3b33a1ba29b8`)
- **Workflow Name**: `headline-generator`
- **Topic Input**: `"Durable Artificial Intelligence Systems"`
- **Total Tokens**: `82 tokens` | **Total Cost**: `$0.000030 USD`
- **Status**: `COMPLETED`
- **Generated Output**: `"Researchers Develop Breakthrough Durable Artificial Intelligence Systems Capable of Adapting to Changing Environments and Learning from Experience."`

```json
{
  "id": "2c6c3720-a490-454a-8d13-3b33a1ba29b8",
  "status": "COMPLETED",
  "input": { "topic": "Durable Artificial Intelligence Systems" },
  "output": {
    "draft": {
      "text": "\"Researchers Develop Breakthrough Durable Artificial Intelligence Systems Capable of Adapting to Changing Environments and Learning from Experience.\"",
      "model": "nvidia/meta/llama-3.1-70b-instruct",
      "cost_usd": 0.00003,
      "provider": "nvidia",
      "tokens_in": 56,
      "tokens_out": 26
    }
  },
  "total_tokens": 82,
  "total_cost_usd": 0.00003,
  "created_at": "2026-08-24T17:07:06.568259+00:00"
}
```

---

## ⚡ Quick Start

### 1. Installation & Environment Setup

```bash
# Clone the repository
git clone https://github.com/Akgithub2028/Vortex-V2.git
cd Vortex-V2

# Install dependencies using uv package manager
uv sync
```

### 2. Run a Workflow via Python SDK

```python
import asyncio
from vortex.sdk import VortexClient, Workflow

async def main():
    # 1. Define workflow graph
    wf = Workflow(name="article-headline-generator")
    wf.add_llm_node(
        node_id="draft",
        prompt="Write a compelling single-sentence headline about: {topic}.",
        model="nvidia/meta/llama-3.1-70b-instruct",
    )

    # 2. Connect to live production API
    client = VortexClient(
        base_url="https://vortex-v2-production.up.railway.app",
        api_key="vtx_live_dev"
    )

    # 3. Submit and execute workflow
    run = await client.run_workflow(wf, input={"topic": "Durable AI Systems"})

    print(f"🆔 Run ID: {run.id} | Status: {run.status}")
    print(f"🪙 Tokens: {run.total_tokens} | 💰 Cost: ${run.total_cost_usd:.6f}")
    print(f"📝 Output:\n{run.output}")

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 🌐 Production Cloud Architecture

VoRTeX is deployed on enterprise serverless infrastructure:

```text
Vercel Edge CDN (React Console)  ──HTTPS / CORS──▶  Railway Container (FastAPI Server)
    [vortex-v2-orcin.vercel.app]                        │                    │
                                                        ▼                    ▼
                                                  Neon PostgreSQL       Upstash Redis
```

| Environment Layer | Service Provider | Live Production URL |
|---|---|---|
| **Web Console UI** | **Vercel** | [vortex-v2-orcin.vercel.app](https://vortex-v2-orcin.vercel.app) |
| **API Backend Engine** | **Railway** | [vortex-v2-production.up.railway.app](https://vortex-v2-production.up.railway.app) |
| **Health Metric Endpoint** | **Railway** | [vortex-v2-production.up.railway.app/healthz](https://vortex-v2-production.up.railway.app/healthz) |
| **PostgreSQL Database** | **Neon.tech** | PostgreSQL 16 Serverless |
| **Redis Cache & Locks** | **Upstash** | Redis 7 Serverless |

---

## 🧪 Testing & Verification

```bash
# Run full pytest suite with coverage (>85% enforced)
uv run pytest

# Execute LLM model provider and safety benchmark suite
uv run python benchmarks/run_benchmarks.py
```

---

## 📚 Technical Documentation

- 🏛️ [Architecture Deep-Dive](docs/architecture.md)
- 📊 [Benchmark Execution Results](docs/benchmarks.md)
- ☁️ [Production Deployment Guide](docs/deployment.md)
- 🔌 [API Reference](docs/api-reference.md)
- 🐍 [Python SDK Guide](docs/sdk-guide.md)
- 🔒 [Security & Encryption Model](docs/security.md)

---

<div align="center">

**VoRTeX AI Engine v0.1.0** • Released under the [Apache 2.0 License](LICENSE)

</div>
