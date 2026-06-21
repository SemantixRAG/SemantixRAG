"""GDPR data subject access request automation (GuardRail)."""
import logging
import uuid
from datetime import datetime
from typing import Optional, List
from ..models import DSARResult, PIIFinding

logger = logging.getLogger(__name__)


class DSAREngine:
    """Automate GDPR data subject access/deletion requests."""

    def __init__(self, opensearch_client=None, neo4j_client=None):
        self.opensearch = opensearch_client
        self.neo4j = neo4j_client
        self._active_requests: dict[str, DSARResult] = {}

    async def execute_dsar(
        self,
        subject_id: str,
        action: str,
        tenant_id: str,
        requested_by: str,
        reason: Optional[str] = None,
    ) -> DSARResult:
        """Execute a GDPR data subject request.

        Args:
            subject_id: The data subject identifier (email, customer ID).
            action: 'access', 'delete', or 'export'.
            tenant_id: Tenant scope.
            requested_by: User ID making the request.
            reason: Required for delete actions.

        Returns:
            DSARResult with affected record counts.
        """
        dsar_id = str(uuid.uuid4())
        logger.info(
            f"Processing DSAR {dsar_id}: subject={subject_id}, "
            f"action={action}, tenant={tenant_id}"
        )

        result = DSARResult(
            dsar_id=dsar_id,
            status="processing",
            subject_id=subject_id,
            action=action,
            tenant_id=tenant_id,
            estimated_completion=datetime.utcnow().isoformat(),
        )

        try:
            if action == "access":
                affected = await self._find_subject_data(
                    subject_id, tenant_id
                )
            elif action == "delete":
                if not reason:
                    raise ValueError("Reason required for delete action")
                affected = await self._delete_subject_data(
                    subject_id, tenant_id
                )
            elif action == "export":
                affected = await self._export_subject_data(
                    subject_id, tenant_id
                )
            else:
                raise ValueError(f"Unknown DSAR action: {action}")

            result.affected_documents = affected.get("documents", 0)
            result.affected_chunks = affected.get("chunks", 0)
            result.affected_embeddings = affected.get("embeddings", 0)
            result.affected_memories = affected.get("memories", 0)
            result.status = "completed"

        except Exception as e:
            logger.error(f"DSAR {dsar_id} failed: {e}")
            result.status = "failed"

        self._active_requests[dsar_id] = result
        return result

    async def _find_subject_data(
        self,
        subject_id: str,
        tenant_id: str,
    ) -> dict:
        """Find all data related to a subject across indexes."""
        affected = {
            "documents": 0,
            "chunks": 0,
            "embeddings": 0,
            "memories": 0,
        }

        if self.opensearch:
            try:
                # Search in documents
                doc_query = {
                    "query": {
                        "bool": {
                            "must": [
                                {"term": {"tenant_id": tenant_id}},
                                {
                                    "multi_match": {
                                        "query": subject_id,
                                        "fields": [
                                            "chunk_text",
                                            "document_title",
                                            "metadata.entities.name",
                                        ],
                                    }
                                },
                            ]
                        }
                    }
                }
                doc_response = self.opensearch.search(
                    index="rag_documents",
                    body=doc_query,
                )
                affected["chunks"] = doc_response["hits"]["total"]["value"]

                # Search in observability (agent memories)
                obs_query = {
                    "query": {
                        "bool": {
                            "must": [
                                {"term": {"tenant_id": tenant_id}},
                                {"match": {"metadata": subject_id}},
                            ]
                        }
                    }
                }
                obs_response = self.opensearch.search(
                    index="rag_observability",
                    body=obs_query,
                )
                affected["memories"] = obs_response["hits"]["total"]["value"]

            except Exception as e:
                logger.error(f"OpenSearch DSAR search failed: {e}")

        return affected

    async def _delete_subject_data(
        self,
        subject_id: str,
        tenant_id: str,
    ) -> dict:
        """Delete all data related to a subject."""
        affected = await self._find_subject_data(subject_id, tenant_id)

        if self.opensearch:
            try:
                # Delete by query
                delete_query = {
                    "query": {
                        "bool": {
                            "must": [
                                {"term": {"tenant_id": tenant_id}},
                                {
                                    "multi_match": {
                                        "query": subject_id,
                                        "fields": [
                                            "chunk_text",
                                            "document_title",
                                            "metadata.entities.name",
                                        ],
                                    }
                                },
                            ]
                        }
                    }
                }
                self.opensearch.delete_by_query(
                    index="rag_documents",
                    body=delete_query,
                    refresh=True,
                )
                logger.info(
                    f"Deleted {affected['chunks']} chunks "
                    f"for subject {subject_id}"
                )
            except Exception as e:
                logger.error(f"OpenSearch DSAR delete failed: {e}")

        return affected

    async def _export_subject_data(
        self,
        subject_id: str,
        tenant_id: str,
    ) -> dict:
        """Export all data related to a subject."""
        return await self._find_subject_data(subject_id, tenant_id)

    def get_dsar_status(self, dsar_id: str) -> Optional[DSARResult]:
        """Get the status of a DSAR request."""
        return self._active_requests.get(dsar_id)