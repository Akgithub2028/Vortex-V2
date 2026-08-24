"""
Tool Registry and Execution Engine.

Provides type-safe registration, schema validation, and execution of tool functions for ToolNode.
"""

from __future__ import annotations

import json
from typing import Any, Callable

from vortex.observability.logger import get_logger

logger = get_logger(__name__)


class ToolRegistration:
    def __init__(
        self,
        name: str,
        func: Callable[..., Any],
        description: str = "",
        parameters_schema: dict[str, Any] | None = None,
    ):
        self.name = name
        self.func = func
        self.description = description
        self.parameters_schema = parameters_schema or {}


class ToolRegistry:
    """Central registry for workflow tool execution."""

    def __init__(self):
        self._tools: dict[str, ToolRegistration] = {}
        self._register_default_tools()

    def register(
        self,
        name: str,
        func: Callable[..., Any],
        description: str = "",
        parameters_schema: dict[str, Any] | None = None,
    ) -> None:
        """Register a tool function."""
        self._tools[name.lower()] = ToolRegistration(
            name=name,
            func=func,
            description=description,
            parameters_schema=parameters_schema,
        )
        logger.info("Registered tool", tool_name=name)

    def get_tool(self, name: str) -> ToolRegistration | None:
        return self._tools.get(name.lower())

    def list_tools(self) -> list[dict[str, Any]]:
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "parameters_schema": tool.parameters_schema,
            }
            for tool in self._tools.values()
        ]

    async def execute_tool(self, name: str, kwargs: dict[str, Any]) -> dict[str, Any]:
        """Execute registered tool by name with arguments."""
        tool = self.get_tool(name)
        if not tool:
            raise KeyError(f"Tool '{name}' is not registered in ToolRegistry.")

        logger.info("Executing tool", tool_name=name, kwargs=kwargs)

        try:
            import inspect

            if inspect.iscoroutinefunction(tool.func):
                result = await tool.func(**kwargs)
            else:
                result = tool.func(**kwargs)

            if isinstance(result, dict):
                return result
            return {"result": result}
        except Exception as e:
            logger.error("Tool execution failed", tool_name=name, error=str(e))
            raise RuntimeError(f"Tool '{name}' execution failed: {e!s}") from e

    def _register_default_tools(self) -> None:
        """Register standard built-in tools."""
        self.register(
            name="text_processor",
            func=_text_processor_tool,
            description="Process or format input text strings.",
            parameters_schema={
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "action": {"type": "string", "enum": ["uppercase", "lowercase", "word_count", "reverse"]},
                },
                "required": ["text"],
            },
        )

        self.register(
            name="json_extractor",
            func=_json_extractor_tool,
            description="Extract specific keys from JSON string payloads.",
            parameters_schema={
                "type": "object",
                "properties": {
                    "json_string": {"type": "string"},
                    "key": {"type": "string"},
                },
                "required": ["json_string"],
            },
        )

        self.register(
            name="web_search_stub",
            func=_web_search_stub_tool,
            description="Execute web search query for factual research.",
            parameters_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "limit": {"type": "integer", "default": 3},
                },
                "required": ["query"],
            },
        )


def _text_processor_tool(text: str, action: str = "uppercase") -> dict[str, Any]:
    action = action.lower()
    if action == "uppercase":
        res = text.upper()
    elif action == "lowercase":
        res = text.lower()
    elif action == "reverse":
        res = text[::-1]
    elif action == "word_count":
        res = str(len(text.split()))
    else:
        res = text

    return {"processed_text": res, "action": action, "original_length": len(text)}


def _json_extractor_tool(json_string: str, key: str | None = None) -> dict[str, Any]:
    try:
        data = json.loads(json_string)
        if key and isinstance(data, dict):
            extracted = data.get(key)
        else:
            extracted = data
        return {"extracted_data": extracted, "success": True}
    except Exception as e:
        return {"extracted_data": None, "success": False, "error": str(e)}


def _web_search_stub_tool(query: str, limit: int = 3) -> dict[str, Any]:
    results = [
        {"title": f"Overview of {query}", "snippet": f"Detailed factual information regarding {query}.", "url": f"https://example.com/search?q={query}"},
        {"title": f"{query} - Key Insights", "snippet": f"Recent developments and benchmark data for {query}.", "url": f"https://example.org/{query}"},
    ][:limit]

    return {"query": query, "results": results, "total_results": len(results)}


# Global default singleton registry
tool_registry = ToolRegistry()
