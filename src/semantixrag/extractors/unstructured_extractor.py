"""PDF/Text extractor using the Unstructured library."""
import hashlib
from pathlib import Path
from typing import Optional
import logging

from ..models import ExtractionResult, ExtractedElement, ElementType
from .base import BaseExtractor

logger = logging.getLogger(__name__)


class UnstructuredExtractor(BaseExtractor):
    """Extracts structured content from PDFs and text files using Unstructured.io."""

    supported_extensions = [".pdf", ".txt", ".md", ".docx", ".html", ".xml", ".csv"]

    def __init__(self, extract_tables: bool = True, include_page_breaks: bool = True):
        self.extract_tables = extract_tables
        self.include_page_breaks = include_page_breaks
        self._unstructured_available = False
        self._check_unstructured()

    def _check_unstructured(self) -> None:
        """Check if unstructured is available, log warning if not."""
        try:
            import unstructured  # noqa: F401
            self._unstructured_available = True
        except ImportError:
            logger.warning(
                "Unstructured library not installed. "
                "Install with: pip install 'unstructured[pdf,docx]'"
            )

    def supports(self, file_path: Path) -> bool:
        return file_path.suffix.lower() in self.supported_extensions

    def extract(self, file_path: Path, document_id: str) -> ExtractionResult:
        """Extract content using Unstructured.io library."""
        if not self._unstructured_available:
            return self._fallback_extract(file_path, document_id)

        return self._unstructured_extract(file_path, document_id)

    def _unstructured_extract(self, file_path: Path, document_id: str) -> ExtractionResult:
        """Extract using Unstructured's partition function."""
        from unstructured.partition.auto import partition

        elements = partition(
            str(file_path),
            strategy="hi_res",
            include_page_breaks=self.include_page_breaks,
            infer_table_structure=self.extract_tables,
        )

        extracted_elements: list[ExtractedElement] = []
        title: Optional[str] = None

        for element in elements:
            element_type = self._map_element_type(element.category)
            text = str(getattr(element, "text", "")).strip()
            if not text:
                continue

            metadata = {}
            page_number = getattr(element.metadata, "page_number", None) if element.metadata else None
            coordinates = getattr(element.metadata, "coordinates", None) if element.metadata else None

            bbox = None
            if coordinates and hasattr(coordinates, "points") and coordinates.points:
                points = coordinates.points
                bbox = {
                    "x1": float(points[0][0]),
                    "y1": float(points[0][1]),
                    "x2": float(points[2][0]),
                    "y2": float(points[2][1]),
                }

            extracted = ExtractedElement(
                element_type=element_type,
                text=text,
                bounding_box=bbox,
                page_number=page_number,
                metadata=metadata,
            )

            # Capture markdown for tables
            if element_type == ElementType.TABLE:
                try:
                    extracted.markdown = element.metadata.text_as_html if element.metadata else None
                except Exception:
                    pass

            extracted_elements.append(extracted)

            # First title/header becomes the document title
            if element_type in (ElementType.TITLE, ElementType.HEADER) and title is None:
                title = text

        raw_text = "\n\n".join(e.text for e in extracted_elements)
        if not title:
            title = file_path.stem

        result = ExtractionResult(
            document_id=document_id,
            filename=file_path.name,
            title=title,
            elements=extracted_elements,
            raw_text=raw_text,
            metadata={
                "file_size": file_path.stat().st_size,
                "num_elements": len(extracted_elements),
                "extraction_method": "unstructured",
            },
        )
        return result

    def _fallback_extract(self, file_path: Path, document_id: str) -> ExtractionResult:
        """Fallback extraction using basic PyMuPDF if Unstructured is unavailable."""
        text_content = file_path.read_text(encoding="utf-8", errors="replace")

        if file_path.suffix.lower() == ".pdf":
            try:
                import pypdf
                reader = pypdf.PdfReader(str(file_path))
                text_content = "\n".join(page.extract_text() for page in reader.pages)
            except ImportError:
                logger.warning("pypdf not available, reading raw text.")

        elements = [
            ExtractedElement(
                element_type=ElementType.PARAGRAPH,
                text=text_content.strip(),
            )
        ]

        return ExtractionResult(
            document_id=document_id,
            filename=file_path.name,
            title=file_path.stem,
            elements=elements,
            raw_text=text_content.strip(),
            metadata={
                "file_size": file_path.stat().st_size,
                "extraction_method": "fallback",
            },
        )

    @staticmethod
    def _map_element_type(category: str) -> ElementType:
        """Map Unstructured element categories to our standard types."""
        mapping = {
            "Title": ElementType.TITLE,
            "Header": ElementType.HEADER,
            "Headline": ElementType.HEADER,
            "Subheadline": ElementType.HEADER,
            "Paragraph": ElementType.PARAGRAPH,
            "NarrativeText": ElementType.PARAGRAPH,
            "UncategorizedText": ElementType.PARAGRAPH,
            "ListItem": ElementType.LIST_ITEM,
            "BulletedText": ElementType.LIST_ITEM,
            "Table": ElementType.TABLE,
            "FigureCaption": ElementType.FIGURE,
            "Image": ElementType.FIGURE,
            "Picture": ElementType.FIGURE,
            "Footer": ElementType.FOOTER,
            "Footerify": ElementType.FOOTER,
        }
        return mapping.get(category, ElementType.PARAGRAPH)

    @staticmethod
    def generate_document_id(file_path: Path) -> str:
        """Generate a deterministic document ID from file path."""
        raw = str(file_path.absolute())
        return hashlib.sha256(raw.encode()).hexdigest()[:16]