"""PII detection using Microsoft Presidio and fine-tuned classifier."""
import logging
from typing import Optional, List
from ..models import PIIFinding

logger = logging.getLogger(__name__)

try:
    from presidio_analyzer import AnalyzerEngine, RecognizerRegistry
    from presidio_analyzer.nlp_engine import NlpEngineProvider
    from presidio_anonymizer import AnonymizerEngine
    PRESIDIO_AVAILABLE = True
except ImportError:
    PRESIDIO_AVAILABLE = False
    logger.warning("Presidio not installed. PII scanning will use fallback regex patterns.")


# Fallback PII patterns when Presidio is not available
FALLBACK_PII_PATTERNS = {
    "EMAIL_ADDRESS": r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
    "PHONE_NUMBER": r'(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',
    "SSN": r'\b\d{3}[-]\d{2}[-]\d{4}\b',
    "CREDIT_CARD": r'\b\d{4}[-.\s]?\d{4}[-.\s]?\d{4}[-.\s]?\d{4}\b',
    "IP_ADDRESS": r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b',
    "DATE": r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b',
}


class PIIScanner:
    """Scan text for PII using Presidio + fallback patterns."""

    def __init__(
        self,
        use_presidio: bool = True,
        supported_languages: Optional[list[str]] = None,
    ):
        self.supported_languages = supported_languages or ["en"]
        self.analyzer = None
        self.anonymizer = None

        if use_presidio and PRESIDIO_AVAILABLE:
            self._init_presidio()
        elif use_presidio and not PRESIDIO_AVAILABLE:
            logger.info("Falling back to regex-based PII detection")

    def _init_presidio(self):
        """Initialize Presidio analyzer."""
        try:
            provider = NlpEngineProvider({
                "nlp_engine_name": "spacy",
                "models": [{"lang_code": "en", "model_name": "en_core_web_lg"}],
            })
            nlp_engine = provider.create_engine()

            registry = RecognizerRegistry()
            registry.load_predefined_recognizers(nlp_engine=nlp_engine)

            self.analyzer = AnalyzerEngine(
                nlp_engine=nlp_engine,
                registry=registry,
                supported_languages=self.supported_languages,
            )
            self.anonymizer = AnonymizerEngine()
            logger.info("Presidio initialized successfully")
        except Exception as e:
            logger.warning(f"Failed to initialize Presidio: {e}. Using fallback regex.")
            self.analyzer = None
            self.anonymizer = None

    async def scan(self, text: str, language: str = "en") -> List[PIIFinding]:
        """Scan text for PII."""
        if not text:
            return []

        if self.analyzer:
            return await self._scan_presidio(text, language)
        else:
            return self._scan_fallback(text)

    async def _scan_presidio(self, text: str, language: str) -> List[PIIFinding]:
        """Scan using Presidio."""
        try:
            results = self.analyzer.analyze(
                text=text,
                language=language,
                entities=None,
                score_threshold=0.5,
            )
            findings = []
            for result in results:
                finding = PIIFinding(
                    pii_type=result.entity_type,
                    start=result.start,
                    end=result.end,
                    confidence=result.score,
                    context=text[max(0, result.start - 30):result.end + 30],
                    masked_text=f"[{result.entity_type}]",
                )
                findings.append(finding)
            return findings
        except Exception as e:
            logger.error(f"Presidio scan failed: {e}")
            return []

    def _scan_fallback(self, text: str) -> List[PIIFinding]:
        """Scan using regex fallback patterns."""
        import re
        findings = []
        for pii_type, pattern in FALLBACK_PII_PATTERNS.items():
            try:
                for match in re.finditer(pattern, text):
                    finding = PIIFinding(
                        pii_type=pii_type,
                        start=match.start(),
                        end=match.end(),
                        confidence=0.9,
                        context=text[max(0, match.start() - 30):match.end() + 30],
                        masked_text=f"[{pii_type}]",
                    )
                    findings.append(finding)
            except re.error as e:
                logger.warning(f"Regex error for {pii_type}: {e}")
        return findings

    async def mask_text(
        self,
        text: str,
        findings: List[PIIFinding],
    ) -> str:
        """Mask PII in text."""
        if not findings:
            return text

        sorted_findings = sorted(findings, key=lambda f: f.start, reverse=True)
        masked = text
        for finding in sorted_findings:
            masked = masked[:finding.start] + finding.masked_text + masked[finding.end:]
        return masked

    def get_risk_level(self, findings: List[PIIFinding]) -> str:
        """Determine risk level based on PII types found."""
        if not findings:
            return "low"

        high_risk_types = {"SSN", "CREDIT_CARD", "BANK_ACCOUNT", "MEDICAL_LICENSE"}
        medium_risk_types = {"EMAIL", "PHONE_NUMBER", "ADDRESS", "EMAIL_ADDRESS"}

        types = {f.pii_type for f in findings}
        if types & high_risk_types:
            return "high"
        elif types & medium_risk_types:
            return "medium"
        else:
            return "low"

    def get_summary(self, findings: List[PIIFinding]) -> dict:
        """Get summary of PII findings."""
        by_type: dict[str, int] = {}
        for f in findings:
            by_type[f.pii_type] = by_type.get(f.pii_type, 0) + 1
        return {
            "total_findings": len(findings),
            "by_type": by_type,
            "risk_score": self.get_risk_level(findings),
        }