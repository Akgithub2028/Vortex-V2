"""
Fluent Workflow graph builder for the Vortex Python SDK.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class WorkflowNode(BaseModel):
    """Workflow node specification."""

    id: str
    type: str  # llm | tool | branch | parallel | eval | human
    config: dict[str, Any] = Field(default_factory=dict)
    dependencies: list[str] = Field(default_factory=list)


def yield_task(
    node_id: str,
    type: str,
    config: dict[str, Any] | None = None,
    dependencies: list[str] | None = None,
) -> dict[str, Any]:
    """SDK helper to dynamically yield sub-tasks at runtime."""
    return {
        "_yielded_nodes": [
            {
                "id": node_id,
                "type": type,
                "config": config or {},
                "dependencies": dependencies or [],
            }
        ]
    }


class Workflow(BaseModel):
    """
    Fluent DAG builder for defining Vortex workflows programmatically.

    Example:
        >>> wf = Workflow(name="summary-pipeline")
        >>> wf.add_llm_node("summarize", prompt="Summarize: {text}")
        >>> wf.add_eval_node("check_quality", target_node="summarize", dependencies=["summarize"])
        >>> payload = wf.to_dict()
    """

    name: str
    version: int = 1
    description: str | None = None
    nodes: list[WorkflowNode] = Field(default_factory=list)

    def add_llm_node(
        self,
        node_id: str,
        prompt: str,
        model: str = "openai/gpt-4o",
        temperature: float = 0.7,
        dependencies: list[str] | None = None,
    ) -> Workflow:
        """Add an LLM inference node."""
        node = WorkflowNode(
            id=node_id,
            type="llm",
            config={
                "prompt": prompt,
                "model": model,
                "temperature": temperature,
            },
            dependencies=dependencies or [],
        )
        self.nodes.append(node)
        return self

    def add_tool_node(
        self,
        node_id: str,
        tool_name: str,
        tool_args: dict[str, Any] | None = None,
        dependencies: list[str] | None = None,
    ) -> Workflow:
        """Add a tool/function execution node."""
        node = WorkflowNode(
            id=node_id,
            type="tool",
            config={
                "tool_name": tool_name,
                "tool_args": tool_args or {},
            },
            dependencies=dependencies or [],
        )
        self.nodes.append(node)
        return self

    def add_branch_node(
        self,
        node_id: str,
        condition_variable: str,
        truthy_target: str,
        falsy_target: str,
        dependencies: list[str] | None = None,
    ) -> Workflow:
        """Add a conditional routing branch node."""
        node = WorkflowNode(
            id=node_id,
            type="branch",
            config={
                "condition_variable": condition_variable,
                "truthy_target": truthy_target,
                "falsy_target": falsy_target,
            },
            dependencies=dependencies or [],
        )
        self.nodes.append(node)
        return self

    def add_parallel_node(
        self,
        node_id: str,
        branches: list[str],
        dependencies: list[str] | None = None,
    ) -> Workflow:
        """Add a parallel fan-out node."""
        node = WorkflowNode(
            id=node_id,
            type="parallel",
            config={"branches": branches},
            dependencies=dependencies or [],
        )
        self.nodes.append(node)
        return self

    def add_eval_node(
        self,
        node_id: str,
        target_node: str,
        scorer_name: str = "faithfulness",
        threshold: float = 0.7,
        dependencies: list[str] | None = None,
    ) -> Workflow:
        """Add an inline quality evaluation gate node."""
        node = WorkflowNode(
            id=node_id,
            type="eval",
            config={
                "target_node": target_node,
                "scorer_name": scorer_name,
                "threshold": threshold,
            },
            dependencies=dependencies or [],
        )
        self.nodes.append(node)
        return self

    def add_human_node(
        self,
        node_id: str,
        instructions: str = "Review output before proceeding",
        dependencies: list[str] | None = None,
    ) -> Workflow:
        """Add a human-in-the-loop (HITL) approval pause node."""
        node = WorkflowNode(
            id=node_id,
            type="human",
            config={"instructions": instructions},
            dependencies=dependencies or [],
        )
        self.nodes.append(node)
        return self

    def to_dict(self) -> dict[str, Any]:
        """Export workflow specification dictionary payload."""
        return self.model_dump(mode="json")
