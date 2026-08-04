"""
Abstract base node interface for Vortex engine.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from vortex.engine.state import NodeDefinition, WorkflowState


class BaseNode(ABC):
    """Abstract base class for all DAG execution nodes."""

    def __init__(self, definition: NodeDefinition):
        self.definition = definition
        self.id = definition.id
        self.type = definition.type
        self.config = definition.config

    @abstractmethod
    async def execute(self, state: WorkflowState) -> dict[str, Any]:
        """
        Execute node logic.

        Args:
            state: Current WorkflowState snapshot containing completed node outputs and variables.

        Returns:
            dict containing node outputs to be stored in `state.completed_nodes[self.id]`
            and merged into `state.variables`.
        """
        pass
