"""Main RAG ingestion pipeline orchestrator.

Ties together all phases:
  Phase 2: Extraction -> Phase 3: Chunking & Enrichment -> Phase 4: Embedding & Indexing
"""
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional
import uuid

from config.settings import settings
from .models import ExtractionResult, Chunk, IndexedDocument
from .extractors import BaseExtractor, UnstructuredExtractor, TableExtractor
from .chunking import HeaderAwareSplitter, ContextualEnricher
from .embeddings import EmbeddingModel
from .indexing import IndexManager, BulkIndexer, HybridSearch

logger = logging.getLogger(__name__)


class IngestionPipeline:
    """End-to-end RAG ingestion pipeline.

    Processes documents through extraction, chunking, enrichment,
    embedding, and indexing into OpenSearch.
    """

    def __init__(
        self,
        extractor: Optional[BaseExtractor] = None,
        splitter: Optional[HeaderAwareSplitter] = None,
        enricher: Optional[ContextualEnricher] = None,
        embedder: Optional[EmbeddingModel] = None,
        index_manager: Optional[IndexManager] = None,
        bulk_indexer: Optional[BulkIndexer] = None,
        hybrid_search: Optional[HybridSearch] = None,
        use_mock_summaries: bool = False,
    ):
        self.extractor = extractor or UnstructuredExtractor()
        self.splitter = splitter or HeaderAwareSplitter(
            max_tokens=settings.chunk_max_tokens,
            overlap_tokens=settings.chunk_overlap_tokens,
        )
        self.enricher = enricher or ContextualEnricher(
            use_mock=use_mock_summaries,
        )
        self.embedder = embedder or EmbeddingModel(
            model_name=settings.embedding_model_name,
            batch_size=settings.embedding_batch_size,
        )
        self.index_manager = index_manager or IndexManager()
        self.bulk_indexer = bulk_indexer or BulkIndexer()
        self.hybrid_search = hybrid_search or HybridSearch()
        self.table_extractor = TableExtractor(use_mock=True)

    def process_document(self, file_path: Path, document_id: Optional[str] = None) -> dict:
        """Process a single document through the full pipeline.

        Extraction -> Chunking -> Enrichment -> Embedding -> Indexing

        Args:
            file_path: Path to the document file.
            document_id: Optional custom document ID (auto-generated if not provided).

        Returns:
            Dict with processing results: document_id, chunks_count, success, etc.
        """
        if not file_path.exists():
            logger.error(f"File not found: {file_path}")
            return {"success": False, "error": f"File not found: {file_path}"}

        if document_id is None:
            document_id = UnstructuredExtractor.generate_document_id(file_path)

        logger.info(f"Processing document: {file_path.name} (id={document_id})")

        try:
            # Phase 2: Extraction
            logger.info(f"[Phase 2] Extracting content from '{file_path.name}'...")
            extraction = self.extractor.extract(file_path, document_id)
            logger.info(
                f"Extracted {len(extraction.elements)} elements "
                f"(method={extraction.extraction_method})"
            )

            # Phase 3: Chunking
            logger.info(f"[Phase 3] Chunking {len(extraction.elements)} elements...")
            chunks = self.splitter.split(extraction)
            logger.info(f"Created {len(chunks)} base chunks")

            # Phase 3: Enrichment
            logger.info(f"[Phase 3] Enriching {len(chunks)} chunks with context...")
            chunks = self.enricher.enrich(extraction, chunks)
            logger.info(f"Enriched {len(chunks)} chunks")

            # Phase 4: Embedding
            logger.info(f"[Phase 4] Generating embeddings for {len(chunks)} chunks...")
            chunk_vector_pairs = self.embedder.encode_chunks(chunks)
            logger.info(f"Generated {len(chunk_vector_pairs)} embeddings")

            # Phase 4: Indexing
            logger.info(f"[Phase 4] Indexing {len(chunk_vector_pairs)} chunks into OpenSearch...")
            index_result = self.bulk_indexer.index_chunks(chunk_vector_pairs)
            logger.info(
                f"Indexing complete: {index_result.get('success', 0)} success, "
                f"{index_result.get('failed', 0)} failed"
            )

            # Index document metadata
            total_tokens = sum(
                len(c.chunk_text.split()) for c in chunks
            )
            indexed_doc = IndexedDocument(
                document_id=document_id,
                filename=file_path.name,
                title=extraction.title,
                total_chunks=len(chunks),
                total_tokens=total_tokens,
                metadata={
                    "file_size": file_path.stat().st_size,
                    "extraction_method": extraction.extraction_method,
                    "num_elements": len(extraction.elements),
                },
                indexed_at=datetime.utcnow().isoformat(),
            )
            self.bulk_indexer.index_document_metadata(indexed_doc)

            result = {
                "success": True,
                "document_id": document_id,
                "filename": file_path.name,
                "chunks_count": len(chunks),
                "elements_count": len(extraction.elements),
                "indexed_count": index_result.get("success", 0),
                "failed_count": index_result.get("failed", 0),
                "total_tokens": total_tokens,
            }

            logger.info(f"Successfully processed '{file_path.name}': {result}")
            return result

        except Exception as e:
            logger.exception(f"Failed to process '{file_path.name}': {e}")
            return {
                "success": False,
                "document_id": document_id,
                "filename": file_path.name,
                "error": str(e),
            }

    def process_directory(
        self,
        directory: Path,
        extensions: set[str] = None,
    ) -> list[dict]:
        """Process all supported documents in a directory.

        Args:
            directory: Path to the directory containing documents.
            extensions: Set of file extensions to process.

        Returns:
            List of per-document processing results.
        """
        if not directory.exists():
            logger.warning(f"Directory not found: {directory}")
            return []

        extensions = extensions or {".pdf", ".txt", ".md", ".docx", ".csv", ".html", ".xml"}
        results: list[dict] = []

        for file_path in sorted(directory.iterdir()):
            if file_path.is_file() and file_path.suffix.lower() in extensions:
                result = self.process_document(file_path)
                results.append(result)

        return results

    def initialize_index(self, force: bool = False) -> bool:
        """Ensure the OpenSearch index exists with the correct mapping.

        Args:
            force: If True, delete and recreate the index.

        Returns:
            True if the index is ready.
        """
        created = self.index_manager.create_index(force=force)
        if created:
            logger.info(f"Index '{settings.opensearch_index}' is ready")
        return True