"""
Faithfulness & Hallucination Scorer.

Evaluates whether statements in generated output are supported by the reference context.
"""

import json
from typing import ClassVar

from vortex.config import get_settings
from vortex.gateway.providers import get_provider
from vortex.gateway.providers.base import CompletionRequest
from vortex.eval.scorers.base import BaseScorer, EvalScoreResult
from vortex.observability.logger import get_logger
from vortex.observability.metrics import EVAL_SCORES

logger = get_logger(__name__)


class FaithfulnessScorer(BaseScorer):
    
    SYSTEM_PROMPT: ClassVar[str] = (
        "You are an expert AI evaluator. Compare the 'Output' to the 'Reference Context'. "
        "Does the output contain any information that is NOT supported by the reference context? "
        "Respond with a JSON object exactly like this: "
        '{"is_faithful": true/false, "confidence": 0.0-1.0, "reason": "brief explanation"}'
    )

    def __init__(self, provider_name: str = "openai", model_name: str = "gpt-4o-mini", threshold: float = 0.8):
        super().__init__(threshold=threshold)
        settings = get_settings()
        self.provider_name = provider_name
        self.model_name = model_name
        self.api_key = getattr(settings, f"{self.provider_name}_api_key", "mock-key")
        self.provider = get_provider(self.provider_name, self.api_key)

    @property
    def scorer_name(self) -> str:
        return "faithfulness"

    async def score(
        self,
        output: str,
        input_prompt: str | None = None,
        reference_context: str | None = None,
    ) -> EvalScoreResult:
        if not output:
            return EvalScoreResult(
                scorer_name=self.scorer_name,
                score=0.0,
                passed=False,
                threshold=self.threshold,
                reasoning="Output text is empty.",
            )

        if not reference_context:
            return EvalScoreResult(
                scorer_name=self.scorer_name,
                score=0.5,
                passed=False,
                threshold=self.threshold,
                reasoning="No reference context provided.",
            )

        try:
            req = CompletionRequest(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": f"<REFERENCE_CONTEXT>\n{reference_context}\n</REFERENCE_CONTEXT>\n<OUTPUT>\n{output}\n</OUTPUT>"}
                ],
                temperature=0.0,
            )
            
            resp = await self.provider.complete(req)
            content = resp.content.replace("```json", "").replace("```", "").strip()
            
            import re
            json_match = re.search(r'(\{.*\})', content, re.DOTALL)
            if json_match:
                content = json_match.group(1)
                
            try:
                result = json.loads(content)
            except Exception as parse_e:
                logger.error("JSON parse error", content=content, error=str(parse_e))
                result = {}
            
            is_faithful = result.get("is_faithful", False)
            confidence = result.get("confidence", 0.0)
            reason = result.get("reason", "No reason provided")
            
            calc_score = confidence if is_faithful else (1.0 - confidence)
            passed = calc_score >= self.threshold
            
            EVAL_SCORES.labels(scorer_name=self.scorer_name).observe(calc_score)
            
            return EvalScoreResult(
                scorer_name=self.scorer_name,
                score=calc_score,
                passed=passed,
                threshold=self.threshold,
                reasoning=reason,
            )
            
        except Exception as e:
            logger.error("FaithfulnessScorer failed", error=str(e))
            return EvalScoreResult(
                scorer_name=self.scorer_name,
                score=0.0,
                passed=False,
                threshold=self.threshold,
                reasoning=f"LLM API Evaluation Failed: {str(e)}",
            )
