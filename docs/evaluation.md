# VoRTeX Evaluation Framework & Quality Gating

VoRTeX treats **evaluation as a first-class execution primitive** rather than an off-line, after-the-fact analysis step. Evaluation scorers run directly inside workflow execution graphs (`EvalNode`), gating whether LLM outputs meet defined quality, faithfulness, and safety thresholds before results are returned to downstream consumers or persisted to database read models.

---

## 1. Core Scorer Suite

VoRTeX includes a modular, extensible scoring engine located in `src/vortex/eval/scorers/`:

| Scorer | Class Name | Purpose | Output Range |
|---|---|---|---|
| **Faithfulness** | `FaithfulnessScorer` | Measures whether generated text statements are fully supported by reference context (hallucination detection). | `0.0` to `1.0` |
| **Relevance** | `RelevanceScorer` | Measures prompt adherence and alignment between output response and input prompt. | `0.0` to `1.0` |
| **Toxicity** | `ToxicityScorer` | Evaluates output safety, hostility, and policy compliance. | `0.0` to `1.0` |

---

## 2. Architecture & Execution Modes

```text
               ┌───────────────────────────┐
               │    LLM Generation Output  │
               └─────────────┬─────────────┘
                             │
                             ▼
               ┌───────────────────────────┐
               │  EvalNode / Scorer Gate   │
               └─────────────┬─────────────┘
                             │
               ┌─────────────┴─────────────┐
               ▼                           ▼
      [Pass: Score >= Threshold]  [Fail: Score < Threshold]
               │                           │
               ▼                           ▼
      Continue Workflow           Trigger Gate Action
                                  (Warn / Retry / Block)
```

### 2.1 Graph Node Gating (`EvalNode`)

An `EvalNode` can be placed anywhere in a workflow DAG. It receives state variables (e.g. `output` from a prior `LLMNode` and `context` from a retrieval step) and evaluates them against configured quality thresholds.

- **Threshold:** Configurable float (default `0.7`).
- **Gate Actions:**
  - `warn`: Logs evaluation warnings and records metrics, allowing execution to proceed.
  - `block`: Fails node execution with `EvalGateError`, terminating or rerouting the workflow.
  - `retry`: Re-executes the upstream generation node with adjusted sampling parameters.

### 2.2 Batch Evaluation Runner (`EvaluationRunner`)

For benchmark regression testing, `EvaluationRunner` processes JSONL evaluation datasets (`benchmarks/eval_datasets/`):

```python
from vortex.eval.runner import EvaluationRunner, DatasetItem

runner = EvaluationRunner(scorer_name="faithfulness", threshold=0.7)
summary = await runner.run_batch(
    dataset_name="faithfulness_v1",
    items=dataset_items,
    tenant_id=tenant_uuid,
)

print(f"Pass Rate: {summary.pass_rate * 100:.1f}%")
print(f"Mean Score: {summary.mean_score:.3f}")
```

Summaries and per-item scores are automatically materialized to the PostgreSQL `eval_results` table for auditability and quality tracking over time.

---

## 3. Observability & Metrics

Every evaluation execution automatically records telemetry:

- **Prometheus Metrics:**
  - `vortex_eval_scores_total{scorer_name="..."}`: Histogram of score distributions.
  - `vortex_eval_gate_results_total{scorer_name="...", result="pass|block"}`: Pass/fail outcome counter.
- **Structured Logging:**
  - Includes `eval_id`, `dataset`, `scorer`, `mean_score`, and `pass_rate` in structlog events.

---

## 4. Running Evaluation Tests

To execute evaluation suite unit and benchmark tests:

```bash
# Run unit & evaluation test suite
python3 -m pytest tests/eval/ -v

# Run full benchmark suite against HuggingFace datasets
python3 benchmarks/run_benchmarks.py
```
