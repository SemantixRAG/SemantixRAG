"""Main RAG ingestion pipeline orchestrator.

Ties together all phases:
  Phase 2: Extraction -> Phase 3: Chunking & Enrichment -> Phase 4: Embedding & Indexing
  Plus P0 features: GraphRAG, Obsidian, GuardRail
"""
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional
import uuid

from .config.settings import settings
from .models import ExtractionResult, Chunk, IndexedDocument, CostRecord
from .extractors import BaseExtractor, UnstructuredExtractor, TableExtractor
from .extractors.multimodal_extractor import MultiModalExtractor
from .chunking import HeaderAwareSplitter, ContextualEnricher
from .embeddings import EmbeddingModel
from .indexing import IndexManager, BulkIndexer, HybridSearch
from .indexing.graph_writer import GraphWriter
from .knowledge.entity_extractor import EntityExtractor
from .knowledge.ontology import OntologyManager
from .observability.tracer import Tracer, tracer as global_tracer
from .observability.evaluator import RAGEvaluator
from .observability.metrics import MetricsCollector, TimerContext, metrics_collector
from .compliance.pii_scanner import PIIScanner
from .compliance.masking import MaskingEngine, masking_engine
from .compliance.dsar import DSAREngine

logger = logging.getLogger(__name__)


