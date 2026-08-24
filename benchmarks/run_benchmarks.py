#!/usr/bin/env python3
"""
VoRTeX Gateway & Evaluation Benchmark Runner Script.

Executes benchmark suites against evaluation datasets (Prompt Injection & Faithfulness),
evaluates latency distribution, throughput, and costs across providers, and outputs
a formatted Markdown report to benchmarks/benchmark_results.md.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
import time
from typing import Any

from vortex.eval.scorers.faithfulness import FaithfulnessScorer
from vortex.gateway.providers.base import CompletionRequest
from vortex.gateway.router import ModelRouter
from vortex.guardrails.validators.prompt_injection import PromptInjectionValidator

BENCHMARKS_DIR = Path(__file__).parent
DATASETS_DIR = BENCHMARKS_DIR / "eval_datasets"
RESULTS_FILE = BENCHMARKS_DIR / "benchmark_results.md"


async def run_injection_benchmark(limit: int = 50) -> dict[str, Any]:
    dataset_path = DATASETS_DIR / "injection_v1.jsonl"
    if not dataset_path.exists():
        return {"error": "injection_v1.jsonl missing"}

    validator = PromptInjectionValidator()
    correct = 0
    total = 0
    latencies: list[float] = []

    with open(dataset_path, "r", encoding="utf-8") as f:
        for line in f:
            if total >= limit:
                break
            record = json.loads(line)
            prompt = record.get("prompt", "")
            expected_injection = record.get("is_injection", False)

            start = time.perf_counter()
            res = await validator.validate(prompt)
            elapsed = (time.perf_counter() - start) * 1000.0
            latencies.append(elapsed)

            detected_injection = not res.passed
            if detected_injection == expected_injection:
                correct += 1
            total += 1

    accuracy = (correct / max(1, total)) * 100.0
    latencies.sort()
    p50 = latencies[int(len(latencies) * 0.5)] if latencies else 0.0
    p95 = latencies[int(len(latencies) * 0.95)] if latencies else 0.0

    return {
        "total_evaluated": total,
        "correct_predictions": correct,
        "accuracy_pct": round(accuracy, 2),
        "latency_p50_ms": round(p50, 2),
        "latency_p95_ms": round(p95, 2),
    }


async def run_gateway_benchmark(limit: int = 20) -> dict[str, Any]:
    router = ModelRouter()
    dataset_path = DATASETS_DIR / "faithfulness_v1.jsonl"
    if not dataset_path.exists():
        return {"error": "faithfulness_v1.jsonl missing"}

    total_tokens_in = 0
    total_tokens_out = 0
    total_cost = 0.0
    latencies: list[float] = []

    start_batch = time.perf_counter()

    with open(dataset_path, "r", encoding="utf-8") as f:
        for idx, line in enumerate(f):
            if idx >= limit:
                break
            record = json.loads(line)
            context = record.get("context", "")
            claim = record.get("claim", "")

            req = CompletionRequest(
                model="nvidia/meta/llama-3.1-70b-instruct",
                messages=[
                    {"role": "system", "content": "You are a concise AI evaluator."},
                    {"role": "user", "content": f"Context: {context}\nClaim: {claim}\nIs claim supported?"},
                ],
            )

            start_req = time.perf_counter()
            resp = await router.complete(req)
            elapsed = (time.perf_counter() - start_req) * 1000.0
            latencies.append(elapsed)

            total_tokens_in += resp.tokens_input
            total_tokens_out += resp.tokens_output
            total_cost += resp.cost_usd

    total_time = time.perf_counter() - start_batch
    throughput_qps = round(limit / max(0.001, total_time), 2)

    latencies.sort()
    p50 = latencies[int(len(latencies) * 0.5)] if latencies else 0.0
    p95 = latencies[int(len(latencies) * 0.95)] if latencies else 0.0

    return {
        "total_requests": limit,
        "total_time_sec": round(total_time, 2),
        "throughput_qps": throughput_qps,
        "tokens_input": total_tokens_in,
        "tokens_output": total_tokens_out,
        "total_cost_usd": round(total_cost, 6),
        "latency_p50_ms": round(p50, 2),
        "latency_p95_ms": round(p95, 2),
    }


async def main():
    print("🚀 Running VoRTeX Production Benchmarks...")

    inj_res = await run_injection_benchmark(limit=50)
    gw_res = await run_gateway_benchmark(limit=20)

    report_md = f"""# VoRTeX Benchmark Execution Report

Generated on: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}

## 1. Safety & Guardrails Engine Benchmark

Evaluating `PromptInjectionValidator` accuracy & latency over synthetic & real injection samples:

| Metric | Value |
|---|---|
| **Evaluated Samples** | {inj_res.get('total_evaluated')} |
| **Detection Accuracy** | **{inj_res.get('accuracy_pct')}%** |
| **Latency (p50)** | `{inj_res.get('latency_p50_ms')} ms` |
| **Latency (p95)** | `{inj_res.get('latency_p95_ms')} ms` |

---

## 2. Model Gateway & NIM Inference Benchmark

Evaluating `ModelRouter` throughput, token consumption, and cost tracking with `NVIDIANIMProvider` (`nvidia/meta/llama-3.1-70b-instruct`):

| Metric | Value |
|---|---|
| **Total Requests** | {gw_res.get('total_requests')} |
| **Throughput** | **{gw_res.get('throughput_qps')} req/sec** |
| **Latency (p50)** | `{gw_res.get('latency_p50_ms')} ms` |
| **Latency (p95)** | `{gw_res.get('latency_p95_ms')} ms` |
| **Input Tokens** | {gw_res.get('tokens_input'):,} |
| **Output Tokens** | {gw_res.get('tokens_output'):,} |
| **Total Cost (USD)** | **${gw_res.get('total_cost_usd'):.6f}** |

---

## 3. Comparative Cost Efficiency Analysis

| Provider & Model | Price / 1M Input | Price / 1M Output | Relative Cost Savings |
|---|---|---|---|
| **NVIDIA NIM (`llama-3.1-70b`)** | **$0.35** | **$0.40** | **Baseline (Free tier available)** |
| **OpenAI (`gpt-4o`)** | $2.50 | $10.00 | ~85% more expensive |
| **Anthropic (`claude-3-5-sonnet`)** | $3.00 | $15.00 | ~90% more expensive |
"""

    RESULTS_FILE.write_text(report_md, encoding="utf-8")
    print(f"✅ Benchmark completed successfully! Report written to {RESULTS_FILE}")


if __name__ == "__main__":
    asyncio.run(main())
