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

    # Embedding Model
    embedding_model_name: str = "BAAI/bge-m3"
    embedding_dimension: int = 1024
    embedding_batch_size: int = 32
    embedding_device: Optional[str] = None  # auto-detect

    # Chunking
    chunk_max_tokens: int = 512
    chunk_overlap_tokens: int = 64

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