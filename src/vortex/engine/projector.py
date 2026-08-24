"""
Vortex StateProjector — CQRS Read Model projection engine.

Reconstructs in-memory WorkflowState and materializes relational read models
(WorkflowRun, NodeRun) from ordered immutable event sequences.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timezone
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import select

from vortex.engine.state import WorkflowState, WorkflowStatus
from vortex.observability.logger import get_logger
from vortex.storage.models import NodeRun, WorkflowEvent, WorkflowRun

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger(__name__)


class StateProjector:
    """Projects immutable workflow events into state snapshots and read models."""

    @classmethod
    def project(cls, events: list[WorkflowEvent]) -> WorkflowState:
        """
        Reconstruct a WorkflowState snapshot from an ordered list of WorkflowEvent objects.
        """
        if not events:
            raise ValueError("Cannot project state from an empty event list.")

        first_event = events[0]
        state = WorkflowState(
            run_id=first_event.run_id,
            tenant_id=first_event.tenant_id,
            status=WorkflowStatus.PENDING,
            version=len(events),
            updated_at=datetime.now(UTC),
        )

        for event in events:
            cls.apply_event_to_state(state, event)

        return state

    @classmethod
    def apply_event_to_state(cls, state: WorkflowState, event: WorkflowEvent) -> None:
        """Apply a single event to modify the WorkflowState instance in-place."""
        data = event.event_data or {}

        if event.event_type == "WorkflowStarted":
            state.status = WorkflowStatus.RUNNING
            state.variables.update(data.get("input", {}))
            if "_dag" in data:
                state.variables["_dag"] = data["_dag"]

        elif event.event_type == "NodeScheduled":
            pass

        elif event.event_type == "NodeStarted":
            node_id = data.get("node_id")
            if node_id and node_id not in state.current_nodes:
                state.current_nodes.append(node_id)

        elif event.event_type == "NodeCompleted":
            node_id = data.get("node_id")
            if node_id:
                if node_id in state.current_nodes:
                    state.current_nodes.remove(node_id)
                output = data.get("output", {})
                state.completed_nodes[node_id] = output
                if isinstance(output, dict):
                    state.variables.update(output)
                state.variables[f"node_{node_id}_output"] = output

            tokens = data.get("tokens", 0)
            cost = Decimal(str(data.get("cost_usd", "0.0")))
            state.total_tokens += tokens
            state.total_cost_usd += cost

        elif event.event_type == "NodeFailed":
            node_id = data.get("node_id")
            if node_id:
                if node_id in state.current_nodes:
                    state.current_nodes.remove(node_id)
                err = data.get("error", "Unknown error")
                state.failed_nodes[node_id] = err

        elif event.event_type == "HumanApprovalRequested":
            state.status = WorkflowStatus.AWAITING_APPROVAL

        elif event.event_type == "HumanApproved":
            node_id = data.get("node_id")
            if node_id:
                state.completed_nodes[node_id] = data.get("output", {})
            state.status = WorkflowStatus.RUNNING

        elif event.event_type == "HumanRejected":
            node_id = data.get("node_id")
            if node_id:
                state.failed_nodes[node_id] = "Human rejected"
            state.status = WorkflowStatus.FAILED

        elif event.event_type == "WorkflowCompleted":
            state.status = WorkflowStatus.COMPLETED
            if "output" in data:
                state.variables["_output"] = data["output"]

        elif event.event_type == "WorkflowFailed":
            state.status = WorkflowStatus.FAILED
            if "error" in data:
                state.variables["_workflow_error"] = data["error"]

    @classmethod
    async def materialize_read_model(
        cls,
        session: AsyncSession,
        run_id: uuid.UUID,
        events: list[WorkflowEvent],
    ) -> WorkflowRun:
        """
        Asynchronously project event history into relational `WorkflowRun` and `NodeRun` read models.
        """
        if not events:
            raise ValueError("No events to materialize")

        state = cls.project(events)

        # Upsert WorkflowRun
        run = await session.get(WorkflowRun, run_id)
        if not run:
            stmt = select(WorkflowRun).where(WorkflowRun.id == run_id)
            res = await session.execute(stmt)
            run = res.scalar_one_or_none()

        first_event = events[0]
        if not run:
            run = WorkflowRun(
                id=run_id,
                tenant_id=first_event.tenant_id,
                status=state.status.value,
                input=state.variables,
                checkpoint=state.model_dump(mode="json"),
                total_tokens=state.total_tokens,
                total_cost_usd=state.total_cost_usd,
                started_at=events[0].timestamp,
                created_at=events[0].timestamp,
            )
            session.add(run)
        else:
            run.status = state.status.value
            run.checkpoint = state.model_dump(mode="json")
            run.total_tokens = state.total_tokens
            run.total_cost_usd = state.total_cost_usd
            if state.is_terminal():
                run.completed_at = datetime.now(UTC)
            if "_output" in state.variables:
                run.output = state.variables["_output"]
            session.add(run)

        # Update NodeRun records from event stream
        for event in events:
            if event.event_type in ("NodeStarted", "NodeCompleted", "NodeFailed"):
                data = event.event_data or {}
                node_id = data.get("node_id")
                if not node_id:
                    continue

                stmt = select(NodeRun).where(NodeRun.run_id == run_id, NodeRun.node_id == node_id)
                res = await session.execute(stmt)
                n_run = res.scalar_one_or_none()

                status_str = "RUNNING" if event.event_type == "NodeStarted" else ("COMPLETED" if event.event_type == "NodeCompleted" else "FAILED")

                if not n_run:
                    n_run = NodeRun(
                        id=uuid.uuid4(),
                        run_id=run_id,
                        node_id=node_id,
                        node_type=data.get("node_type", "llm"),
                        status=status_str,
                        input=data.get("input"),
                        output=data.get("output"),
                        error=data.get("error"),
                        tokens_in=data.get("tokens_in"),
                        tokens_out=data.get("tokens_out"),
                        cost_usd=Decimal(str(data["cost_usd"])) if "cost_usd" in data else None,
                        started_at=event.timestamp if event.event_type == "NodeStarted" else None,
                        completed_at=event.timestamp if event.event_type in ("NodeCompleted", "NodeFailed") else None,
                    )
                    session.add(n_run)
                else:
                    n_run.status = status_str
                    if data.get("output") is not None:
                        n_run.output = data["output"]
                    if data.get("error") is not None:
                        n_run.error = data["error"]
                    if event.event_type in ("NodeCompleted", "NodeFailed"):
                        n_run.completed_at = event.timestamp
                    session.add(n_run)

        await session.flush()
        return run
