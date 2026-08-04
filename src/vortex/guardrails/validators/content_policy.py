"""
Content Policy & Safety Validator.

Scans for toxic content, self-harm instructions, malware generation, and illegal activities.
"""

from __future__ import annotations

import re
from typing import ClassVar

from vortex.guardrails.validators.base import BaseValidator, GuardrailResult
from vortex.observability.logger import get_logger

logger = get_logger(__name__)


class ContentPolicyValidator(BaseValidator):
    POLICY_PATTERNS: ClassVar[list[tuple[str, float, str]]] = [
        (r"(?i)how\ (to\ )?(build|make)\ a\ (bomb|weapon|explosive)", 0.99, "Weapons/Explosives policy violation"),
        (r"(?i)write\ a\ (keylogger|ransomware|trojan|rootkit)", 0.95, "Malware generation policy violation"),
        (r"(?i)how\ to\ (commit|perform)\ self-harm", 0.99, "Self-harm policy violation"),
        (r"(?i)generate\ (hate\ speech|racist\ slur)", 0.90, "Hate speech policy violation"),
    ]

    @property
    def validator_name(self) -> str:
        return "content_policy"

    async def validate(self, text: str) -> GuardrailResult:
        max_risk = 0.0
        violations: list[str] = []

        for pattern, risk, desc in self.POLICY_PATTERNS:
            if re.search(pattern, text):
                max_risk = max(max_risk, risk)
                violations.append(desc)

        passed = max_risk < 0.80
        reason = "; ".join(violations) if violations else None

        if not passed:
            logger.warning("Content policy violation detected", risk_score=max_risk, reason=reason)

        return GuardrailResult(
            validator_name=self.validator_name,
            passed=passed,
            risk_score=max_risk,
            reason=reason,
            details={"violations": violations},
        )
