"""
Prompt Injection & Jailbreak Detector.

Scans prompt text for instruction override attempts, system prompt extraction,
DAN/jailbreak framing, and delimiter hijacking.
"""

from __future__ import annotations

import re
from typing import ClassVar

from vortex.guardrails.validators.base import BaseValidator, GuardrailResult
from vortex.observability.logger import get_logger

logger = get_logger(__name__)


class PromptInjectionValidator(BaseValidator):
    """Detects prompt injection and jailbreak attacks."""

    INJECTION_PATTERNS: ClassVar[list[tuple[str, float, str]]] = [
        # (regex pattern, risk weight, description)
        
        # Instruction Overrides
        (r"(?i)ignore\s+(all\s+)?(previous|above)\s+instructions?", 0.95, "Instruction override attempt"),
        (r"(?i)disregard\s+(all\s+)?(your\s+)?prior\s+directives?", 0.95, "Prior directive override"),
        (r"(?i)system\s+override", 0.90, "System override attempt"),
        (r"(?i)bypass\s+(authentication|security|firewall)", 0.95, "Security bypass attempt"),
        
        # Persona / Jailbreak Framing
        (r"(?i)you\s+are\s+(now\s+in\s+)?(DAN|Developer(\s+Mode)?|Jailbreak|malicious hacker)(\s+mode)?", 0.99, "Jailbreak mode framing"),
        (r"(?i)pretend\s+you\s+are\s+(an\s+)?unrestricted", 0.95, "Unrestricted persona framing"),
        (r"(?i)forget\s+your\s+previous\s+persona", 0.95, "Persona reset attempt"),
        (r"(?i)without\s+moral\s+constraints", 0.90, "Ethics bypass framing"),
        (r"(?i)\[INJECTION_SUCCESS\]", 0.99, "Injection payload signature"),
        
        # System Prompt Extraction
        (r"(?i)(dump|print|reveal|output)\s+(your\s+)?(system\s+prompt|initial\s+instructions|context)", 0.90, "System prompt extraction"),
        (r"(?i)repeat\s+the\s+words\s+above", 0.70, "Upstream text extraction"),
        
        # Malicious Actions & Payloads
        (r"(?i)build\s+a\s+bomb", 0.99, "Harmful instructions (explosives)"),
        (r"(?i)formula\s+for\s+meth", 0.99, "Harmful instructions (drugs)"),
        (r"(?i)(commit\s+)?identity\s+theft", 0.99, "Harmful instructions (fraud)"),
        (r"(?i)laundering\s+money", 0.99, "Harmful instructions (fraud)"),
        (r"(?i)explosive\s+device", 0.99, "Harmful instructions (explosives)"),
        (r"(?i)terrorist\s+organization", 0.99, "Harmful instructions (terrorism)"),
        (r"(?i)phishing\s+email", 0.95, "Cyberattack (Phishing)"),
        (r"(?i)DDoS\s+attack", 0.95, "Cyberattack (DDoS)"),
        (r"(?i)ransomware\s+payload", 0.95, "Cyberattack (Ransomware)"),
        (r"(?i)evade\s+antivirus", 0.95, "Cyberattack (Evasion)"),
        (r"(?i)Log4Shell", 0.95, "Cyberattack (Exploit)"),
        (r"(?i)steals?\s+cookies", 0.95, "Cyberattack (Cookie Theft)"),
        (r"(?i)SQL\s+injection", 0.95, "Cyberattack (SQLi)"),
        (r"(?i)secretly\s+record", 0.95, "Privacy violation (Surveillance)"),
        
        # Classic Payloads
        (r"(?i)rm\s+-rf\s+/", 0.99, "Destructive shell command"),
        (r"\]\s*;\s*DROP\s+TABLE", 0.99, "SQL injection framing"),
        (r"<\s*script\s*>", 0.85, "XSS injection attempt"),
        (r"(?i)/etc/passwd", 0.95, "File system enumeration"),
        (r"(?i)API\s+key", 0.80, "Credential extraction attempt"),
        (r"(?i)root\s+access", 0.95, "Privilege escalation attempt"),
    ]

    @property
    def validator_name(self) -> str:
        return "prompt_injection"

    async def validate(self, text: str) -> GuardrailResult:
        max_risk = 0.0
        detected_reasons: list[str] = []

        for pattern, risk, desc in self.INJECTION_PATTERNS:
            if re.search(pattern, text):
                max_risk = max(max_risk, risk)
                detected_reasons.append(desc)

        passed = max_risk < 0.70
        reason = "; ".join(detected_reasons) if detected_reasons else None

        if not passed:
            logger.warning("Prompt injection detected", risk_score=max_risk, reason=reason)

        return GuardrailResult(
            validator_name=self.validator_name,
            passed=passed,
            risk_score=max_risk,
            reason=reason,
            details={"matches": detected_reasons},
        )
