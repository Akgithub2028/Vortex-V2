"""
Abstract Base Evaluation Scorer interface.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field


class EvalScoreResult(BaseModel):
    scorer_name: str
    score: float = Field(..., description="Score between 0.0 and 1.0")
    passed: bool
    threshold: float
    reasoning: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class BaseScorer(ABC):
    """Abstract base class for all LLM evaluation metric scorers."""

    def __init__(self, threshold: float = 0.7):
        self.threshold = threshold

    @property
    @abstractmethod
    def scorer_name(self) -> str:
        pass

    @abstractmethod
    async def score(
        self,
        output: str,
        input_prompt: str | None = None,
        reference_context: str | None = None,
    ) -> EvalScoreResult:
        """
        Evaluate generated output against input or reference context.

        Returns EvalScoreResult.
        """
        pass
