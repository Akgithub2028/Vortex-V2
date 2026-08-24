# VoRTeX Benchmarks & Performance Metrics

This document outlines the benchmarking methodology, safety accuracy performance, latency distributions, and cost efficiency metrics across supported model providers (NVIDIA NIM, OpenAI, Anthropic).

---

## 1. Safety Guardrails & Injection Benchmark

Evaluated using `PromptInjectionValidator` across 50 benchmark cases from `benchmarks/eval_datasets/injection_v1.jsonl`:

- **Detection Accuracy:** `100.0%`
- **p50 Latency:** `< 1.0 ms`
- **p95 Latency:** `< 2.5 ms`

The regex & pattern matching heuristic validator operates inline before model provider dispatch, incurring negligible latency overhead (< 1ms).

---

## 2. Model Gateway Throughput & Latency

Evaluated using `ModelRouter` with `NVIDIANIMProvider` (`nvidia/meta/llama-3.1-70b-instruct`):

| Metric | Target / Measured Value |
|---|---|
| **Max Provider RPM (Rate Limit)** | `40 RPM` (Configurable via `VORTEX_NVIDIA_RATE_LIMIT_RPM`) |
| **Response Cache Match** | Exact SHA-256 Prompt Key Hash |
| **Cache Hit Latency** | `< 2 ms` (Redis GET + JSON deserialization) |
| **Circuit Breaker Threshold** | 5 consecutive failures -> 30s OPEN recovery window |

---

## 3. Cost Efficiency Comparison

VoRTeX tracks token usage and calculates USD cost per request dynamically based on model pricing matrices:

| Model Provider | Model Name | Input Price / 1M | Output Price / 1M | Cost Savings vs GPT-4o |
|---|---|---|---|---|
| **NVIDIA NIM** | `nvidia/meta/llama-3.1-70b-instruct` | **$0.35** | **$0.40** | **~85% Savings** |
| **NVIDIA NIM** | `nvidia/meta/llama-3.1-8b-instruct` | **$0.06** | **$0.06** | **~97% Savings** |
| **OpenAI** | `openai/gpt-4o-mini` | $0.15 | $0.60 | ~75% Savings |
| **OpenAI** | `openai/gpt-4o` | $2.50 | $10.00 | Baseline (1.0x) |
| **Anthropic** | `anthropic/claude-3-5-sonnet` | $3.00 | $15.00 | +50% vs GPT-4o |

---

---

## 5. Verified Live Production Execution Traces

Below are two complete real-time workflow traces executed against the production deployment (**Railway API + Neon PostgreSQL + NVIDIA NIM Llama 3.1 70B**):

### Trace 1: Multi-Step Chain (`5df630ff-8248-44c9-80cf-240583a43616`)
- **Workflow Name:** `research-summary-agent`
- **Topic:** `"Durable AI Execution Engines"`
- **Total Tokens:** `531`
- **Total Cost:** `$0.000207`
- **Nodes Executed:** `draft` (Outline generation), `refine` (Post-processing)
- **Status:** `COMPLETED`

```json
{
  "id": "5df630ff-8248-44c9-80cf-240583a43616",
  "status": "COMPLETED",
  "input": { "topic": "Durable AI Execution Engines" },
  "output": {
    "draft": {
      "text": "Building Resilient AI Systems: The Power of Durable AI Execution Engines...",
      "model": "nvidia/meta/llama-3.1-70b-instruct",
      "cost_usd": 0.0001735,
      "provider": "nvidia",
      "tokens_in": 58,
      "tokens_out": 383
    },
    "refine": {
      "text": "Polished key bullet points...",
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

### Trace 2: Fast Headline Generation (`2c6c3720-a490-454a-8d13-3b33a1ba29b8`)
- **Workflow Name:** `headline-generator`
- **Topic:** `"Durable Artificial Intelligence Systems"`
- **Total Tokens:** `82`
- **Total Cost:** `$0.000030`
- **Output:** `"Researchers Develop Breakthrough Durable Artificial Intelligence Systems Capable of Adapting to Changing Environments and Learning from Experience."`
- **Status:** `COMPLETED`

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
