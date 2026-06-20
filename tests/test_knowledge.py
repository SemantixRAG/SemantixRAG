"""Tests for GraphRAG knowledge graph integration."""
import pytest
from src.knowledge.entity_extractor import EntityExtractor
from src.knowledge.ontology import OntologyManager
from src.models import ExtractedElement, ElementType


@pytest.fixture
def extractor():
    return EntityExtractor()


@pytest.fixture
def sample_elements():
    return [
        ExtractedElement(
            element_type=ElementType.PARAGRAPH,
            text="Apple Inc. announced a partnership with Microsoft in January 2024. "
                 "Tim Cook, Apple's CEO, met with Satya Nadella.",
        ),
    ]


def test_entity_extraction(extractor, sample_elements):
    entities = extractor.extract_batch(sample_elements)
    if extractor.nlp:
        assert len(entities) > 0
        entity_types = {e["type"] for e in entities}
        assert "ORG" in entity_types
        assert "PERSON" in entity_types
    else:
        assert entities == []


def test_entity_normalization(extractor):
    entities = [
        {"name": "Apple Inc.", "type": "ORG"},
        {"name": "apple", "type": "ORG"},
    ]
    resolved = extractor.resolve_coreference(entities)
    assert len(resolved) == 1  # Should merge


def test_empty_text(extractor):
    elements = [ExtractedElement(element_type=ElementType.PARAGRAPH, text="")]
    entities = extractor.extract_batch(elements)
    assert entities == []


def test_normalize_entity(extractor):
    normalized = extractor.normalize_entity({"name": "Apple Inc.", "type": "ORG"})
    assert normalized == "apple inc."


def test_extract_from_chunk(extractor):
    entities = extractor.extract_from_chunk("John Smith works at Google.")
    if extractor.nlp:
        assert len(entities) > 0
    else:
        assert entities == []


class TestOntologyManager:
    def test_default_ontology(self):
        mgr = OntologyManager()
        schema = mgr.to_schema()
        assert "PERSON" in schema["entity_types"]
        assert "RELATED_TO" in schema["relationship_types"]

    def test_domain_ontology(self):
        mgr = OntologyManager(domain="healthcare")
        schema = mgr.to_schema()
        assert "DISEASE" in schema["entity_types"]

    def test_add_entity_type(self):
        mgr = OntologyManager()
        mgr.add_entity_type("NEW_TYPE")
        assert mgr.is_valid_entity_type("new_type")

    def test_add_relationship_type(self):
        mgr = OntologyManager()
        mgr.add_relationship_type("NEW_REL")
        assert mgr.is_valid_relationship_type("new_rel")

    def test_auto_discovery(self):
        mgr = OntologyManager()
        entities = [{"name": "test", "type": "NEW_DOMAIN_ENTITY"}]
        discovered = mgr.auto_discover_types(entities)
        assert "NEW_DOMAIN_ENTITY" in discovered["entity_types"]