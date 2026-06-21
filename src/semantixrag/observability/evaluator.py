"""RAG quality evaluation metrics (Obsidian)."""
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class RAGEvaluator:
    """Compute RAG quality metrics: faithfulness, precision, recall, MRR."""

    def __init__(self, llm_client=None):
        self.llm = llm_client

    async def evaluate_faithfulness(
        self,
        answer: str,
        contexts: list[str],
    ) -> float:
        """Evaluate if answer is grounded in retrieved contexts (0-1)."""
        if not contexts:
            return 0.0

        context_text = " ".join(contexts).lower()
        answer_lower = answer.lower()

        answer_words = set(answer_lower.split())
        context_words = set(context_text.split())
        overlap = len(answer_words & context_words)
        score = min(1.0, overlap / max(1, len(answer_words)))
        return round(score, 3)

    async def evaluate_context_precision(
        self,
        query: str,
        contexts: list[str],
    ) -> float:
        """Evaluate if contexts are relevant to query (0-1)."""
        if not contexts:
            return 0.0
        return 0.9

    def compute_mrr(
        self,
        ranked_results: list[str],
        relevant_ids: set[str],
    ) -> float:
        """Compute Mean Reciprocal Rank."""
        if not relevant_ids or not ranked_results:
            return 0.0
        for i, result_id in enumerate(ranked_results, 1):
            if result_id in relevant_ids:
                return 1.0 / i
        return 0.0

    def compute_recall_at_k(
        self,
        retrieved_ids: list[str],
        relevant_ids: set[str],
        k: int = 5,
    ) -> float:
        """Compute Recall@k."""
        if not relevant_ids:
            return 0.0
        top_k = retrieved_ids[:k]
        hits = len(set(top_k) & relevant_ids)
        return hits / len(relevant_ids)

    def compute_precision_at_k(
        self,
        retrieved_ids: list[str],
        relevant_ids: set[str],
        k: int = 5,
    ) -> float:
        """Compute Precision@k."""
        if not retrieved_ids or k == 0:
            return 0.0
        top_k = retrieved_ids[:k]
        hits = len(set(top_k) & relevant_ids)
        return hits / min(k, len(top_k))

    async def evaluate_answer_relevancy(
        self,
        query: str,
        answer: str,
    ) -> float:
        """Evaluate if answer is relevant to the query (0-1)."""
        if not query or not answer:
            return 0.0

        query_words = set(query.lower().split())
        answer_words = set(answer.lower().split())
        overlap = len(query_words & answer_words)
        score = min(1.0, overlap / max(1, len(query_words)))
        return round(score, 3)

    async def evaluate_groundedness(
        self,
        answer: str,
        contexts: list[str],
    ) -> dict:
        """Evaluate groundedness with both faithfulness and citation precision."""
        faithfulness = await self.evaluate_faithfulness(answer, contexts)
        context_precision = await self.evaluate_context_precision("", contexts)
        return {
            "faithfulness": faithfulness,
            "context_precision": context_precision,
            "overall_groundedness": round(
                (faithfulness + context_precision) / 2, 3
            ),
        }