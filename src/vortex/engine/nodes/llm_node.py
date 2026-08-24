"""
LLM Node execution logic.

Routes prompt template through the Model Gateway with support for:
- Prompt variable interpolation from workflow state
- Provider selection + fallback chain
- Token counting + cost attribution
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, Any

from vortex.engine.nodes.base import BaseNode
from vortex.gateway.providers.base import CompletionRequest
from vortex.gateway.router import ModelRouter
from vortex.observability.logger import get_logger

if TYPE_CHECKING:
    from vortex.engine.state import WorkflowState

logger = get_logger(__name__)

_router = ModelRouter()


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
            "Executing LLM node via ModelRouter",
            node_id=self.id,
            model=model,
            prompt_len=len(formatted_prompt),
        )

        output_schema = self.config.get("output_schema")
        response_format = None
        if output_schema:
            response_format = {"type": "json_schema", "json_schema": output_schema}

        req = CompletionRequest(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": formatted_prompt},
            ],
            temperature=temperature,
            response_format=response_format,
        )

        response = await _router.complete(req)

        # Update state accumulators
        tokens_in = response.tokens_input
        tokens_out = response.tokens_output
        state.total_tokens += tokens_in + tokens_out
        state.total_cost_usd += Decimal(str(response.cost_usd))

        return {
            "text": response.content,
            "model": response.model,
            "provider": response.provider,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "cost_usd": response.cost_usd,
        }
