"""
Abstract Base Guardrail Validator interface.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field


class GuardrailResult(BaseModel):
    validator_name: str
    passed: bool
    risk_score: float = Field(default=0.0, description="Risk score from 0.0 (safe) to 1.0 (unsafe)")
    reason: str | None = None
    scrubbed_text: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class BaseValidator(ABC):
    """Abstract base class for all guardrail validators."""

    @property
    @abstractmethod
    def validator_name(self) -> str:
        pass

    @abstractmethod
    async def validate(self, text: str) -> GuardrailResult:
        """
        Validate input or output text.

        Returns GuardrailResult with passed boolean, risk score, and optional scrubbed text.
        """
        pass
