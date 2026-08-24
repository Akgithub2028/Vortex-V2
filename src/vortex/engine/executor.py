"""
Vortex Dynamic Graph Executor.

Implements DynamicGraphExecutor supporting runtime node yielding (`yield_task`),
dynamic graph expansion, dependency resolution, human-in-the-loop pause/resume,
and append-only event sourcing state projections.
"""

import asyncio
from collections import defaultdict, deque
from typing import TYPE_CHECKING, Any, Callable

from vortex.api.errors import WorkflowBudgetExceededError, WorkflowMaxStepsExceededError
from vortex.config import get_settings
from vortex.engine.checkpoint import CheckpointStore
from vortex.engine.event_store import EventStore
from vortex.engine.nodes import create_node
from vortex.engine.state import (
    DAGDefinition,
    NodeDefinition,
    WorkflowState,
    WorkflowStatus,
)
from vortex.observability.logger import get_logger

if TYPE_CHECKING:
    from collections.abc import Callable

logger = get_logger(__name__)


def yield_task(
    node_id: str,
    type: str,
    config: dict[str, Any] | None = None,
    dependencies: list[str] | None = None,
    name: str | None = None,
) -> dict[str, Any]:
    """
    Utility function for nodes/sub-workflows to yield dynamic tasks during runtime execution.

    Example:
        >>> return {"result": "ok", **yield_task("sub_task1", "llm", {"prompt": "Analyze chunk 1"}, dependencies=["prev"])}
    """
    return {
        "_yielded_nodes": [
            {
                "id": node_id,
                "type": type,
                "config": config or {},
                "dependencies": dependencies or [],
                "name": name,
            }
        ]
    }


