"""Contextual enrichment pipeline that injects document-level context into chunks."""
import logging
from typing import Optional
from ..models import ExtractionResult, Chunk

logger = logging.getLogger(__name__)


class ContextualEnricher:
    """Enriches chunks with document-level context.

    Passes the complete document through a lightweight LLM to generate a
    concise document summary, then prepends the title and summary to each
    chunk so that no chunk loses its global context during retrieval.
    """

    def __init__(
        self,
        model_name: str = "gemma:2b",
        endpoint: Optional[str] = None,
        use_mock: bool = False,
        max_summary_tokens: int = 256,
    ):
        self.model_name = model_name
        self.endpoint = endpoint
        self.use_mock = use_mock
        self.max_summary_tokens = max_summary_tokens

    def enrich(self, extraction: ExtractionResult, chunks: list[Chunk]) -> list[Chunk]:
        """Enrich chunks with document-level context.

        Args:
            extraction: The full extraction result with document text.
            chunks: The chunks to enrich.

        Returns:
            Enriched chunks with title and summary prepended.
        """
        if not chunks:
            return chunks

        # Generate document summary
        summary = self._generate_summary(extraction)

        # Enrich each chunk
        for chunk in chunks:
            chunk.document_title = extraction.title
            chunk.document_summary = summary
            chunk.metadata["enriched_at_indexing"] = True

            # Prepend context to chunk text for better vectorization
            context_parts = []
            if extraction.title:
                context_parts.append(f"Document Title: {extraction.title}")
            if summary:
                context_parts.append(f"Document Summary: {summary}")

            context_prefix = "\n\n---\n\n".join(context_parts) if context_parts else ""
            if context_prefix:
                chunk.chunk_text = f"{context_prefix}\n\n---\n\n{chunk.chunk_text}"
                chunk.metadata["context_enriched"] = True

        logger.info(
            f"Enriched {len(chunks)} chunks for document '{extraction.document_id}'"
            f" with title='{extraction.title}'"
        )
        return chunks

    def _generate_summary(self, extraction: ExtractionResult) -> Optional[str]:
        """Generate a concise summary of the document using an LLM."""
        if self.use_mock:
            return self._mock_summarize(extraction)

        if self.endpoint:
            return self._api_summarize(extraction)

        return self._local_llm_summarize(extraction)

    def _mock_summarize(self, extraction: ExtractionResult) -> str:
        """Generate a mock summary for testing."""
        text = extraction.raw_text[:500]
        logger.info(f"[MOCK] Generating summary for '{extraction.document_id}'")
        return f"This document ({extraction.filename}) discusses: {text[:200]}..."

    def _api_summarize(self, extraction: ExtractionResult) -> Optional[str]:
        """Generate summary via an LLM API endpoint."""
        try:
            import requests

            text_sample = extraction.raw_text[:4000]
            prompt = (
                f"Summarize the following document in 2-3 sentences. "
                f"Focus on the main topic and key points:\n\n{text_sample}"
            )

            payload = {
                "model": self.model_name,
                "messages": [
                    {"role": "user", "content": prompt},
                ],
                "max_tokens": self.max_summary_tokens,
                "temperature": 0.3,
            }

            response = requests.post(
                self.endpoint,
                json=payload,
                timeout=60,
            )
            response.raise_for_status()
            result = response.json()
            summary = (
                result.get("choices", [{}])[0]
                .get("message", {})
                .get("content", "")
                .strip()
            )
            return summary if summary else None

        except Exception as e:
            logger.error(f"API summarization failed: {e}")
            return None

    def _local_llm_summarize(self, extraction: ExtractionResult) -> Optional[str]:
        """Generate summary using a local LLM (e.g., via Ollama)."""
        try:
            import requests

            text_sample = extraction.raw_text[:4000]
            prompt = (
                "Summarize the following document in 2-3 sentences. "
                "Focus on the main topic and key points."
            )

            payload = {
                "model": self.model_name,
                "messages": [
                    {"role": "user", "content": f"{prompt}\n\n{text_sample}"},
                ],
                "stream": False,
                "options": {"temperature": 0.3},
            }

            endpoint = self.endpoint or "http://localhost:11434/api/chat"
            response = requests.post(endpoint, json=payload, timeout=120)
            response.raise_for_status()
            result = response.json()
            summary = result.get("message", {}).get("content", "").strip()
            return summary if summary else None

        except Exception as e:
            logger.error(f"Local LLM summarization failed: {e}")
            return None