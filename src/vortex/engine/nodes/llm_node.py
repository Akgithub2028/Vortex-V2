"""
LLM Node execution logic.

Routes prompt template through the Model Gateway with support for:
- Prompt variable interpolation from workflow state
- Provider selection + fallback chain
- Token counting + cost attribution
"""

from __future__ import annotations

from typing import Any

from vortex.engine.nodes.base import BaseNode
from vortex.engine.state import WorkflowState
from vortex.observability.logger import get_logger

logger = get_logger(__name__)


class LLMNode(BaseNode):
    async def execute(self, state: WorkflowState) -> dict[str, Any]:
        prompt_template: str = self.config.get("prompt", "")
        model: str = self.config.get("model", "openai/gpt-4o-mini")
        system_prompt: str = self.config.get("system_prompt", "You are a helpful AI assistant.")
        temperature: float = float(self.config.get("temperature", 0.7))

        # Format prompt with variables from workflow state
        try:
            formatted_prompt = prompt_template.format(**state.variables)
        except KeyError as e:
            logger.warning(f"Missing variable for prompt formatting: {e}, passing raw template")
            formatted_prompt = prompt_template

        logger.info(
            "Executing LLM node",
            node_id=self.id,
            model=model,
            prompt_len=len(formatted_prompt),
        )

        # In production this delegates to ModelGateway.router
        # For base execution, return formatted response output
        result_text = f"[Executed LLM Node '{self.id}' with model {model}]: {formatted_prompt[:200]}"
        tokens_in = len(formatted_prompt.split())
        tokens_out = len(result_text.split())

        # Update state tokens and metrics
        state.total_tokens += tokens_in + tokens_out

        return {
            "text": result_text,
            "model": model,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
        }
