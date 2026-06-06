"""High-throughput OpenSearch bulk indexer using the _bulk API."""
import logging
from typing import Iterator
from opensearchpy.helpers import bulk, streaming_bulk

from config.settings import settings
from .connection import OpenSearchConnection
from ..models import Chunk, IndexedDocument

logger = logging.getLogger(__name__)


class BulkIndexer:
    """Indexes chunks and their embeddings into OpenSearch using the _bulk API."""

    def __init__(self, connection: OpenSearchConnection = None):
        self.connection = connection or OpenSearchConnection.get_instance()
        self.client = self.connection.client

    def index_chunks(
        self,
        chunk_vector_pairs: list[tuple[Chunk, list[float]]],
        index_name: str = None,
    ) -> dict:
        """Bulk index chunks with their embedding vectors.

        Args:
            chunk_vector_pairs: List of (Chunk, embedding_vector) tuples.
            index_name: OpenSearch index name (default from settings).

        Returns:
            Dict with 'success' count, 'failed' count, and 'errors'.
        """
        index_name = index_name or settings.opensearch_index
        if not chunk_vector_pairs:
            return {"success": 0, "failed": 0, "errors": []}

        success = 0
        failed = 0
        errors = []

        for ok, result in streaming_bulk(
            self.client,
            self._generate_actions(chunk_vector_pairs, index_name),
            chunk_size=settings.opensearch_bulk_size,
            max_retries=settings.opensearch_max_retries,
            raise_on_error=False,
        ):
            if ok:
                success += 1
            else:
                failed += 1
                errors.append(result)

        logger.info(
            f"Bulk indexed {success} chunks into '{index_name}' "
            f"({failed} failed)"
        )
        return {"success": success, "failed": failed, "errors": errors}

    def index_document_metadata(
        self,
        indexed_doc: IndexedDocument,
        index_name: str = None,
    ) -> bool:
        """Store document-level metadata in a separate metadata index.

        Args:
            indexed_doc: Document metadata object.
            index_name: Name of the metadata index.

        Returns:
            True if indexed successfully.
        """
        index_name = f"{index_name or settings.opensearch_index}_metadata"

        doc_body = indexed_doc.model_dump(exclude_none=True)

        response = self.client.index(
            index=index_name,
            id=indexed_doc.document_id,
            body=doc_body,
            refresh=True,
        )
        logger.info(
            f"Indexed document metadata for '{indexed_doc.document_id}' "
            f"into '{index_name}' (result={response['result']})"
        )
        return response["result"] in ("created", "updated")

    def delete_document_chunks(
        self,
        document_id: str,
        index_name: str = None,
    ) -> dict:
        """Delete all chunks for a given document (for incremental updates).

        Args:
            document_id: The document ID whose chunks should be deleted.
            index_name: OpenSearch index name.

        Returns:
            Dict with deletion results.
        """
        index_name = index_name or settings.opensearch_index

        response = self.client.delete_by_query(
            index=index_name,
            body={
                "query": {
                    "term": {"document_id": document_id}
                }
            },
            refresh=True,
        )
        deleted = response.get("deleted", 0)
        logger.info(f"Deleted {deleted} chunks for document '{document_id}'")
        return {"deleted": deleted}

    def _generate_actions(
        self,
        chunk_vector_pairs: list[tuple[Chunk, list[float]]],
        index_name: str,
    ) -> Iterator[dict]:
        """Generate bulk actions from chunk/vector pairs."""
        for chunk, vector in chunk_vector_pairs:
            yield {
                "_index": index_name,
                "_id": chunk.chunk_id,
                "_source": {
                    "chunk_id": chunk.chunk_id,
                    "document_id": chunk.document_id,
                    "chunk_index": chunk.chunk_index,
                    "chunk_text": chunk.chunk_text,
                    "chunk_vector": vector,
                    "document_title": chunk.document_title,
                    "document_summary": chunk.document_summary,
                    "header_path": chunk.header_path,
                    "element_types": chunk.element_types,
                    "metadata": chunk.metadata,
                },
            }