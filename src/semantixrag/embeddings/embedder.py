"""Embedding model integration using HuggingFace sentence-transformers."""
import logging
import numpy as np
from typing import Optional
from tqdm import tqdm

from ..models import Chunk

logger = logging.getLogger(__name__)


class EmbeddingModel:
    """Wrapper around a HuggingFace sentence-transformers embedding model.

    Uses BAAI/bge-m3 by default, which supports multi-lingual dense embeddings.
    Falls back gracefully if the model is unavailable.
    """

    def __init__(
        self,
        model_name: str = "BAAI/bge-m3",
        device: Optional[str] = None,
        batch_size: int = 32,
        use_mock: bool = False,
    ):
        self.model_name = model_name
        self.device = device or self._detect_device()
        self.batch_size = batch_size
        self.use_mock = use_mock
        self._model = None
        self._model_loaded = False

    def _detect_device(self) -> str:
        """Auto-detect the best available device."""
        try:
            import torch
            if torch.cuda.is_available():
                return "cuda"
            elif hasattr(torch, "mps") and torch.backends.mps.is_available():
                return "mps"
        except ImportError:
            pass
        return "cpu"

    def load_model(self) -> None:
        """Load the embedding model from HuggingFace."""
        if self._model_loaded:
            return

        if self.use_mock:
            logger.info("[MOCK] Using mock embedding model")
            self._model_loaded = True
            return

        try:
            from sentence_transformers import SentenceTransformer

            logger.info(f"Loading embedding model '{self.model_name}' on {self.device}...")
            self._model = SentenceTransformer(
                self.model_name,
                device=self.device,
            )
            self._model_loaded = True
            logger.info(f"Model '{self.model_name}' loaded successfully")

        except Exception as e:
            logger.warning(
                f"Failed to load model '{self.model_name}': {e}. "
                "Falling back to mock embeddings."
            )
            self.use_mock = True
            self._model_loaded = True

    def encode(self, texts: list[str]) -> list[list[float]]:
        """Encode a list of texts into embedding vectors.

        Args:
            texts: List of text strings to encode.

        Returns:
            List of embedding vectors as float lists.
        """
        self.load_model()

        if not texts:
            return []

        if self.use_mock:
            return self._mock_encode(texts)

        try:
            # Add instruction prefix for bge models
            prefixed = [
                f"Represent this sentence for searching relevant passages: {t}"
                for t in texts
            ]

            embeddings = self._model.encode(
                prefixed,
                batch_size=self.batch_size,
                show_progress_bar=True,
                normalize_embeddings=True,
            )
            return embeddings.tolist()

        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            return self._mock_encode(texts)

    def encode_chunks(self, chunks: list[Chunk]) -> list[tuple[Chunk, list[float]]]:
        """Encode a list of chunks into (chunk, vector) pairs.

        Args:
            chunks: List of Chunk objects.

        Returns:
            List of (chunk, embedding_vector) tuples.
        """
        texts = [c.chunk_text for c in chunks]
        vectors = self.encode(texts)

        result = []
        for chunk, vector in zip(chunks, vectors):
            if isinstance(vector, np.ndarray):
                vector = vector.tolist()
            result.append((chunk, list(vector)))

        return result

    def _mock_encode(self, texts: list[str]) -> list[list[float]]:
        """Generate mock embeddings for testing."""
        dimension = 1024 if "bge-m3" in self.model_name else 768
        return [
            [float(np.sin(i + idx)) for i in range(dimension)]
            for idx in range(len(texts))
        ]

    @property
    def dimension(self) -> int:
        """Get the embedding dimension for this model."""
        if self._model is not None:
            return self._model.get_sentence_embedding_dimension()
        return 1024  # Default for bge-m3