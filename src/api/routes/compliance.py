"""Compliance API routes (GuardRail)."""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
import uuid
from datetime import datetime
from ...compliance.pii_scanner import PIIScanner
from ...compliance.masking import masking_engine
from ...compliance.dsar import DSAREngine
from ...config.settings import settings

router = APIRouter()
pii_scanner = PIIScanner()
dsar_engine = DSAREngine()


class PIIscanRequest(BaseModel):
    document_id: Optional[str] = None
    text: Optional[str] = None
    tenant_id: str = "default"
    scan_depth: str = "standard"


class DSARRequest(BaseModel):
    subject_id: str
    action: str
    tenant_id: str = "default"
    requested_by: str
    reason: Optional[str] = None


@router.post("/compliance/pii/scan")
async def scan_pii(request: PIIscanRequest):
    """Scan text or document for PII."""
    if not request.text:
        raise HTTPException(status_code=400, detail="No text provided for scanning")

    findings = await pii_scanner.scan(request.text)
    summary = pii_scanner.get_summary(findings)

    return {
        "scan_id": str(uuid.uuid4()),
        "pii_findings": [
            {
                "pii_type": f.pii_type,
                "sensitivity": f.sensitivity,
                "confidence": f.confidence,
                "location": {"start": f.start, "end": f.end},
                "context": f.context[:100],
                "recommended_action": f.recommended_action,
                "masked_text": f.masked_text,
            }
            for f in findings
        ],
        "summary": summary,
    }


@router.post("/compliance/dsar")
async def execute_dsar(request: DSARRequest):
    """Execute GDPR data subject access/deletion request."""
    if request.action == "delete" and not request.reason:
        raise HTTPException(
            status_code=400,
            detail="Reason is required for delete actions",
        )

    result = await dsar_engine.execute_dsar(
        subject_id=request.subject_id,
        action=request.action,
        tenant_id=request.tenant_id,
        requested_by=request.requested_by,
        reason=request.reason,
    )

    return {
        "dsar_id": result.dsar_id,
        "status": result.status,
        "subject_id": result.subject_id,
        "action": result.action,
        "affected_records": {
            "documents": result.affected_documents,
            "chunks": result.affected_chunks,
            "embeddings": result.affected_embeddings,
            "agent_memories": result.affected_memories,
        },
        "estimated_completion": result.estimated_completion,
    }


@router.get("/compliance/dsar/{dsar_id}")
async def get_dsar_status(dsar_id: str):
    """Get DSAR request status."""
    result = dsar_engine.get_dsar_status(dsar_id)
    if not result:
        raise HTTPException(status_code=404, detail="DSAR request not found")
    return {
        "dsar_id": result.dsar_id,
        "status": result.status,
        "subject_id": result.subject_id,
        "action": result.action,
        "affected_records": {
            "documents": result.affected_documents,
            "chunks": result.affected_chunks,
            "embeddings": result.affected_embeddings,
            "agent_memories": result.affected_memories,
        },
    }