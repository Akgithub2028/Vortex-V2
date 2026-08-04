"""
Central Guardrails Execution Engine.

Executes configured validators (prompt injection, PII, content policy)
and enforces action policies (warn | block).
"""

from __future__ import annotations

from typing import Literal

from vortex.api.errors import GuardrailBlockError
from vortex.config import get_settings
from vortex.guardrails.validators.base import BaseValidator, GuardrailResult
from vortex.guardrails.validators.content_policy import ContentPolicyValidator
from vortex.guardrails.validators.pii import PIIValidator
from vortex.guardrails.validators.prompt_injection import PromptInjectionValidator
from vortex.observability.logger import get_logger
from vortex.observability.metrics import GUARDRAIL_CHECKS_TOTAL

logger = get_logger(__name__)


class GuardrailsEngine:
    """Orchestrates inline input and output guardrail validation."""

    def __init__(self, validators: list[BaseValidator] | None = None):
        self.validators = validators or [
            PromptInjectionValidator(),
            PIIValidator(),
            ContentPolicyValidator(),
        ]

    async def inspect(
        self,
        text: str,
        action: Literal["warn", "block"] = "warn",
    ) -> tuple[str, list[GuardrailResult]]:
        """
        Inspect text across all registered validators.

        Args:
            text: Raw input or output prompt text.
            action: Policy action if a check fails ('warn' or 'block').

        Returns:
            Tuple of (processed_text, list of GuardrailResult objects).

        Raises:
            GuardrailBlockError: If action='block' and any validator fails.
        """
        settings = get_settings()

        if not settings.guardrails_enabled:
            return text, []

        current_text = text
        results: list[GuardrailResult] = []

        for validator in self.validators:
            result = await validator.validate(current_text)
            results.append(result)

            # Record Prometheus metrics
            result_str = "pass" if result.passed else ("warn" if action == "warn" else "block")
            GUARDRAIL_CHECKS_TOTAL.labels(
                guardrail_type=validator.validator_name,
                result=result_str,
            ).inc()

            # Apply scrubbed text if PII was redacted
            if result.scrubbed_text:
                current_text = result.scrubbed_text

            # Enforce block action
            if not result.passed and action == "block":
                logger.error(
                    "Guardrail BLOCKED request",
                    validator=validator.validator_name,
                    reason=result.reason,
                )
                raise GuardrailBlockError(
                    guardrail_type=validator.validator_name,
                    reason=result.reason or "Risk score exceeded threshold.",
                )

        return current_text, results
