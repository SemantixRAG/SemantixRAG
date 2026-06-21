"""Admin API routes (AdminCopilot)."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from ...pipeline import IngestionPipeline
from ...observability.metrics import metrics_collector

router = APIRouter()
pipeline = IngestionPipeline()


class AdminQueryRequest(BaseModel):
    query: str
    user_id: str = "anonymous"
    user_role: str = "viewer"
    tenant_id: str = "default"
    confirm_destructive: bool = True


class AdminQueryResponse(BaseModel):
    action_taken: str = "query_executed"
    action_type: str = "read"
    result: dict = {}
    requires_confirmation: bool = False
    summary: str = ""


@router.post("/admin/query", response_model=AdminQueryResponse)
async def admin_query(request: AdminQueryRequest):
    """Natural-language platform administration."""
    query = request.query.lower()

    try:
        if "document" in query and "count" in query:
            return AdminQueryResponse(
                summary="Document count query processed",
                result={"message": "Use GET /metrics for document counts"},
            )

        elif "pii" in query and ("scan" in query or "find" in query):
            return AdminQueryResponse(
                action_type="compliance",
                summary="PII scan initiated",
                result={"status": "PII scanning enabled by default on ingestion"},
            )

        elif "health" in query or "status" in query:
            return AdminQueryResponse(
                action_type="read",
                summary="Platform health check",
                result=metrics_collector.snapshot(),
            )

        elif "schema" in query or "ontology" in query:
            return AdminQueryResponse(
                action_type="read",
                summary="Knowledge graph schema",
                result=pipeline.ontology_manager.to_schema(),
            )

        else:
            return AdminQueryResponse(
                summary=f"Processed: {request.query}",
                result={"message": f"Query '{request.query}' received. Use specific commands: 'document count', 'PII scan', 'health', 'schema'"},
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))