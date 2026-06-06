"""OpenSearch index management — creates and configures the search index."""
import json
import logging
from typing import Optional

from config.settings import settings
from .connection import OpenSearchConnection

logger = logging.getLogger(__name__)


class IndexManager:
    """Manages OpenSearch index creation with proper mapping for hybrid search."""

    def __init__(self, connection: Optional[OpenSearchConnection] = None):
        self.connection = connection or OpenSearchConnection.get_instance()
        self.client = self.connection.client

    def create_index(self, index_name: Optional[str] = None, force: bool = False) -> bool:
        """Create the RAG document index with proper mapping.

        Creates an index with:
        - knn_vector field for dense embeddings
        - text fields for BM25 keyword search
        - keyword fields for filtering on document_id, chunk_index, etc.
        - metadata object for flexible metadata storage

        Args:
            index_name: Name of the index (default from settings).
            force: If True, delete existing index first.

        Returns:
            True if index was created, False if it already exists.
        """
        index_name = index_name or settings.opensearch_index

        # Check if index exists
        if self.client.indices.exists(index=index_name):
            if force:
                logger.warning(f"Deleting existing index '{index_name}' (force=True)")
                self.client.indices.delete(index=index_name)
            else:
                logger.info(f"Index '{index_name}' already exists")
                return False

        # Define index mapping
        mapping = {
            "settings": {
                "index": {
                    "knn": True,
                    "knn.algo_param.ef_search": 512,
                    "number_of_shards": 1,
                    "number_of_replicas": 0,
                },
                "analysis": {
                    "analyzer": {
                        "rag_analyzer": {
                            "type": "standard",
                            "stopwords": "_english_",
                        }
                    }
                },
            },
            "mappings": {
                "properties": {
                    "chunk_id": {
                        "type": "keyword",
                    },
                    "document_id": {
                        "type": "keyword",
                    },
                    "chunk_index": {
                        "type": "integer",
                    },
                    "chunk_text": {
                        "type": "text",
                        "analyzer": "rag_analyzer",
                        "fields": {
                            "keyword": {
                                "type": "keyword",
                            },
                        },
                    },
                    "chunk_vector": {
                        "type": "knn_vector",
                        "dimension": settings.embedding_dimension,
                        "method": {
                            "name": "hnsw",
                            "space_type": "cosinesimil",
                            "engine": "lucene",
                            "parameters": {
                                "ef_construction": 512,
                                "m": 16,
                            },
                        },
                    },
                    "document_title": {
                        "type": "text",
                        "analyzer": "rag_analyzer",
                    },
                    "document_summary": {
                        "type": "text",
                        "analyzer": "rag_analyzer",
                    },
                    "header_path": {
                        "type": "text",
                        "analyzer": "rag_analyzer",
                    },
                    "element_types": {
                        "type": "keyword",
                    },
                    "metadata": {
                        "type": "object",
                        "dynamic": True,
                    },
                },
            },
        }

        # Create the index
        self.client.indices.create(index=index_name, body=mapping)
        logger.info(
            f"Created index '{index_name}' "
            f"(dimension={settings.embedding_dimension}, "
            f"knn=True)"
        )
        return True

    def delete_index(self, index_name: Optional[str] = None) -> bool:
        """Delete an index.

        Args:
            index_name: Name of the index to delete.

        Returns:
            True if deleted, False if it didn't exist.
        """
        index_name = index_name or settings.opensearch_index
        if not self.client.indices.exists(index=index_name):
            return False
        self.client.indices.delete(index=index_name)
        logger.info(f"Deleted index '{index_name}'")
        return True

    def index_exists(self, index_name: Optional[str] = None) -> bool:
        """Check if the index exists."""
        index_name = index_name or settings.opensearch_index
        return self.client.indices.exists(index=index_name)

    def get_index_stats(self, index_name: Optional[str] = None) -> dict:
        """Get statistics about the index."""
        index_name = index_name or settings.opensearch_index
        if not self.index_exists(index_name):
            return {"error": f"Index '{index_name}' does not exist"}

        stats = self.client.indices.stats(index=index_name)
        index_stats = stats.get("indices", {}).get(index_name, {}).get("total", {})

        return {
            "index": index_name,
            "doc_count": index_stats.get("docs", {}).get("count", 0),
            "size_bytes": index_stats.get("store", {}).get("size_in_bytes", 0),
        }