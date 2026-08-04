"""
Node factory mapping node definitions to BaseNode instances.
"""

from __future__ import annotations

from vortex.engine.nodes.base import BaseNode
from vortex.engine.nodes.branch_node import BranchNode
from vortex.engine.nodes.eval_node import EvalNode
from vortex.engine.nodes.human_node import HumanNode
from vortex.engine.nodes.llm_node import LLMNode
from vortex.engine.nodes.parallel_node import ParallelNode
from vortex.engine.nodes.tool_node import ToolNode
from vortex.engine.state import NodeDefinition


def create_node(definition: NodeDefinition) -> BaseNode:
    """Factory function mapping NodeDefinition to concrete BaseNode subclass."""
    node_type = definition.type
    if node_type == "llm":
        return LLMNode(definition)
    elif node_type == "tool":
        return ToolNode(definition)
    elif node_type == "branch":
        return BranchNode(definition)
    elif node_type == "parallel":
        return ParallelNode(definition)
    elif node_type == "eval":
        return EvalNode(definition)
    elif node_type == "human":
        return HumanNode(definition)
    else:
        raise ValueError(f"Unknown node type '{node_type}'.")


__all__ = [
    "BaseNode",
    "BranchNode",
    "EvalNode",
    "HumanNode",
    "LLMNode",
    "ParallelNode",
    "ToolNode",
    "create_node",
]
