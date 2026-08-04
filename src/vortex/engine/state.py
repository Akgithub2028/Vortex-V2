"""
Vortex Workflow State Machine and Schema.

Defines:
- WorkflowStatus & NodeStatus enums
- WorkflowState checkpoint object
- NodeDefinition & DAG models
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import TYPE_CHECKING, Any, Literal

from pydantic import BaseModel, Field


class WorkflowStatus(StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"


class NodeStatus(StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"


NodeType = Literal["llm", "tool", "branch", "parallel", "eval", "human"]


class NodeDefinition(BaseModel):
    """Definition of a single node in a Workflow DAG."""

    id: str = Field(..., description="Unique node ID within the DAG")
    type: NodeType = Field(..., description="Type of node")
    name: str | None = Field(None, description="Human-readable node name")
    dependencies: list[str] = Field(default_factory=list, description="IDs of upstream nodes that must complete before this node runs")

    # Node-specific configuration parameters
    config: dict[str, Any] = Field(default_factory=dict)
    max_retries: int | None = Field(None, description="Override default max retries")
    timeout_seconds: float | None = Field(None, description="Node timeout in seconds")


class DAGDefinition(BaseModel):
    """Complete Workflow DAG specification."""

    name: str = Field(..., description="Workflow name")
    version: int = Field(default=1, description="Workflow version")
    nodes: list[NodeDefinition] = Field(..., description="List of nodes in the DAG")
    config: dict[str, Any] = Field(default_factory=dict, description="Workflow-level configuration")

    def get_node(self, node_id: str) -> NodeDefinition:
        for node in self.nodes:
            if node.id == node_id:
                return node
        raise ValueError(f"Node '{node_id}' not found in DAG.")


class WorkflowState(BaseModel):
    """
    Serializable checkpoint object for a running workflow.

    Persisted to PostgreSQL `workflow_runs.checkpoint` JSONB after each node completes.
    Enables 100% crash recovery and time-travel debugging.
    """

    run_id: uuid.UUID
    tenant_id: uuid.UUID
    definition_id: uuid.UUID | None = None
    status: WorkflowStatus = WorkflowStatus.PENDING

    # Node execution state
    current_nodes: list[str] = Field(default_factory=list, description="Currently executing node IDs")
    completed_nodes: dict[str, Any] = Field(default_factory=dict, description="Map of node_id -> output result dict")
    failed_nodes: dict[str, str] = Field(default_factory=dict, description="Map of node_id -> error message")
    skipped_nodes: list[str] = Field(default_factory=list, description="List of skipped node IDs")
    retry_counts: dict[str, int] = Field(default_factory=dict, description="Map of node_id -> retry count")

    # Workflow variable store
    variables: dict[str, Any] = Field(default_factory=dict, description="Accumulated global state variables passed between nodes")

    # Metrics accumulation
    total_tokens: int = 0
    total_cost_usd: Decimal = Decimal("0.0")

    # Checkpoint versioning for optimistic locking
    version: int = 1
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    def is_terminal(self) -> bool:
        return self.status in (WorkflowStatus.COMPLETED, WorkflowStatus.FAILED, WorkflowStatus.CANCELLED)

    def mark_completed(self) -> None:
        self.status = WorkflowStatus.COMPLETED

    def mark_failed(self, error: str) -> None:
        self.status = WorkflowStatus.FAILED
        self.variables["_workflow_error"] = error
