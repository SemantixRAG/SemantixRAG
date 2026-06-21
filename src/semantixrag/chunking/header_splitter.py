"""Markdown/Header-aware text splitter that preserves document structure."""
import re
import logging
from typing import Optional
from ..models import ExtractionResult, Chunk, ElementType

logger = logging.getLogger(__name__)


class HeaderAwareSplitter:
    """Splits extracted document elements into chunks while preserving header hierarchy.

    Groups paragraphs under their parent headers so that each chunk maintains
    semantic boundaries. Uses a configurable max token threshold with overlap.
    """

    def __init__(
        self,
        max_tokens: int = 512,
        overlap_tokens: int = 64,
        approx_chars_per_token: int = 4,
    ):
        self.max_tokens = max_tokens
        self.overlap_tokens = overlap_tokens
        self.approx_chars_per_token = approx_chars_per_token

    def split(self, extraction: ExtractionResult) -> list[Chunk]:
        """Split extraction results into header-aware chunks.

        Args:
            extraction: Standardized extraction output.

        Returns:
            List of Chunk objects with preserved header context.
        """
        if not extraction.elements:
            logger.warning(f"No elements to chunk for {extraction.document_id}")
            return []

        # Build a hierarchy of elements grouped by headers
        header_groups = self._group_by_headers(extraction.elements)

        # Flatten groups into chunks
        chunks: list[Chunk] = []
        current_chunk_parts: list[str] = []
        current_header_path: Optional[str] = None
        current_element_types: list[str] = []
        char_count = 0
        chunk_index = 0

        for group in header_groups:
            header_path, elements = group["header_path"], group["elements"]
            group_text = self._elements_to_text(elements)
            group_types = [e.element_type.value for e in elements]
            group_chars = len(group_text)

            # If this group alone exceeds max_tokens, we need to split it further
            if group_chars > self.max_tokens * self.approx_chars_per_token:
                # First flush any accumulated content
                if current_chunk_parts:
                    chunks.append(self._make_chunk(
                        extraction, chunk_index, current_chunk_parts,
                        current_header_path, current_element_types,
                    ))
                    chunk_index += 1
                    current_chunk_parts = []
                    current_element_types = []

                # Split the large group into sub-chunks
                sub_chunks_text = self._split_text_by_tokens(
                    group_text, group_types,
                )
                for sub_text, sub_types in sub_chunks_text:
                    chunks.append(self._make_chunk(
                        extraction, chunk_index, [sub_text],
                        header_path, sub_types,
                    ))
                    chunk_index += 1
                continue

            # If adding this group would exceed max_tokens, flush first
            if char_count + group_chars > self.max_tokens * self.approx_chars_per_token:
                if current_chunk_parts:
                    chunks.append(self._make_chunk(
                        extraction, chunk_index, current_chunk_parts,
                        current_header_path, current_element_types,
                    ))
                    chunk_index += 1

                    # Apply overlap: keep last portion
                    overlap_text = self._get_overlap_text(current_chunk_parts)
                    current_chunk_parts = [overlap_text] if overlap_text else []
                    current_element_types = current_element_types[-1:] if current_element_types else []
                    char_count = len(overlap_text)

            current_chunk_parts.append(group_text)
            current_element_types.extend(group_types)
            current_header_path = header_path or current_header_path
            char_count = sum(len(p) for p in current_chunk_parts)

        # Flush remaining
        if current_chunk_parts:
            chunks.append(self._make_chunk(
                extraction, chunk_index, current_chunk_parts,
                current_header_path, current_element_types,
            ))

        logger.info(
            f"Split {extraction.document_id} into {len(chunks)} chunks "
            f"({len(extraction.elements)} elements)"
        )
        return chunks

    def _group_by_headers(self, elements: list) -> list[dict]:
        """Group elements under their nearest preceding header."""
        groups: list[dict] = []
        current_headers: list[str] = []
        current_group: list = []

        for element in elements:
            if element.element_type in (ElementType.HEADER, ElementType.TITLE):
                # Flush current group
                if current_group:
                    groups.append({
                        "header_path": " / ".join(current_headers) if current_headers else None,
                        "elements": current_group,
                    })
                    current_group = []

                # Update header hierarchy based on header level
                header_text = element.text.strip()
                level = self._infer_header_level(element.text, element.metadata)

                # Prune headers deeper than current level
                while current_headers and len(current_headers) >= level:
                    current_headers.pop()
                current_headers.append(header_text)

                # Start new group with this header
                groups.append({
                    "header_path": " / ".join(current_headers),
                    "elements": [element],
                })
            else:
                current_group.append(element)

        # Flush final group
        if current_group:
            groups.append({
                "header_path": " / ".join(current_headers) if current_headers else None,
                "elements": current_group,
            })

        return groups

    def _infer_header_level(self, text: str, metadata: dict) -> int:
        """Infer header level from markdown markers or metadata."""
        # Check for markdown heading markers
        match = re.match(r'^(#{1,6})\s', text)
        if match:
            return len(match.group(1))

        # Check metadata for category
        cat = metadata.get("category", "")
        if "sub" in cat.lower() or "subhead" in cat.lower():
            return 3
        if "headline" in cat.lower():
            return 2

        # Default to level 1 for Title, level 2 for Header
        return 1

    def _elements_to_text(self, elements: list) -> str:
        """Convert a list of elements to a text string."""
        parts = []
        for elem in elements:
            if elem.element_type == ElementType.TABLE and elem.markdown:
                parts.append(elem.markdown)
            else:
                parts.append(elem.text)
        return "\n\n".join(parts)

    def _split_text_by_tokens(self, text: str, types: list[str]) -> list[tuple[str, list[str]]]:
        """Split a long text into chunks respecting token limits."""
        char_limit = self.max_tokens * self.approx_chars_per_token
        overlap_chars = self.overlap_tokens * self.approx_chars_per_token

        chunks: list[tuple[str, list[str]]] = []
        paragraphs = text.split("\n\n")

        current = ""
        for para in paragraphs:
            if len(current) + len(para) > char_limit and current:
                chunks.append((current.strip(), types))
                # Overlap: keep last portion
                current = current[-overlap_chars:] + "\n\n" if overlap_chars > 0 else ""
            current += ("\n\n" if current else "") + para

        if current.strip():
            chunks.append((current.strip(), types))

        return chunks if chunks else [(text.strip(), types)]

    def _get_overlap_text(self, chunk_parts: list[str]) -> str:
        """Extract the trailing portion of a chunk for overlap."""
        full = "\n\n".join(chunk_parts)
        overlap_chars = self.overlap_tokens * self.approx_chars_per_token
        if len(full) <= overlap_chars:
            return full
        return full[-overlap_chars:]

    def _make_chunk(
        self,
        extraction: ExtractionResult,
        chunk_index: int,
        parts: list[str],
        header_path: Optional[str],
        element_types: list[str],
    ) -> Chunk:
        """Create a Chunk object from accumulated parts."""
        text = "\n\n".join(p for p in parts if p.strip())

        return Chunk(
            chunk_id=f"{extraction.document_id}_chunk_{chunk_index:04d}",
            document_id=extraction.document_id,
            chunk_index=chunk_index,
            chunk_text=text,
            document_title=extraction.title,
            document_summary=None,  # Will be populated by enricher
            header_path=header_path,
            element_types=list(set(element_types)),
            metadata={
                "filename": extraction.filename,
                "extraction_method": extraction.extraction_method,
                "num_elements_in_chunk": len(parts),
            },
        )