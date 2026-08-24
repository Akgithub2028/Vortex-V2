# ADR 001: Event Sourcing & CQRS State Management

- **Status:** Accepted
- **Date:** 2026-08-24
- **Context:** Workflow execution engines must provide durable state persistence, auditability, and fault tolerance across worker crashes and restarts. Standard mutable database updates lose execution history and complicate time-travel debugging.

## Decision
We adopt **Command Query Responsibility Segregation (CQRS) with an Append-Only Event Store**:

1. **Append-Only Event Log (`EventStore`):** All workflow state mutations (`WorkflowStarted`, `NodeStarted`, `NodeCompleted`, `TaskYielded`, `WorkflowCompleted`) are written as immutable event records in PostgreSQL.
2. **Materialized Read Models (`StateProjector`):** A projection process updates indexed read tables (`WorkflowRun`, `NodeRun`) for fast API queries (`GET /v1/workflows/{id}`).

## Consequences
- **Pros:** Full auditability, cryptographic payload encryption support, crash recovery without lost state, sub-millisecond query performance for read traffic.
- **Cons:** Slightly higher write latency and storage footprint compared to in-place entity mutations.
