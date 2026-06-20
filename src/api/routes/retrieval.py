"""Retrieval API routes."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import uuid
from ...pipeline import IngestionPipeline
from ...indexing.hybrid_search import HybridSearch
from ...indexing.graph_writer import GraphWriter
from ...config.settings import settings

router = APIRouter()
pipeline = IngestionPipeline()
hybrid_search = HybridSearch()


class RetrievalRequest(BaseModel):
    query: str
    tenant_id: str = "default"
    strategy: str = "hybrid"
    vector_top_k: int = 50
    keyword_top_k: int = 50
    graph_hops: int = 2
    rerank: bool = True
    rerank_top_k: int = 5
    filters: Optional[dict] = None
    generation: Optional[dict] = None


class RetrievalResponse(BaseModel):
    query_id: str
    query: str
    results: list[dict] = []
    retrieval_metrics: dict = {}
    generation: Optional[dict] = None
    trace_id: str = ""


@router.post("/query", response_model=RetrievalResponse)
async def query(request: RetrievalRequest):
    """Execute semantic search with hybrid retrieval."""
    query_id = str(uuid.uuid4())
    trace_id = str(uuid.uuid4())

    try:
        search_results = hybrid_search.search(
            query_text=request.query,
            top_k=request.vector_top_k,
            tenant_id=request.tenant_id,
        )

        results = []
        for i, result in enumerate(search_results[:request.rerank_top_k]):
            results.append({
                "chunk_id": result.get("chunk_id", ""),
                "document_id": result.get("document_id", ""),
                "document_title": result.get("document_title", ""),
                "header_path": result.get("header_path", ""),
                "chunk_text": result.get("chunk_text", "")[:500],
                "score": result.get("score", 0.0),
                "entities": result.get("entities", []),
            })

        return RetrievalResponse(
            query_id=query_id,
            query=request.query,
            results=results,
            retrieval_metrics={
                "total_candidates": len(search_results),
                "returned": len(results),
            },
            trace_id=trace_id,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))