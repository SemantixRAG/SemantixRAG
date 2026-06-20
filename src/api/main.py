"""FastAPI application entry point for SemantixRAG Platform."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routes import ingestion, retrieval, admin, observability, compliance

app = FastAPI(
    title="SemantixRAG Platform",
    description="AI-native RAG ingestion, retrieval, and governance platform",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ingestion.router, prefix="/v1", tags=["ingestion"])
app.include_router(retrieval.router, prefix="/v1", tags=["retrieval"])
app.include_router(admin.router, prefix="/v1", tags=["admin"])
app.include_router(observability.router, prefix="/v1", tags=["observability"])
app.include_router(compliance.router, prefix="/v1", tags=["compliance"])


@app.get("/health")
async def health_check():
    return {"status": "ok", "version": "2.0.0"}