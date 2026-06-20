"""Dynamic PII masking and redaction (GuardRail)."""
import logging
from typing import Optional, List
from ..models import PIIFinding

logger = logging.getLogger(__name__)


class MaskingEngine:
    """Apply dynamic masking rules to text containing PII."""

    def __init__(self):
        self._mask_rules: dict[str, str] = {
            "EMAIL_ADDRESS": "[EMAIL]",
            "EMAIL": "[EMAIL]",
            "SSN": "[SSN]",
            "CREDIT_CARD": "[CREDIT_CARD]",
            "PHONE_NUMBER": "[PHONE]",
            "BANK_ACCOUNT": "[BANK_ACCOUNT]",
            "MEDICAL_LICENSE": "[MEDICAL_LICENSE]",
            "IP_ADDRESS": "[IP]",
            "PERSON": "[PERSON]",
            "DEFAULT": "[PII]",
        }

    def get_mask_token(self, pii_type: str) -> str:
        """Get the mask token for a given PII type."""
        return self._mask_rules.get(pii_type.upper(), self._mask_rules["DEFAULT"])

    def add_mask_rule(self, pii_type: str, mask_token: str):
        """Add or override a masking rule."""
        self._mask_rules[pii_type.upper()] = mask_token

    def apply_masking(
        self,
        text: str,
        findings: List[PIIFinding],
        mask_strategy: str = "type_specific",
    ) -> str:
        """Apply masking to text based on findings.

        Args:
            text: Original text.
            findings: List of PII findings.
            mask_strategy: 'type_specific' (EMAIL->[EMAIL]), 'uniform' (all->[PII]).

        Returns:
            Masked text.
        """
        if not findings:
            return text

        sorted_findings = sorted(findings, key=lambda f: f.start, reverse=True)
        masked = text

        for finding in sorted_findings:
            if mask_strategy == "type_specific":
                token = self.get_mask_token(finding.pii_type)
            else:
                token = self._mask_rules["DEFAULT"]

            masked = masked[:finding.start] + token + masked[finding.end:]

        return masked

    def create_redaction_plan(
        self,
        findings: List[PIIFinding],
        sensitivity_threshold: str = "medium",
    ) -> List[PIIFinding]:
        """Create a redaction plan based on sensitivity levels.

        Args:
            findings: PII findings to evaluate.
            sensitivity_threshold: Minimum sensitivity to redact ('low', 'medium', 'high').

        Returns:
            List of findings to redact.
        """
        levels = {"low": 0, "medium": 1, "high": 2}
        threshold = levels.get(sensitivity_threshold, 1)

        plan = []
        for finding in findings:
            finding_sensitivity = levels.get(finding.sensitivity, 0)
            if finding_sensitivity >= threshold:
                plan.append(finding)

        return plan


# Global masking engine
masking_engine = MaskingEngine()