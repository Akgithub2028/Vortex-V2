"""
Vortex Prometheus metrics definitions.

Defines all application-level metrics and exposes them via /metrics endpoint.
"""

from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram, Info

from vortex.config import get_settings
from vortex.observability.logger import get_logger

logger = get_logger(__name__)

# ─── Application Info ──────────────────────────────────────────────────────────

APP_INFO = Info("vortex", "Vortex AI Execution Engine metadata")

# ─── LLM Gateway Metrics ──────────────────────────────────────────────────────

LLM_REQUESTS_TOTAL = Counter(
    "vortex_llm_requests_total",
    "Total LLM API requests",
    ["provider", "model", "status"],  # status: success, error, timeout, rate_limited
)

LLM_LATENCY_SECONDS = Histogram(
    "vortex_llm_latency_seconds",
    "LLM API call latency in seconds",
    ["provider", "model"],
    buckets=(0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0),
)

LLM_TOKENS_TOTAL = Counter(
    "vortex_llm_tokens_total",
    "Total tokens consumed",
    ["provider", "model", "direction"],  # direction: input, output
)

LLM_COST_USD_TOTAL = Counter(
    "vortex_llm_cost_usd_total",
    "Total cost in USD",
    ["provider", "model"],
)

LLM_CACHE_HITS_TOTAL = Counter(
    "vortex_cache_hits_total",
    "Semantic and exact cache hits",
    ["cache_type"],  # exact, semantic
)

LLM_CACHE_MISSES_TOTAL = Counter(
    "vortex_cache_misses_total",
    "Cache misses",
    ["cache_type"],
)

# ─── Workflow Engine Metrics ───────────────────────────────────────────────────

WORKFLOW_RUNS_TOTAL = Counter(
    "vortex_workflow_runs_total",
    "Total workflow executions",
    ["status"],  # completed, failed, cancelled, timeout
)

WORKFLOW_DURATION_SECONDS = Histogram(
    "vortex_workflow_duration_seconds",
    "End-to-end workflow duration in seconds",
    buckets=(1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0, 600.0),
)

WORKFLOW_ACTIVE_RUNS = Gauge(
    "vortex_workflow_active_runs",
    "Currently executing workflows",
)

NODE_RUNS_TOTAL = Counter(
    "vortex_node_runs_total",
    "Total node executions",
    ["node_type", "status"],  # node_type: llm, tool, branch, parallel, eval, human
)

NODE_RETRIES_TOTAL = Counter(
    "vortex_node_retries_total",
    "Total node retry attempts",
    ["node_type"],
)

# ─── Guardrails Metrics ───────────────────────────────────────────────────────

GUARDRAIL_CHECKS_TOTAL = Counter(
    "vortex_guardrail_checks_total",
    "Total guardrail checks executed",
    ["guardrail_type", "result"],  # type: injection, pii, content_policy; result: pass, warn, block
)

# ─── Evaluation Metrics ───────────────────────────────────────────────────────

EVAL_SCORES = Histogram(
    "vortex_eval_scores",
    "Evaluation scores distribution",
    ["scorer_name"],
    buckets=(0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0),
)

EVAL_GATE_RESULTS_TOTAL = Counter(
    "vortex_eval_gate_results_total",
    "Evaluation gate pass/fail results",
    ["scorer_name", "result"],  # result: pass, retry, block
)

# ─── API Metrics ───────────────────────────────────────────────────────────────

API_REQUESTS_TOTAL = Counter(
    "vortex_api_requests_total",
    "Total API requests",
    ["method", "endpoint", "status_code"],
)

API_REQUEST_DURATION_SECONDS = Histogram(
    "vortex_api_request_duration_seconds",
    "API request duration in seconds",
    ["method", "endpoint"],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
)

# ─── DLQ Metrics ──────────────────────────────────────────────────────────────

DLQ_SIZE = Gauge(
    "vortex_dlq_size",
    "Number of items in the dead letter queue",
)

# ─── V2 Event Store & Engine Metrics ──────────────────────────────────────────

EVENT_STORE_EVENTS_TOTAL = Counter(
    "vortex_event_store_events_total",
    "Total workflow events appended to event store",
    ["event_type"],
)

EVENT_STORE_LAG_MS = Gauge(
    "vortex_event_store_projection_lag_ms",
    "Lag in milliseconds for event projection materialization",
)

LEASE_ACQUISITIONS_TOTAL = Counter(
    "vortex_lease_acquisitions_total",
    "Total distributed lease acquisition attempts",
    ["status"],  # acquired, rejected
)

KV_CACHE_AFFINITY_HITS_TOTAL = Counter(
    "vortex_kv_cache_affinity_hits_total",
    "Total KV-Cache prefix affinity routing hits",
)


def setup_metrics() -> None:
    """Initialize application-level metrics. Call once at startup."""
    settings = get_settings()

    APP_INFO.info(
        {
            "version": settings.service_version,
            "environment": settings.environment.value,
        }
    )

    logger.info("Prometheus metrics initialized")
