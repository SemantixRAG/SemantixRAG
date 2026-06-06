"""Pydantic data models for the RAG ingestion pipeline."""
from pydantic import BaseModel, Field
from typing import Optional, Any
from enum import Enum


class ElementType(str, Enum):
    HEADER = "Header"
    PARAGRAPH = "Paragraph"
    LIST_ITEM = "ListItem"
    TABLE = "Table"
    FIGURE = "Figure"
    FOOTER = "Footer"
    TITLE = "Title"


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