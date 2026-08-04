"""
Branch Node execution logic — evaluates conditional logic to route workflow execution.
"""

from __future__ import annotations

from typing import Any

from vortex.engine.nodes.base import BaseNode
from vortex.engine.state import WorkflowState
from vortex.observability.logger import get_logger

logger = get_logger(__name__)


class BranchNode(BaseNode):
    async def execute(self, state: WorkflowState) -> dict[str, Any]:
        condition_var: str = self.config.get("condition_var", "")
        expected_value: Any = self.config.get("expected_value", True)
        true_node: str = self.config.get("true_node", "")
        false_node: str = self.config.get("false_node", "")

        actual_value = state.variables.get(condition_var)
        condition_met = actual_value == expected_value

        selected_branch = true_node if condition_met else false_node

        logger.info(
            "Executing Branch node",
            node_id=self.id,
            var=condition_var,
            actual=actual_value,
            expected=expected_value,
            selected=selected_branch,
        )

        return {
            "condition_met": condition_met,
            "selected_branch": selected_branch,
        }
