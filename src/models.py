"""Pydantic data models for the RAG ingestion pipeline."""
from pydantic import BaseModel, Field
from typing import Optional, Any
from enum import Enum
from datetime import datetime


class ElementType(str, Enum):
    HEADER = "Header"
    PARAGRAPH = "Paragraph"
    LIST_ITEM = "ListItem"
    TABLE = "Table"
    FIGURE = "Figure"
    FOOTER = "Footer"
    TITLE = "Title"
    IMAGE = "Image"
    AUDIO = "Audio"
    VIDEO = "Video"


class ExtractedElement(BaseModel):
    """A single structural element extracted from a document."""
    element_type: ElementType
    text: str
    markdown: Optional[str] = None
    bounding_box: Optional[dict[str, float]] = None
    page_number: Optional[int] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ExtractionResult(BaseModel):
    """Standardized output from the extraction phase."""
    document_id: str
    filename: str
    title: Optional[str] = None
    elements: list[ExtractedElement] = Field(default_factory=list)
    raw_text: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
    extraction_method: str = "unstructured"


class Chunk(BaseModel):
    """A single chunk ready for embedding and indexing."""
    chunk_id: str
    document_id: str
    chunk_index: int
    chunk_text: str
    document_title: Optional[str] = None
    document_summary: Optional[str] = None
    header_path: Optional[str] = None
    element_types: list[str] = Field(default_factory=list)
    entities: list[dict] = Field(default_factory=list)
    modality: str = "text"
    metadata: dict[str, Any] = Field(default_factory=dict)


class IndexedDocument(BaseModel):
    """Document metadata stored in OpenSearch."""
    document_id: str
    filename: str
    title: Optional[str] = None
    total_chunks: int = 0
    total_tokens: int = 0
    summary: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    indexed_at: str = ""


class PIIFinding(BaseModel):
    """A single PII finding from scanning."""
    pii_type: str
    start: int
    end: int
    confidence: float
    context: str = ""
    masked_text: str = "[PII]"
    sensitivity: str = "medium"
    recommended_action: str = "mask"


class DSARResult(BaseModel):
    """GDPR data subject access request result."""
    dsar_id: str
    status: str = "processing"
    subject_id: str
    action: str  # access | delete | export
    affected_documents: int = 0
    affected_chunks: int = 0
    affected_embeddings: int = 0
    affected_memories: int = 0
    estimated_completion: Optional[str] = None
    tenant_id: str = "default"


class TraceSpan(BaseModel):
    """A trace span for observability."""
    trace_id: str
    span_id: str
    operation: str
    parent_span_id: Optional[str] = None
    start_time: float = 0.0
    end_time: Optional[float] = None
    duration_ms: int = 0
    status: str = "success"
    metadata: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)
    tenant_id: str = "default"


class CostRecord(BaseModel):
    """Cost tracking record."""
    operation: str
    model: str
    tokens: int = 0
    cost_usd: float = 0.0
    compute_seconds: float = 0.0
    tenant_id: str = "default"
    timestamp: str = ""


class SearchResult(BaseModel):
    """Single search result from retrieval."""
    chunk_id: str
    document_id: str
    document_title: Optional[str] = None
    header_path: Optional[str] = None
    chunk_text: str
    score: float = 0.0
    vector_score: Optional[float] = None
    keyword_score: Optional[float] = None
    graph_score: Optional[float] = None
    entities: list[str] = Field(default_factory=list)
    modality: str = "text"
    metadata: dict[str, Any] = Field(default_factory=dict)
    citations: list[dict] = Field(default_factory=list)


class QueryResult(BaseModel):
    """Complete query response."""
    query_id: str
    query: str
    results: list[SearchResult] = Field(default_factory=list)
    retrieval_metrics: dict[str, Any] = Field(default_factory=dict)
    generation: Optional[dict[str, Any]] = None
    trace_id: str = ""
    confidence: float = 0.0