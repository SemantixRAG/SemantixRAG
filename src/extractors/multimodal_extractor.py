"""Multi-modal extraction for VLM, audio, and video content."""
import logging
from pathlib import Path
from typing import Optional, List
from ..models import ExtractionResult, ExtractedElement, ElementType

logger = logging.getLogger(__name__)


class MultiModalExtractor:
    """Extract content from images, audio, and video files."""

    def __init__(
        self,
        vlm_model: str = "llava-hf/llava-1.5-7b-hf",
        whisper_model: str = "openai/whisper-base",
        use_mock: bool = True,
    ):
        self.vlm_model = vlm_model
        self.whisper_model = whisper_model
        self.use_mock = use_mock
        self._vlm = None
        self._whisper = None

    def _init_vlm(self):
        """Initialize VLM model (lazy load)."""
        if self._vlm is not None or self.use_mock:
            return
        try:
            from transformers import LlavaForConditionalGeneration, AutoProcessor
            self._vlm = LlavaForConditionalGeneration.from_pretrained(self.vlm_model)
            self._processor = AutoProcessor.from_pretrained(self.vlm_model)
            logger.info(f"VLM model {self.vlm_model} loaded")
        except Exception as e:
            logger.warning(f"Failed to load VLM model: {e}. Using mock.")
            self.use_mock = True

    def _init_whisper(self):
        """Initialize Whisper model (lazy load)."""
        if self._whisper is not None or self.use_mock:
            return
        try:
            import whisper
            self._whisper = whisper.load_model(self.whisper_model)
            logger.info(f"Whisper model {self.whisper_model} loaded")
        except Exception as e:
            logger.warning(f"Failed to load Whisper: {e}. Using mock.")
            self.use_mock = True

    def extract_image(
        self,
        image_path: Path,
        document_id: str,
    ) -> ExtractedElement:
        """Extract content from an image using VLM."""
        if self.use_mock:
            return ExtractedElement(
                element_type=ElementType.FIGURE,
                text=f"[Image: {image_path.name}]",
                metadata={
                    "image_path": str(image_path),
                    "extraction_method": "mock_vlm",
                },
            )

        self._init_vlm()
        try:
            from PIL import Image as PILImage
            image = PILImage.open(image_path)
            prompt = "Describe this image in detail."
            inputs = self._processor(prompt, image, return_tensors="pt")
            output = self._vlm.generate(**inputs, max_new_tokens=200)
            description = self._processor.decode(output[0], skip_special_tokens=True)

            return ExtractedElement(
                element_type=ElementType.FIGURE,
                text=description,
                metadata={
                    "image_path": str(image_path),
                    "extraction_method": "vlm",
                    "vlm_model": self.vlm_model,
                },
            )
        except Exception as e:
            logger.error(f"VLM extraction failed for {image_path}: {e}")
            return ExtractedElement(
                element_type=ElementType.FIGURE,
                text=f"[Image: {image_path.name}]",
                metadata={"error": str(e)},
            )

    def transcribe_audio(
        self,
        audio_path: Path,
        document_id: str,
    ) -> ExtractedElement:
        """Transcribe audio using Whisper."""
        if self.use_mock:
            return ExtractedElement(
                element_type=ElementType.PARAGRAPH,
                text=f"[Audio transcription of {audio_path.name}]",
                metadata={
                    "audio_path": str(audio_path),
                    "extraction_method": "mock_whisper",
                },
            )

        self._init_whisper()
        try:
            result = self._whisper.transcribe(str(audio_path))
            return ExtractedElement(
                element_type=ElementType.PARAGRAPH,
                text=result["text"],
                metadata={
                    "audio_path": str(audio_path),
                    "extraction_method": "whisper",
                    "language": result.get("language", "unknown"),
                    "duration_seconds": result.get("duration", 0),
                },
            )
        except Exception as e:
            logger.error(f"Whisper transcription failed for {audio_path}: {e}")
            return ExtractedElement(
                element_type=ElementType.PARAGRAPH,
                text=f"[Audio: {audio_path.name}]",
                metadata={"error": str(e)},
            )

    def extract_video(
        self,
        video_path: Path,
        document_id: str,
        frame_interval: int = 30,
    ) -> List[ExtractedElement]:
        """Extract frames and audio from video."""
        elements = []

        if self.use_mock:
            elements.append(
                ExtractedElement(
                    element_type=ElementType.PARAGRAPH,
                    text=f"[Video analysis of {video_path.name}]",
                    metadata={
                        "video_path": str(video_path),
                        "extraction_method": "mock_video",
                    },
                )
            )
            return elements

        try:
            import cv2
            cap = cv2.VideoCapture(str(video_path))
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            frame_idx = 0

            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                if frame_idx % frame_interval == 0:
                    # Save frame temporarily for VLM processing
                    timestamp_sec = frame_idx / fps
                    elements.append(
                        ExtractedElement(
                            element_type=ElementType.FIGURE,
                            text=f"[Video frame at {timestamp_sec:.1f}s]",
                            metadata={
                                "video_path": str(video_path),
                                "frame_index": frame_idx,
                                "timestamp_sec": timestamp_sec,
                                "extraction_method": "video_frame",
                            },
                        )
                    )
                frame_idx += 1
            cap.release()
            logger.info(f"Extracted {len(elements)} frames from {video_path}")
        except Exception as e:
            logger.error(f"Video extraction failed for {video_path}: {e}")
            elements.append(
                ExtractedElement(
                    element_type=ElementType.PARAGRAPH,
                    text=f"[Video: {video_path.name}]",
                    metadata={"error": str(e)},
                )
            )

        return elements

    def extract(
        self,
        file_path: Path,
        document_id: str,
    ) -> ExtractionResult:
        """Extract content from a multi-modal file."""
        suffix = file_path.suffix.lower()

        if suffix in {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}:
            element = self.extract_image(file_path, document_id)
            return ExtractionResult(
                document_id=document_id,
                filename=file_path.name,
                elements=[element],
                raw_text=element.text,
                extraction_method="multimodal_vlm",
            )

        elif suffix in {".mp3", ".wav", ".m4a", ".ogg", ".flac"}:
            element = self.transcribe_audio(file_path, document_id)
            return ExtractionResult(
                document_id=document_id,
                filename=file_path.name,
                elements=[element],
                raw_text=element.text,
                extraction_method="multimodal_whisper",
            )

        elif suffix in {".mp4", ".avi", ".mov", ".mkv", ".webm"}:
            elements = self.extract_video(file_path, document_id)
            raw_text = " ".join(e.text for e in elements)
            return ExtractionResult(
                document_id=document_id,
                filename=file_path.name,
                elements=elements,
                raw_text=raw_text,
                extraction_method="multimodal_video",
            )

        else:
            return ExtractionResult(
                document_id=document_id,
                filename=file_path.name,
                extraction_method="unsupported",
                metadata={"error": f"Unsupported file type: {suffix}"},
            )