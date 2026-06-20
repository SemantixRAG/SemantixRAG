"""Application settings using pydantic-settings."""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Global configuration for the RAG ingestion pipeline."""

    # OpenSearch
    opensearch_host: str = "localhost"
    opensearch_port: int = 9200
    opensearch_index: str = "rag_documents"
    opensearch_bulk_size: int = 100
    opensearch_max_retries: int = 3
    opensearch_timeout: int = 60

    # Neo4j (GraphRAG)
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "password"
    neo4j_database: str = "rag"

    # OPA (Policy Engine)
    opa_url: str = "http://localhost:8181"

    # Embedding Model
    embedding_model_name: str = "BAAI/bge-m3"
    embedding_dimension: int = 1024
    embedding_batch_size: int = 32
    embedding_device: Optional[str] = None

    # Chunking
    chunk_max_tokens: int = 512
    chunk_overlap_tokens: int = 64

    # Observability (Obsidian)
    observability_enabled: bool = True
    observability_index: str = "rag_observability"
    observability_sample_rate: float = 1.0

    # Compliance (GuardRail)
    pii_scan_enabled: bool = True
    pii_scan_depth: str = "standard"
    masking_enabled: bool = True
    audit_log_enabled: bool = True

    # Knowledge Graph
    entity_extraction_enabled: bool = True
    entity_confidence_threshold: float = 0.8
    ontology_auto_discovery: bool = True

    # Cost Sentinel
    cost_tracking_enabled: bool = True
    cost_alert_threshold_usd: float = 100.0

    # Multi-modal
    multimodal_enabled: bool = False
    vlm_model_name: str = "llava-hf/llava-1.5-7b-hf"
    whisper_model_name: str = "openai/whisper-base"

    # Monitoring / Watching
    watch_directory: str = "./documents"
    watch_recursive: bool = True
    poll_interval_seconds: int = 10

    # Logging
    log_level: str = "INFO"
    log_file: str = "rag_ingestion.log"

    class Config:
        env_file = ".env"
        env_prefix = "RAG_"
        case_sensitive = False


settings = Settings()