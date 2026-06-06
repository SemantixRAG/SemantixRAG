"""Incremental update logic for keeping the vector store synchronized."""
import logging
from pathlib import Path
from typing import Optional

from config.settings import settings
from ..indexing.bulk_indexer import BulkIndexer
from ..monitoring.logger import get_logger

logger = logging.getLogger(__name__)


class IncrementalUpdater:
    """Handles incremental updates to the OpenSearch index.

    When a document is updated: deletes all existing chunks for that
    document_id, then re-triggers the full extraction/chunking/embedding pipeline.
    """

    def __init__(self, bulk_indexer: Optional[BulkIndexer] = None):
        self.bulk_indexer = bulk_indexer or BulkIndexer()

    def before_reindex(self, file_path: Path, document_id: str) -> dict:
        """Prepare for re-indexing by cleaning up existing entries.

        Args:
            file_path: Path to the document.
            document_id: Unique document identifier.

        Returns:
            Deletion result from OpenSearch.
        """
        logger.info(
            f"Preparing to re-index '{file_path.name}' "
            f"(document_id={document_id})"
        )
        return self.bulk_indexer.delete_document_chunks(document_id)

    def process_deletion(self, file_path: Path, document_id: str) -> dict:
        """Handle file deletion: remove all chunks from index.

        Args:
            file_path: Path to the deleted document.
            document_id: Unique document identifier.

        Returns:
            Deletion result from OpenSearch.
        """
        logger.info(
            f"Processing deletion of '{file_path.name}' "
            f"(document_id={document_id})"
        )
        result = self.bulk_indexer.delete_document_chunks(document_id)
        logger.info(
            f"Deleted {result.get('deleted', 0)} chunks for '{document_id}'"
        )
        return result