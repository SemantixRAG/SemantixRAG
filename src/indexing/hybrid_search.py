"""Hybrid search combining k-NN vector search and BM25 with RRF fusion."""
import logging
from typing import Optional

from config.settings import settings
from .connection import OpenSearchConnection

logger = logging.getLogger(__name__)


class HybridSearch:
    """Performs hybrid search using both dense vector and BM25 keyword search.

    Executes a k-NN vector search on chunk_vector and a BM25 keyword search
    on chunk_text, then merges results using Reciprocal Rank Fusion (RRF).
    """

    def __init__(self, connection: Optional[OpenSearchConnection] = None):
        self.connection = connection or OpenSearchConnection.get_instance()
        self.client = self.connection.client

    def search(
        self,
        query_text: str,
        query_vector: list[float],
        index_name: Optional[str] = None,
        size: int = 10,
        rrf_k: int = 60,
        min_score: float = 0.0,
    ) -> dict:
        """Execute a hybrid search with RRF fusion.

        Args:
            query_text: The raw text query for BM25 search.
            query_vector: The dense vector query for k-NN search.
            index_name: OpenSearch index name.
            size: Number of results to return.
            rrf_k: RRF constant (default 60).
            min_score: Minimum score threshold.

        Returns:
            Dict with 'hits' list and 'total' count.
        """
        index_name = index_name or settings.opensearch_index

        query = {
            "size": size,
            "query": {
                "hybrid": {
                    "queries": [
                        {
                            "match": {
                                "chunk_text": {
                                    "query": query_text,
                                    "minimum_should_match": "50%",
                                }
                            }
                        },
                        {
                            "knn": {
                                "chunk_vector": {
                                    "vector": query_vector,
                                    "k": size * 2,
                                }
                            }
                        },
                    ],
                }
            },
            "ext": {
                "hybrid_search": {
                    "rank_window_size": 100,
                    "rrf_k": rrf_k,
                }
            },
            "_source": {
                "excludes": ["chunk_vector"]
            },
        }

        try:
            response = self.client.search(
                index=index_name,
                body=query,
                params={"search_pipeline": "hybrid-search-pipeline"},
            )
        except Exception:
            # Fallback: if hybrid pipeline is not configured, run separate queries
            return self._search_separate(
                query_text, query_vector, index_name, size, rrf_k
            )

        hits = response.get("hits", {})
        return {
            "hits": [
                {
                    "chunk_id": hit["_source"]["chunk_id"],
                    "document_id": hit["_source"]["document_id"],
                    "chunk_text": hit["_source"]["chunk_text"],
                    "score": hit["_score"],
                    "header_path": hit["_source"].get("header_path"),
                    "document_title": hit["_source"].get("document_title"),
                }
                for hit in hits.get("hits", [])
            ],
            "total": hits.get("total", {}).get("value", 0),
        }

    def _search_separate(
        self,
        query_text: str,
        query_vector: list[float],
        index_name: str,
        size: int,
        rrf_k: int,
    ) -> dict:
        """Fallback: run k-NN and BM25 queries separately, then fuse with RRF."""
        # BM25 search
        bm25_response = self.client.search(
            index=index_name,
            body={
                "size": size * 2,
                "query": {
                    "match": {
                        "chunk_text": {
                            "query": query_text,
                            "minimum_should_match": "50%",
                        }
                    }
                },
                "_source": {"excludes": ["chunk_vector"]},
            },
        )

        # k-NN search
        knn_response = self.client.search(
            index=index_name,
            body={
                "size": size * 2,
                "query": {
                    "knn": {
                        "chunk_vector": {
                            "vector": query_vector,
                            "k": size * 2,
                        }
                    }
                },
                "_source": {"excludes": ["chunk_vector"]},
            },
        )

        # RRF fusion
        bm25_hits = bm25_response.get("hits", {}).get("hits", [])
        knn_hits = knn_response.get("hits", {}).get("hits", [])

        # Score each hit
        scored: dict[str, dict] = {}
        for rank, hit in enumerate(bm25_hits):
            chunk_id = hit["_source"]["chunk_id"]
            scored[chunk_id] = {
                "chunk_id": chunk_id,
                "document_id": hit["_source"]["document_id"],
                "chunk_text": hit["_source"]["chunk_text"],
                "header_path": hit["_source"].get("header_path"),
                "document_title": hit["_source"].get("document_title"),
                "bm25_score": 1.0 / (rrf_k + rank),
                "knn_score": 0.0,
                "rrf_score": 1.0 / (rrf_k + rank),
            }

        for rank, hit in enumerate(knn_hits):
            chunk_id = hit["_source"]["chunk_id"]
            if chunk_id in scored:
                scored[chunk_id]["knn_score"] = 1.0 / (rrf_k + rank)
                scored[chunk_id]["rrf_score"] += 1.0 / (rrf_k + rank)
            else:
                scored[chunk_id] = {
                    "chunk_id": chunk_id,
                    "document_id": hit["_source"]["document_id"],
                    "chunk_text": hit["_source"]["chunk_text"],
                    "header_path": hit["_source"].get("header_path"),
                    "document_title": hit["_source"].get("document_title"),
                    "bm25_score": 0.0,
                    "knn_score": 1.0 / (rrf_k + rank),
                    "rrf_score": 1.0 / (rrf_k + rank),
                }

        # Sort by RRF score descending
        sorted_results = sorted(
            scored.values(),
            key=lambda x: x["rrf_score"],
            reverse=True,
        )[:size]

        return {
            "hits": [
                {
                    "chunk_id": r["chunk_id"],
                    "document_id": r["document_id"],
                    "chunk_text": r["chunk_text"],
                    "score": r["rrf_score"],
                    "header_path": r.get("header_path"),
                    "document_title": r.get("document_title"),
                }
                for r in sorted_results
            ],
            "total": len(sorted_results),
        }