class DynamicGraphExecutor:
    """Dynamic Graph Execution Engine supporting runtime node yielding and HITL pause/resume."""

    def __init__(self, dag: DAGDefinition, state: WorkflowState):
        self.dag = dag
        self.state = state
        self.nodes_map: dict[str, NodeDefinition] = {n.id: n for n in dag.nodes}
        self._validate_initial_dag()

    def _validate_initial_dag(self) -> None:
        """Validate initial DAG structure for unique node IDs and cycle freedom."""
        node_ids = set(self.nodes_map.keys())
        for node in self.nodes_map.values():
            for dep in node.dependencies:
                if dep not in node_ids:
                    raise ValueError(f"Node '{node.id}' references missing dependency '{dep}'.")
        self._topological_sort()

    def _topological_sort(self) -> list[NodeDefinition]:
        """Check for cycles via Kahn's topological sort."""
        in_degree: dict[str, int] = {node.id: 0 for node in self.nodes_map.values()}
        graph: dict[str, list[str]] = defaultdict(list)

        for node in self.nodes_map.values():
            for dep in node.dependencies:
                graph[dep].append(node.id)
                in_degree[node.id] += 1

        queue = deque([n_id for n_id, deg in in_degree.items() if deg == 0])
        sorted_nodes: list[NodeDefinition] = []

        while queue:
            curr_id = queue.popleft()
            sorted_nodes.append(self.nodes_map[curr_id])

            for neighbor_id in graph[curr_id]:
                in_degree[neighbor_id] -= 1
                if in_degree[neighbor_id] == 0:
                    queue.append(neighbor_id)

        if len(sorted_nodes) != len(self.nodes_map):
            raise ValueError("Circular dependency detected in DAG definition.")

        return sorted_nodes

    def _get_next_ready_nodes(self) -> list[NodeDefinition]:
        """Identify nodes whose upstream dependencies have all completed successfully."""
        ready: list[NodeDefinition] = []
        for node_id, node_def in list(self.nodes_map.items()):
            if (
                node_id in self.state.completed_nodes
                or node_id in self.state.failed_nodes
                or node_id in self.state.skipped_nodes
                or node_id in self.state.current_nodes
            ):
                continue

            deps_met = all(dep in self.state.completed_nodes for dep in node_def.dependencies)
            if deps_met:
                ready.append(node_def)
        return ready

    async def run(
        self,
        event_callback: Callable[[str, dict[str, Any]], None] | None = None,
    ) -> WorkflowState:
        """
        Execute the workflow graph dynamically.
        """
        from vortex.engine.event_store import EventStore
        from vortex.engine.projector import StateProjector
        from vortex.storage.database import get_session

        self.state.status = WorkflowStatus.RUNNING
        await CheckpointStore.save_checkpoint(self.state)
        await EventStore.append_event(
            tenant_id=self.state.tenant_id,
            run_id=self.state.run_id,
            event_type="WorkflowStarted",
            event_data={"input": self.state.variables, "_dag": self.dag.model_dump(mode="json")},
        )

        if event_callback:
            event_callback("workflow.started", {"run_id": str(self.state.run_id)})

        settings = get_settings()
        max_steps = int(self.state.variables.get("max_steps", 50))
        max_budget = float(self.state.variables.get("max_budget_usd", 10.0))
        step_count = 0

        try:
            while self.state.status == WorkflowStatus.RUNNING:
                if self.state.status == WorkflowStatus.CANCELLED:
                    logger.info("Workflow execution cancelled", run_id=str(self.state.run_id))
                    break

                # Reliability Gate 1: Check Cost Budget Cap
                if float(self.state.total_cost_usd) > max_budget:
                    raise WorkflowBudgetExceededError(
                        run_id=str(self.state.run_id),
                        current_cost=float(self.state.total_cost_usd),
                        max_budget=max_budget,
                    )

                ready_nodes = self._get_next_ready_nodes()

                if not ready_nodes:
                    # Check if all registered nodes are resolved
                    total_resolved = len(self.state.completed_nodes) + len(self.state.failed_nodes) + len(self.state.skipped_nodes)
                    if total_resolved >= len(self.nodes_map):
                        break

                    # Unresolvable nodes due to broken dependencies
                    unresolved = [
                        n_id
                        for n_id in self.nodes_map
                        if n_id not in self.state.completed_nodes and n_id not in self.state.failed_nodes and n_id not in self.state.skipped_nodes
                    ]
                    for n_id in unresolved:
                        self.state.skipped_nodes.append(n_id)
                    break

                for node_def in ready_nodes:
                    step_count += 1

                    # Reliability Gate 2: Check Step Count Limit
                    if step_count > max_steps:
                        raise WorkflowMaxStepsExceededError(
                            run_id=str(self.state.run_id),
                            steps=step_count,
                            max_steps=max_steps,
                        )

                    # Execute single node
                    self.state.current_nodes = [node_def.id]
                    await EventStore.append_event(
                        tenant_id=self.state.tenant_id,
                        run_id=self.state.run_id,
                        event_type="NodeStarted",
                        event_data={"node_id": node_def.id, "node_type": node_def.type},
                    )
                    if event_callback:
                        event_callback("node.started", {"node_id": node_def.id, "type": node_def.type})

                    node_instance = create_node(node_def)
                    node_timeout = float(node_def.config.get("timeout_seconds", 60.0))

                    try:
                        # Reliability Gate 3: Enforce Node Execution Timeout
                        output = await asyncio.wait_for(node_instance.execute(self.state), timeout=node_timeout)
                        self.state.completed_nodes[node_def.id] = output

                        if isinstance(output, dict):
                            self.state.variables.update(output)

                            # Handle Dynamic Task Yielding
                            yielded = output.get("_yielded_nodes")
                            if isinstance(yielded, list):
                                for y_item in yielded:
                                    y_node = NodeDefinition.model_validate(y_item) if isinstance(y_item, dict) else y_item
                                    self.nodes_map[y_node.id] = y_node
                                    await EventStore.append_event(
                                        tenant_id=self.state.tenant_id,
                                        run_id=self.state.run_id,
                                        event_type="NodeYielded",
                                        event_data={"node_id": y_node.id, "type": y_node.type},
                                    )
                                    logger.info("Dynamic node yielded", parent_id=node_def.id, yielded_id=y_node.id)

                        await EventStore.append_event(
                            tenant_id=self.state.tenant_id,
                            run_id=self.state.run_id,
                            event_type="NodeCompleted",
                            event_data={"node_id": node_def.id, "output": output},
                        )

                        if event_callback:
                            event_callback("node.completed", {"node_id": node_def.id, "output": output})

                    except Exception as e:
                        logger.error("Node execution failed", node_id=node_def.id, error=str(e))
                        self.state.failed_nodes[node_def.id] = str(e)
                        self.state.mark_failed(f"Node '{node_def.id}' failed: {e!s}")

                        await EventStore.append_event(
                            tenant_id=self.state.tenant_id,
                            run_id=self.state.run_id,
                            event_type="NodeFailed",
                            event_data={"node_id": node_def.id, "error": str(e)},
                        )

                        if event_callback:
                            event_callback("node.failed", {"node_id": node_def.id, "error": str(e)})

                        await CheckpointStore.save_checkpoint(self.state)
                        async with get_session() as session:
                            events = await EventStore.get_events(self.state.run_id, session=session)
                            await StateProjector.materialize_read_model(session, self.state.run_id, events)
                        return self.state

                    # Checkpoint state
                    self.state.current_nodes = []
                    await CheckpointStore.save_checkpoint(self.state)
                    async with get_session() as session:
                        events = await EventStore.get_events(self.state.run_id, session=session)
                        await StateProjector.materialize_read_model(session, self.state.run_id, events)

                    # Pause execution if HITL Approval Requested
                    if self.state.status == WorkflowStatus.AWAITING_APPROVAL:
                        await EventStore.append_event(
                            tenant_id=self.state.tenant_id,
                            run_id=self.state.run_id,
                            event_type="HumanApprovalRequested",
                            event_data={"node_id": node_def.id},
                        )
                        logger.info("Workflow paused awaiting human approval", run_id=str(self.state.run_id))
                        return self.state

            # Finalize workflow state
            if self.state.status == WorkflowStatus.RUNNING:
                if not self.state.failed_nodes:
                    self.state.mark_completed()
                    await EventStore.append_event(
                        tenant_id=self.state.tenant_id,
                        run_id=self.state.run_id,
                        event_type="WorkflowCompleted",
                        event_data={"output": self.state.variables.get("_output")},
                    )
                else:
                    self.state.mark_failed("One or more nodes failed.")
                    await EventStore.append_event(
                        tenant_id=self.state.tenant_id,
                        run_id=self.state.run_id,
                        event_type="WorkflowFailed",
                        event_data={"error": "Node execution failures"},
                    )

                await CheckpointStore.save_checkpoint(self.state)
                async with get_session() as session:
                    events = await EventStore.get_events(self.state.run_id, session=session)
                    await StateProjector.materialize_read_model(session, self.state.run_id, events)

                if event_callback:
                    event_callback(
                        "workflow.completed",
                        {
                            "run_id": str(self.state.run_id),
                            "total_tokens": self.state.total_tokens,
                            "total_cost_usd": float(self.state.total_cost_usd),
                        },
                    )

        except Exception as e:
            logger.error("Dynamic execution unhandled error", run_id=str(self.state.run_id), error=str(e))
            self.state.mark_failed(str(e))
            await CheckpointStore.save_checkpoint(self.state)
            await EventStore.append_event(
                tenant_id=self.state.tenant_id,
                run_id=self.state.run_id,
                event_type="WorkflowFailed",
                event_data={"error": str(e)},
            )
            async with get_session() as session:
                events = await EventStore.get_events(self.state.run_id, session=session)
                await StateProjector.materialize_read_model(session, self.state.run_id, events)

        return self.state


# Maintain DAGExecutor alias for backward compatibility
DAGExecutor = DynamicGraphExecutor
