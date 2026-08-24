# ADR 003: Bounded DAG Workflows vs. Autonomous Agent Loops

- **Status:** Accepted
- **Date:** 2026-08-24
- **Context:** Autonomous, unbounded agent loops often suffer from non-deterministic execution paths, infinite loops, runaway API costs, and low reliability in enterprise production environments.

## Decision
We enforce **Bounded Directed Acyclic Graph (DAG) Execution** via `DynamicGraphExecutor`:

1. **Topological Execution:** Nodes execute according to explicit topological dependencies (validated via Kahn's algorithm).
2. **Runtime Task Yielding:** Workflows can dynamically expand graph nodes via `yield_task` while remaining subject to strict system limits.
3. **Execution Safety Boundaries:** Enforces `max_steps` cap (default 50 steps), node execution timeouts (`asyncio.wait_for`), and per-workflow cost budget limits (`max_budget_usd`).

## Consequences
- **Pros:** Deterministic execution, predictable cost caps, zero runaway infinite loops, reproducible debugging.
- **Cons:** Less open-ended exploratory behavior compared to un-constrained ReAct agent loops.
