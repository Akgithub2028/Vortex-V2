"""
Vortex Platform Performance & Quality Benchmark Suite.

Measures:
1. Guardrail Prompt Injection Detection (subset of deepset/prompt-injections)
2. Evaluation Engine Faithfulness (subset of pminervini/HaluEval)
3. Execution Platform Overhead Latency
"""

import asyncio
import json
import time
from pathlib import Path

from vortex.guardrails.validators.llm_injection import LLMPromptInjectionValidator
from vortex.guardrails.validators.prompt_injection import PromptInjectionValidator


async def run_guardrails_benchmark() -> dict:
    dataset_path = Path(__file__).parent / "eval_datasets" / "injection_v1.jsonl"

    # Stage 1: Fast Regex Pre-filter
    regex_validator = PromptInjectionValidator()
    # Stage 2: Deep Semantic LLM Filter using Groq Llama 3.1
    llm_validator = LLMPromptInjectionValidator(provider_name="groq", model_name="llama-3.1-8b-instant")

    tp_regex = fp_regex = fn_regex = tn_regex = 0
    tp_llm = fp_llm = fn_llm = tn_llm = 0
    total = 0

    tasks = []
    expected_labels = []

    with open(dataset_path) as f:
        for line in f:
            item = json.loads(line)
            tasks.append(item["prompt"])
            expected_labels.append(item["is_injection"])

    total = len(tasks)

    # Process Regex Validator (Instant)
    for i, prompt_text in enumerate(tasks):
        expected = expected_labels[i]
        regex_res = await regex_validator.validate(prompt_text)
        regex_detected = not regex_res.passed
        if regex_detected and expected:
            tp_regex += 1
        elif regex_detected and not expected:
            fp_regex += 1
        elif not regex_detected and not expected:
            tn_regex += 1
        else:
            fn_regex += 1

    llm_tasks = tasks
    llm_expected = expected_labels
    total_llm = len(llm_tasks)

    batch_size = 50
    for i in range(0, total_llm, batch_size):
        batch_prompts = llm_tasks[i : i + batch_size]
        batch_expected = llm_expected[i : i + batch_size]

        # Concurrently evaluate the batch
        coros = [llm_validator.validate(p) for p in batch_prompts]
        results = await asyncio.gather(*coros, return_exceptions=True)

        for j, res in enumerate(results):
            expected = batch_expected[j]
            if isinstance(res, Exception):
                # Treat failure as safe (fail-open)
                llm_detected = False
            else:
                llm_detected = not res.passed

            if llm_detected and expected:
                tp_llm += 1
            elif llm_detected and not expected:
                fp_llm += 1
            elif not llm_detected and not expected:
                tn_llm += 1
            else:
                fn_llm += 1

    precision_regex = tp_regex / (tp_regex + fp_regex) if (tp_regex + fp_regex) > 0 else 1.0
    recall_regex = tp_regex / (tp_regex + fn_regex) if (tp_regex + fn_regex) > 0 else 1.0

    precision_llm = tp_llm / (tp_llm + fp_llm) if (tp_llm + fp_llm) > 0 else 1.0
    recall_llm = tp_llm / (tp_llm + fn_llm) if (tp_llm + fn_llm) > 0 else 1.0

    return {
        "benchmark": "prompt_injection_guardrail",
        "precision_regex": round(precision_regex, 4),
        "recall_regex": round(recall_regex, 4),
        "precision_llm": round(precision_llm, 4),
        "recall_llm": round(recall_llm, 4),
        "total": total,
    }


async def run_faithfulness_benchmark() -> dict:
    dataset_path = Path(__file__).parent / "eval_datasets" / "faithfulness_v1.jsonl"
    from vortex.eval.scorers.faithfulness import FaithfulnessScorer

    scorer = FaithfulnessScorer(provider_name="groq", model_name="llama-3.1-8b-instant")

    correct = 0
    total = 0

    tasks = []
    expected_labels = []

    with open(dataset_path) as f:
        for i, line in enumerate(f):
            if i >= 10000:
                break
            item = json.loads(line)
            tasks.append(item)
            expected_labels.append(item["is_faithful"])

    total = len(tasks)

    start = time.perf_counter()
    batch_size = 50
    for i in range(0, total, batch_size):
        batch_tasks = tasks[i : i + batch_size]
        batch_expected = expected_labels[i : i + batch_size]

        # Concurrently evaluate the batch
        coros = [scorer.score(output=t["claim"], reference_context=t["context"]) for t in batch_tasks]
        results = await asyncio.gather(*coros, return_exceptions=True)

        for j, res in enumerate(results):
            expected = batch_expected[j]
            if isinstance(res, Exception):
                pass
            else:
                if res.passed == expected:
                    correct += 1

        if (i + batch_size) % 500 == 0:
            pass

    duration_ms = ((time.perf_counter() - start) / total) * 1000.0 if total > 0 else 0.0

    return {
        "benchmark": "faithfulness_evaluation",
        "accuracy": round(correct / total, 4) if total > 0 else 1.0,
        "avg_latency_ms": round(duration_ms, 3),
        "total": total,
    }


async def run_latency_overhead_benchmark() -> dict:
    validator = PromptInjectionValidator()

    iterations = 100
    start = time.perf_counter()
    for _ in range(iterations):
        await validator.validate("Explain vector similarity search algorithm in PostgreSQL 16.")
    duration_ms = ((time.perf_counter() - start) / iterations) * 1000.0

    return {
        "benchmark": "platform_overhead_latency",
        "avg_latency_ms": round(duration_ms, 3),
        "target_ms": 50.0,
        "passed": duration_ms < 50.0,
    }


async def main():

    await run_guardrails_benchmark()

    await run_faithfulness_benchmark()

    await run_latency_overhead_benchmark()


if __name__ == "__main__":
    asyncio.run(main())
