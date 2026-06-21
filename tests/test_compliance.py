"""Tests for GuardRail PII compliance."""
import pytest
from semantixrag.compliance.pii_scanner import PIIScanner
from semantixrag.compliance.masking import MaskingEngine
from semantixrag.compliance.dsar import DSAREngine


@pytest.fixture
def scanner():
    return PIIScanner()


@pytest.fixture
def masking_engine():
    return MaskingEngine()


@pytest.mark.asyncio
async def test_email_detection(scanner):
    text = "Contact John at john.doe@example.com for details."
    findings = await scanner.scan(text)
    assert len(findings) >= 1
    assert any(f.pii_type in ("EMAIL_ADDRESS", "EMAIL") for f in findings)


@pytest.mark.asyncio
async def test_masking(scanner):
    text = "SSN: 123-45-6789"
    findings = await scanner.scan(text)
    masked = await scanner.mask_text(text, findings)
    assert "123-45-6789" not in masked


@pytest.mark.asyncio
async def test_empty_text(scanner):
    findings = await scanner.scan("")
    assert findings == []


@pytest.mark.asyncio
async def test_no_pii(scanner):
    findings = await scanner.scan("The sky is blue and the grass is green.")
    assert findings == []


def test_risk_level(scanner):
    assert scanner.get_risk_level([]) == "low"

    medium_findings = [
        type('obj', (object,), {'pii_type': 'EMAIL_ADDRESS'})(),
    ]
    assert scanner.get_risk_level(medium_findings) == "medium"

    high_findings = [
        type('obj', (object,), {'pii_type': 'SSN'})(),
    ]
    assert scanner.get_risk_level(high_findings) == "high"


def test_summary(scanner):
    findings = [
        type('obj', (object,), {'pii_type': 'EMAIL_ADDRESS' })(),
        type('obj', (object,), {'pii_type': 'SSN'})(),
    ]
    summary = scanner.get_summary(findings)
    assert summary["total_findings"] == 2
    assert summary["risk_score"] == "high"


class TestMaskingEngine:
    def test_mask_email(self, masking_engine):
        from src.models import PIIFinding
        findings = [
            PIIFinding(pii_type="EMAIL_ADDRESS", start=10, end=25, confidence=0.95)
        ]
        masked = masking_engine.apply_masking("Contact: test@example.com", findings)
        assert "[EMAIL]" in masked
        assert "test@example" not in masked

    def test_no_findings(self, masking_engine):
        masked = masking_engine.apply_masking("Hello world", [])
        assert masked == "Hello world"

    def test_mask_rule_override(self, masking_engine):
        masking_engine.add_mask_rule("SSN", "[REDACTED_SSN]")
        assert masking_engine.get_mask_token("SSN") == "[REDACTED_SSN]"

    def test_redaction_plan(self, masking_engine):
        from src.models import PIIFinding
        findings = [
            PIIFinding(pii_type="EMAIL_ADDRESS", sensitivity="low"),
            PIIFinding(pii_type="SSN", sensitivity="high"),
        ]
        plan = masking_engine.create_redaction_plan(findings, "medium")
        assert len(plan) == 1
        assert plan[0].pii_type == "SSN"


class TestDSAREngine:
    @pytest.mark.asyncio
    async def test_dsar_execution(self):
        engine = DSAREngine()
        result = await engine.execute_dsar(
            subject_id="user@example.com",
            action="access",
            tenant_id="default",
            requested_by="admin",
        )
        assert result.dsar_id is not None
        assert result.status in ("processing", "completed", "failed")

    @pytest.mark.asyncio
    async def test_dsar_delete_requires_reason(self):
        engine = DSAREngine()
        with pytest.raises(ValueError):
            await engine.execute_dsar(
                subject_id="user@example.com",
                action="delete",
                tenant_id="default",
                requested_by="admin",
            )

    def test_dsar_status(self):
        engine = DSAREngine()
        status = engine.get_dsar_status("nonexistent")
        assert status is None