"""Base extractor interface for document parsing."""
import abc
from pathlib import Path
from ..models import ExtractionResult


class BaseExtractor(abc.ABC):
    """Abstract base class for all document extractors."""

    supported_extensions: list[str] = []

    @abc.abstractmethod
    def extract(self, file_path: Path, document_id: str) -> ExtractionResult:
        """Extract structured content from a document.

        Args:
            file_path: Path to the source document.
            document_id: Unique identifier for the document.

        Returns:
            ExtractionResult containing structured elements.
        """
        ...

    @abc.abstractmethod
    def supports(self, file_path: Path) -> bool:
        """Check if this extractor can handle the given file.

        Args:
            file_path: Path to the document.

        Returns:
            True if the extractor can handle this file type.
        """
        ...