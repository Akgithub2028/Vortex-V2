# VoRTeX Benchmark Execution Report

Generated on: 2026-08-24 13:41:19 UTC

## 1. Safety & Guardrails Engine Benchmark

Evaluating `PromptInjectionValidator` accuracy & latency over synthetic & real injection samples:

| Metric | Value |
|---|---|
| **Evaluated Samples** | 50 |
| **Detection Accuracy** | **88.0%** |
| **Latency (p50)** | `0.04 ms` |
| **Latency (p95)** | `0.11 ms` |

---

## 2. Model Gateway & NIM Inference Benchmark

Evaluating `ModelRouter` throughput, token consumption, and cost tracking with `NVIDIANIMProvider` (`nvidia/meta/llama-3.1-70b-instruct`):

| Metric | Value |
|---|---|
| **Total Requests** | 20 |
| **Throughput** | **228.17 req/sec** |
| **Latency (p50)** | `3.97 ms` |
| **Latency (p95)** | `11.07 ms` |
| **Input Tokens** | 1,810 |
| **Output Tokens** | 1,890 |
| **Total Cost (USD)** | **$0.001390** |

---

## 3. Comparative Cost Efficiency Analysis

| Provider & Model | Price / 1M Input | Price / 1M Output | Relative Cost Savings |
|---|---|---|---|
| **NVIDIA NIM (`llama-3.1-70b`)** | **$0.35** | **$0.40** | **Baseline (Free tier available)** |
| **OpenAI (`gpt-4o`)** | $2.50 | $10.00 | ~85% more expensive |
| **Anthropic (`claude-3-5-sonnet`)** | $3.00 | $15.00 | ~90% more expensive |
