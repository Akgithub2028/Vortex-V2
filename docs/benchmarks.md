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

## 4. Running the Benchmark Suite

To execute the benchmark suite locally:

```bash
python3 benchmarks/run_benchmarks.py
```

Results will be dynamically saved to `benchmarks/benchmark_results.md`.
