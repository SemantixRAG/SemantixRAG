"""Observability API routes (Obsidian)."""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from datetime import datetime
from ...observability.metrics import metrics_collector

router = APIRouter()


@router.post("/observability/traces")
async def ingest_traces(traces: list[dict]):
    """Ingest telemetry traces."""
    accepted = len(traces)
    metrics_collector.increment("traces.ingested", accepted)
    return {"accepted": accepted, "failed": 0}


@router.get("/observability/metrics")
async def get_metrics(
    start_time: Optional[str] = Query(None),
    end_time: Optional[str] = Query(None),
    granularity: str = Query("5m"),
):
    """Query pipeline metrics."""
    return metrics_collector.snapshot()


@router.get("/observability/evaluation")
async def get_evaluation(
    start_time: Optional[str] = Query(None),
    end_time: Optional[str] = Query(None),
    evaluation_id: Optional[str] = Query(None),
    query_id: Optional[str] = Query(None),
):
    """Query RAG quality evaluation metrics."""
    return {
        "evaluations": [],
        "message": "Evaluation requires LLM client for full functionality",
    }