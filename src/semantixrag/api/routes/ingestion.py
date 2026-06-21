"""Ingestion API routes."""
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from pathlib import Path
import uuid
from datetime import datetime
from typing import Optional
from ...pipeline import IngestionPipeline
from ...config.settings import settings

router = APIRouter()
pipeline = IngestionPipeline()


@router.post("/ingest")
async def ingest_document(
    file: UploadFile = File(...),
    tenant_id: str = Form("default"),
    enrich: bool = Form(True),
    enable_entity_extraction: bool = Form(True),
    enable_pii_scan: bool = Form(True),
    enable_summarization: bool = Form(True),
):
    """Upload and process a single document."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    # Save uploaded file temporarily
    temp_dir = Path(settings.watch_directory) / "uploads"
    temp_dir.mkdir(parents=True, exist_ok=True)
    temp_path = temp_dir / f"{uuid.uuid4()}_{file.filename}"

    try:
        content = await file.read()
        temp_path.write_bytes(content)

        document_id = str(uuid.uuid4())
        result = pipeline.process_document(
            temp_path,
            document_id=document_id,
            tenant_id=tenant_id,
        )

        if not result.get("success"):
            raise HTTPException(
                status_code=500,
                detail=result.get("error", "Processing failed"),
            )

        return {
            "document_id": result["document_id"],
            "filename": result["filename"],
            "status": "completed",
            "chunks_created": result["chunks_count"],
            "entities_extracted": result.get("entities_extracted", 0),
            "pii_findings": result.get("pii_findings", 0),
            "indexed_at": datetime.utcnow().isoformat(),
            "trace_id": result.get("trace_id", ""),
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if temp_path.exists():
            temp_path.unlink()


@router.get("/ingest/{document_id}/status")
async def get_ingest_status(document_id: str):
    """Check ingestion status for a document."""
    return {
        "document_id": document_id,
        "status": "completed",
        "message": "Status tracking requires OpenSearch connection",
    }