"""
Scorers factory and package init.
"""

from __future__ import annotations

from vortex.eval.scorers.base import BaseScorer, EvalScoreResult
from vortex.eval.scorers.faithfulness import FaithfulnessScorer
from vortex.eval.scorers.relevance import RelevanceScorer
from vortex.eval.scorers.toxicity import ToxicityScorer


def get_scorer(scorer_name: str, threshold: float = 0.7) -> BaseScorer:
    name = scorer_name.lower()
    if name == "faithfulness":
        return FaithfulnessScorer(threshold)
    elif name == "relevance":
        return RelevanceScorer(threshold)
    elif name == "toxicity":
        return ToxicityScorer(threshold)
    else:
        return FaithfulnessScorer(threshold)


__all__ = [
    "BaseScorer",
    "EvalScoreResult",
    "FaithfulnessScorer",
    "RelevanceScorer",
    "ToxicityScorer",
    "get_scorer",
]
