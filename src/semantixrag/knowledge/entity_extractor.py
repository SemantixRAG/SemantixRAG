"""Named entity recognition and entity linking for GraphRAG."""
import logging
import re
from typing import Optional
import spacy
from ..models import ExtractedElement

logger = logging.getLogger(__name__)


class EntityExtractor:
    """Extract named entities from text and link to knowledge graph."""

    def __init__(
        self,
        spacy_model: str = "en_core_web_sm",
        confidence_threshold: float = 0.8,
    ):
        self.confidence_threshold = confidence_threshold
        try:
            self.nlp = spacy.load(spacy_model)
        except OSError:
            logger.warning(
                f"Spacy model {spacy_model} not found. "
                f"Install with: python -m spacy download {spacy_model}"
            )
            self.nlp = None

    def extract_from_element(self, element: ExtractedElement) -> list[dict]:
        """Extract entities from a single extracted element."""
        if not self.nlp or not element.text:
            return []

        doc = self.nlp(element.text)
        entities = []

        for ent in doc.ents:
            entities.append({
                "name": ent.text,
                "type": ent.label_,
                "confidence": 0.85,
                "start": ent.start_char,
                "end": ent.end_char,
                "context": element.text[
                    max(0, ent.start_char - 50):ent.end_char + 50
                ],
            })

        return entities

    def extract_batch(self, elements: list[ExtractedElement]) -> list[dict]:
        """Extract entities from a batch of elements."""
        all_entities = []
        for element in elements:
            entities = self.extract_from_element(element)
            all_entities.extend(entities)
        return all_entities

    def extract_from_chunk(self, chunk_text: str) -> list[dict]:
        """Extract entities directly from chunk text."""
        if not self.nlp or not chunk_text:
            return []

        doc = self.nlp(chunk_text)
        entities = []
        for ent in doc.ents:
            entities.append({
                "name": ent.text,
                "type": ent.label_,
                "confidence": 0.85,
                "start": ent.start_char,
                "end": ent.end_char,
            })
        return entities

    def normalize_entity(self, entity: dict) -> str:
        """Normalize entity name for canonical representation."""
        name = entity["name"].lower().strip()
        name = re.sub(r'\s+', ' ', name)
        name = re.sub(r'[^\w\s-]', '', name)
        return name

    def resolve_coreference(self, entities: list[dict]) -> list[dict]:
        """Group entity mentions that refer to the same entity."""
        seen = {}
        resolved = []
        for entity in entities:
            normalized = self.normalize_entity(entity)
            if normalized in seen:
                existing = seen[normalized]
                existing["mentions"] = existing.get("mentions", 1) + 1
                existing["contexts"].append(entity.get("context", ""))
            else:
                entity["mentions"] = 1
                entity["contexts"] = [entity.get("context", "")]
                seen[normalized] = entity
                resolved.append(entity)
        return resolved