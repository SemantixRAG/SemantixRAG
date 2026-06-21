"""Ontology management for knowledge graph schema."""
import logging
from typing import Optional

logger = logging.getLogger(__name__)


ONTOLOGY_TEMPLATES = {
    "general": {
        "entity_types": [
            "PERSON", "ORG", "GPE", "LOC", "PRODUCT", "EVENT",
            "DATE", "MONEY", "PERCENT", "LAW", "FAC", "WORK_OF_ART",
        ],
        "relationship_types": [
            "RELATED_TO", "MENTIONS", "PART_OF", "LOCATED_IN",
            "EMPLOYED_BY", "FOUNDED_BY", "ACQUIRED", "PARTNERED_WITH",
        ],
    },
    "healthcare": {
        "entity_types": [
            "PERSON", "ORG", "DISEASE", "SYMPTOM", "MEDICATION",
            "TREATMENT", "DIAGNOSTIC_PROCEDURE", "ANATOMY",
        ],
        "relationship_types": [
            "TREATS", "CAUSES", "DIAGNOSES", "CONTRANDICATES",
            "SIDE_EFFECT_OF", "RELATED_TO",
        ],
    },
    "legal": {
        "entity_types": [
            "PERSON", "ORG", "GPE", "LAW", "REGULATION", "CASE",
            "CONTRACT_TERM", "OBLIGATION", "RIGHT",
        ],
        "relationship_types": [
            "GOVERNS", "REGULATES", "CITES", "AMENDS", "REPEALS",
            "CONTRADICTS", "COMPLIES_WITH",
        ],
    },
    "finance": {
        "entity_types": [
            "PERSON", "ORG", "MONEY", "PERCENT", "DATE",
            "FINANCIAL_INSTRUMENT", "METRIC", "PRODUCT",
        ],
        "relationship_types": [
            "INVESTED_IN", "ACQUIRED", "MERGER", "REPORTS",
            "OWNS", "TRADES", "REGULATES",
        ],
    },
}


class OntologyManager:
    """Manage knowledge graph entity/relationship type schemas."""

    def __init__(self, domain: str = "general"):
        self.domain = domain
        self.entity_types = set(ONTOLOGY_TEMPLATES.get(domain, ONTOLOGY_TEMPLATES["general"])["entity_types"])
        self.relationship_types = set(ONTOLOGY_TEMPLATES.get(domain, ONTOLOGY_TEMPLATES["general"])["relationship_types"])

    def add_entity_type(self, entity_type: str):
        """Add a new entity type to the ontology."""
        self.entity_types.add(entity_type.upper())
        logger.debug(f"Added entity type: {entity_type}")

    def add_relationship_type(self, rel_type: str):
        """Add a new relationship type to the ontology."""
        self.relationship_types.add(rel_type.upper())
        logger.debug(f"Added relationship type: {rel_type}")

    def is_valid_entity_type(self, entity_type: str) -> bool:
        """Check if entity type is in the ontology."""
        return entity_type.upper() in self.entity_types

    def is_valid_relationship_type(self, rel_type: str) -> bool:
        """Check if relationship type is in the ontology."""
        return rel_type.upper() in self.relationship_types

    def auto_discover_types(self, entities: list[dict]) -> dict:
        """Automatically discover new entity types from extracted entities."""
        discovered = {
            "entity_types": set(),
            "relationship_types": set(),
        }
        for entity in entities:
            ent_type = entity.get("type", "").upper()
            if ent_type and ent_type not in self.entity_types:
                discovered["entity_types"].add(ent_type)

        return {
            "entity_types": list(discovered["entity_types"]),
            "relationship_types": list(discovered["relationship_types"]),
        }

    def to_schema(self) -> dict:
        """Return the full ontology schema."""
        return {
            "domain": self.domain,
            "entity_types": sorted(self.entity_types),
            "relationship_types": sorted(self.relationship_types),
        }