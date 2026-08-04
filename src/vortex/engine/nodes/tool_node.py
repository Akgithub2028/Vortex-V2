"""
Tool Node execution logic — executes tool/function calls in a sandboxed execution context.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

from vortex.engine.nodes.base import BaseNode
from vortex.observability.logger import get_logger

if TYPE_CHECKING:
    from vortex.engine.state import WorkflowState

logger = get_logger(__name__)


class ToolNode(BaseNode):
    async def execute(self, state: WorkflowState) -> dict[str, Any]:
        tool_name: str = self.config.get("tool_name", "custom_tool")
        arguments: dict[str, Any] = self.config.get("arguments", {})

        # Resolve argument placeholders from variables
        resolved_args = {}
        for k, v in arguments.items():
            if isinstance(v, str) and v.startswith("$"):
                var_key = v[1:]
                resolved_args[k] = state.variables.get(var_key, v)
            else:
                resolved_args[k] = v

        logger.info("Executing Tool node", node_id=self.id, tool=tool_name, args=resolved_args)

        # Simulate async tool execution
        await asyncio.sleep(0.01)

        result_data = {
            "status": "success",
            "tool": tool_name,
            "result": f"Executed tool '{tool_name}' with args {resolved_args}",
        }

        return result_data
