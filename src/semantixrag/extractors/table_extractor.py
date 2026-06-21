"""Fallback table extractor using Vision-Language Models for complex layouts."""
import json
import logging
import base64
from pathlib import Path
from typing import Optional

from ..models import ExtractedElement, ElementType

logger = logging.getLogger(__name__)


class TableExtractor:
    """Extracts tables using a VLM fallback when standard OCR fails.

    This extractor is designed as a fallback. For pages where standard
    table extraction yields poor results, the page image is sent to a
    local VLM (e.g., LLaVA, ColPali) that returns the table in Markdown.
    """

    def __init__(
        self,
        model_name: str = "llava",
        endpoint: Optional[str] = None,
        use_mock: bool = False,
    ):
        self.model_name = model_name
        self.endpoint = endpoint
        self.use_mock = use_mock

    def extract_table_from_image(
        self,
        image_path: Path,
        page_number: int = 0,
    ) -> Optional[ExtractedElement]:
        """Extract a table from a page image using a VLM.

        Args:
            image_path: Path to the page image (PNG/JPEG).
            page_number: Page number in the source document.

        Returns:
            ExtractedElement with the table in markdown format, or None.
        """
        if self.use_mock:
            return self._mock_extract(image_path, page_number)

        if self.endpoint:
            return self._api_extract(image_path, page_number)

        return self._local_vlm_extract(image_path, page_number)

    def _mock_extract(self, image_path: Path, page_number: int) -> Optional[ExtractedElement]:
        """Mock extraction for testing without a VLM."""
        logger.info(f"[MOCK] Extracting table from {image_path.name}")
        # In production, this would call the VLM.
        # Returning None signals that a real VLM should process it.
        return None

    def _api_extract(self, image_path: Path, page_number: int) -> Optional[ExtractedElement]:
        """Extract table via a VLM API endpoint."""
        import requests

        try:
            with open(image_path, "rb") as f:
                img_b64 = base64.b64encode(f.read()).decode("utf-8")

            payload = {
                "model": self.model_name,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": (
                                    "Extract the table from this image "
                                    "and return it as a Markdown table. "
                                    "Preserve all rows, columns, and data. "
                                    "Return ONLY the markdown table."
                                ),
                            },
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/png;base64,{img_b64}"},
                            },
                        ],
                    },
                ],
                "max_tokens": 1024,
                "temperature": 0.1,
            }

            response = requests.post(
                self.endpoint,
                json=payload,
                timeout=60,
            )
            response.raise_for_status()
            result = response.json()

            markdown_table = (
                result.get("choices", [{}])[0]
                .get("message", {})
                .get("content", "")
                .strip()
            )

            if markdown_table:
                return ExtractedElement(
                    element_type=ElementType.TABLE,
                    text=markdown_table,
                    markdown=markdown_table,
                    page_number=page_number,
                    metadata={"extraction_method": f"vlm_{self.model_name}"},
                )

        except Exception as e:
            logger.error(f"VLM table extraction failed for {image_path.name}: {e}")

        return None

    def _local_vlm_extract(self, image_path: Path, page_number: int) -> Optional[ExtractedElement]:
        """Extract table using a locally-running VLM (e.g., via Ollama)."""
        try:
            import requests

            with open(image_path, "rb") as f:
                img_b64 = base64.b64encode(f.read()).decode("utf-8")

            payload = {
                "model": self.model_name,
                "messages": [
                    {
                        "role": "user",
                        "content": (
                            "Extract the table from this image "
                            "and return it as a Markdown table. "
                            "Preserve all rows, columns, and data. "
                            "Return ONLY the markdown table."
                        ),
                        "images": [img_b64],
                    },
                ],
                "stream": False,
                "options": {"temperature": 0.1},
            }

            endpoint = self.endpoint or "http://localhost:11434/api/chat"
            response = requests.post(endpoint, json=payload, timeout=120)
            response.raise_for_status()
            result = response.json()

            markdown_table = result.get("message", {}).get("content", "").strip()

            if markdown_table:
                return ExtractedElement(
                    element_type=ElementType.TABLE,
                    text=markdown_table,
                    markdown=markdown_table,
                    page_number=page_number,
                    metadata={"extraction_method": f"vlm_local_{self.model_name}"},
                )

        except ImportError:
            logger.warning("requests not available for local VLM call.")
        except Exception as e:
            logger.error(f"Local VLM extraction failed for {image_path.name}: {e}")

        return None