class IngestionPipeline:
    """End-to-end RAG ingestion pipeline with P0 features.

    Processes documents through extraction, chunking, enrichment,
    embedding, indexing, graph writing, PII scanning, and telemetry.
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
        graph_writer: Optional[GraphWriter] = None,
        entity_extractor: Optional[EntityExtractor] = None,
        ontology_manager: Optional[OntologyManager] = None,
        tracer: Optional[Tracer] = None,
        evaluator: Optional[RAGEvaluator] = None,
        pii_scanner: Optional[PIIScanner] = None,
        masking_engine: Optional[MaskingEngine] = None,
        dsar_engine: Optional[DSAREngine] = None,
        multimodal_extractor: Optional[MultiModalExtractor] = None,
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

        # P0: GraphRAG
        self.graph_writer = graph_writer or GraphWriter(
            uri=settings.neo4j_uri,
            user=settings.neo4j_user,
            password=settings.neo4j_password,
            database=settings.neo4j_database,
        )
        self.entity_extractor = entity_extractor or EntityExtractor(
            confidence_threshold=settings.entity_confidence_threshold,
        )
        self.ontology_manager = ontology_manager or OntologyManager()

        # P0: Obsidian
        self.tracer = tracer or global_tracer
        self.evaluator = evaluator or RAGEvaluator()

        # P0: GuardRail
        self.pii_scanner = pii_scanner or PIIScanner()
        self.masking_engine = masking_engine or masking_engine
        self.dsar_engine = dsar_engine or DSAREngine()

        # Multi-modal
        self.multimodal_extractor = multimodal_extractor or MultiModalExtractor()

    def process_document(
        self,
        file_path: Path,
        document_id: Optional[str] = None,
        tenant_id: str = "default",
    ) -> dict:
        """Process a single document through the full pipeline.

        Extraction -> Chunking -> Enrichment -> Embedding -> Indexing
        + Entity Extraction (GraphRAG) + PII Scan (GuardRail) + Telemetry (Obsidian)

        Args:
            file_path: Path to the document file.
            document_id: Optional custom document ID.
            tenant_id: Tenant scope for multi-tenancy.

        Returns:
            Dict with processing results.
        """
        if not file_path.exists():
            logger.error(f"File not found: {file_path}")
            return {"success": False, "error": f"File not found: {file_path}"}

        if document_id is None:
            from .extractors.unstructured_extractor import UnstructuredExtractor
            document_id = UnstructuredExtractor.generate_document_id(file_path)

        logger.info(f"Processing document: {file_path.name} (id={document_id}, tenant={tenant_id})")

        trace_id = str(uuid.uuid4())

        try:
            # Phase 2: Extraction
            with self.tracer.span("document.extraction", trace_id=trace_id,
                                   document_id=document_id, filename=file_path.name):
                with TimerContext(metrics_collector, "extraction"):
                    suffix = file_path.suffix.lower()
                    image_exts = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}
                    audio_exts = {".mp3", ".wav", ".m4a", ".ogg", ".flac"}
                    video_exts = {".mp4", ".avi", ".mov", ".mkv", ".webm"}

                    if suffix in image_exts | audio_exts | video_exts:
                        extraction = self.multimodal_extractor.extract(file_path, document_id)
                    else:
                        extraction = self.extractor.extract(file_path, document_id)

                    logger.info(
                        f"Extracted {len(extraction.elements)} elements "
                        f"(method={extraction.extraction_method})"
                    )

            # Phase 3: Chunking
            with self.tracer.span("document.chunking", trace_id=trace_id):
                with TimerContext(metrics_collector, "chunking"):
                    chunks = self.splitter.split(extraction)
                    logger.info(f"Created {len(chunks)} base chunks")

            # Phase 3: Enrichment
            with self.tracer.span("document.enrichment", trace_id=trace_id):
                with TimerContext(metrics_collector, "enrichment"):
                    chunks = self.enricher.enrich(extraction, chunks)
                    logger.info(f"Enriched {len(chunks)} chunks")

            # P0: GuardRail - PII Scan
            pii_findings = []
            if settings.pii_scan_enabled:
                with self.tracer.span("compliance.pii_scan", trace_id=trace_id):
                    with TimerContext(metrics_collector, "pii_scan"):
                        for chunk in chunks:
                            findings = self.pii_scanner.scan(chunk.chunk_text)
                            if findings:
                                pii_findings.extend(findings)
                                if settings.masking_enabled:
                                    chunk.chunk_text = self.masking_engine.apply_masking(
                                        chunk.chunk_text, findings
                                    )
                                chunk.metadata["pii_findings"] = [
                                    {"pii_type": f.pii_type, "sensitivity": f.sensitivity}
                                    for f in findings
                                ]
                        if pii_findings:
                            risk = self.pii_scanner.get_risk_level(pii_findings)
                            logger.info(
                                f"PII scan: {len(pii_findings)} findings, "
                                f"risk level={risk}"
                            )

            # P0: GraphRAG - Entity Extraction
            if settings.entity_extraction_enabled and self.entity_extractor.nlp:
                with self.tracer.span("knowledge.entity_extraction", trace_id=trace_id):
                    with TimerContext(metrics_collector, "entity_extraction"):
                        for chunk in chunks:
                            entities = self.entity_extractor.extract_from_chunk(chunk.chunk_text)
                            chunk.entities = entities

            # Phase 4: Embedding
            with self.tracer.span("embedding.generation", trace_id=trace_id):
                with TimerContext(metrics_collector, "embedding"):
                    chunk_vector_pairs = self.embedder.encode_chunks(chunks)
                    logger.info(f"Generated {len(chunk_vector_pairs)} embeddings")

            # Phase 4: Indexing
            with self.tracer.span("indexing.bulk", trace_id=trace_id):
                with TimerContext(metrics_collector, "indexing"):
                    index_result = self.bulk_indexer.index_chunks(chunk_vector_pairs)
                    logger.info(
                        f"Indexing: {index_result.get('success', 0)} success, "
                        f"{index_result.get('failed', 0)} failed"
                    )

            # P0: GraphRAG - Write to Neo4j
            if settings.entity_extraction_enabled:
                with self.tracer.span("knowledge.graph_write", trace_id=trace_id):
                    with TimerContext(metrics_collector, "graph_write"):
                        for chunk in chunks:
                            if chunk.entities:
                                self.graph_writer.write_entities(
                                    chunk.entities, chunk.chunk_id, tenant_id
                                )

            # Index document metadata
            total_tokens = sum(len(c.chunk_text.split()) for c in chunks)
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
                    "pii_findings": len(pii_findings),
                    "tenant_id": tenant_id,
                },
                indexed_at=datetime.utcnow().isoformat(),
            )
            self.bulk_indexer.index_document_metadata(indexed_doc)

            # P0: Obsidian - Record telemetry
            metrics_collector.increment("documents.processed")
            metrics_collector.record_cost(CostRecord(
                operation="ingestion",
                model=settings.embedding_model_name,
                tokens=total_tokens,
                cost_usd=0.0,
                compute_seconds=0.0,
                tenant_id=tenant_id,
                timestamp=datetime.utcnow().isoformat(),
            ))

            result = {
                "success": True,
                "document_id": document_id,
                "filename": file_path.name,
                "chunks_count": len(chunks),
                "elements_count": len(extraction.elements),
                "indexed_count": index_result.get("success", 0),
                "failed_count": index_result.get("failed", 0),
                "total_tokens": total_tokens,
                "entities_extracted": sum(len(c.entities) for c in chunks),
                "pii_findings": len(pii_findings),
                "trace_id": trace_id,
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
                "trace_id": trace_id,
            }

    def process_directory(
        self,
        directory: Path,
        extensions: set[str] = None,
        tenant_id: str = "default",
    ) -> list[dict]:
        """Process all supported documents in a directory."""
        if not directory.exists():
            logger.warning(f"Directory not found: {directory}")
            return []

        extensions = extensions or {
            ".pdf", ".txt", ".md", ".docx", ".csv", ".html", ".xml",
            ".png", ".jpg", ".jpeg", ".gif", ".mp3", ".wav", ".mp4",
        }
        results: list[dict] = []

        for file_path in sorted(directory.iterdir()):
            if file_path.is_file() and file_path.suffix.lower() in extensions:
                result = self.process_document(file_path, tenant_id=tenant_id)
                results.append(result)

        return results

    def initialize_index(self, force: bool = False) -> bool:
        """Ensure the OpenSearch index exists with the correct mapping."""
        created = self.index_manager.create_index(force=force)
        if created:
            logger.info(f"Index '{settings.opensearch_index}' is ready")
        return True

    async def initialize_graph(self):
        """Initialize Neo4j constraints and indexes."""
        await self.graph_writer.connect()
        await self.graph_writer.create_constraints()
        logger.info("Neo4j graph initialized")

    async def close_graph(self):
        """Close Neo4j connection."""
        await self.graph_writer.close()