"""
PII (Personally Identifiable Information) Detector & Redactor.

Scans and scrubs emails, phone numbers, SSNs, credit cards, and IP addresses.
"""

from __future__ import annotations

import re
from typing import ClassVar

from vortex.guardrails.validators.base import BaseValidator, GuardrailResult
from vortex.observability.logger import get_logger

logger = get_logger(__name__)


class PIIValidator(BaseValidator):
    """Detects and redacts PII data from text."""

    PII_RULES: ClassVar[list[tuple[str, str, str]]] = [
        # (name, regex pattern, replacement token)
        ("EMAIL", r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "[EMAIL_REDACTED]"),
        ("PHONE", r"\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b", "[PHONE_REDACTED]"),
        ("SSN", r"\b\d{3}-\d{2}-\d{4}\b", "[SSN_REDACTED]"),
        ("CREDIT_CARD", r"\b(?:\d[ -]*?){13,16}\b", "[CARD_REDACTED]"),
        ("IP_ADDRESS", r"\b(?:\d{1,3}\.){3}\d{1,3}\b", "[IP_REDACTED]"),
    ]

    @property
    def validator_name(self) -> str:
        return "pii_redactor"

    async def validate(self, text: str) -> GuardrailResult:
        scrubbed = text
        detected_types: list[str] = []

        for pii_type, pattern, replacement in self.PII_RULES:
            if re.search(pattern, scrubbed):
                detected_types.append(pii_type)
                scrubbed = re.sub(pattern, replacement, scrubbed)

        has_pii = len(detected_types) > 0
        risk_score = 0.8 if has_pii else 0.0

        if has_pii:
            logger.info("PII detected and redacted", types=detected_types)

        return GuardrailResult(
            validator_name=self.validator_name,
            passed=True,  # Passed because PII is successfully scrubbed
            risk_score=risk_score,
            reason=f"Redacted {len(detected_types)} PII items: {', '.join(detected_types)}" if has_pii else None,
            scrubbed_text=scrubbed if has_pii else text,
            details={"pii_detected": detected_types},
        )
