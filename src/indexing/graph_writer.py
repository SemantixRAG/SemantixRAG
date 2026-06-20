"""Neo4j graph writer for knowledge graph integration."""
import logging
from typing import Optional
from neo4j import AsyncGraphDatabase
from ..models import Chunk

logger = logging.getLogger(__name__)


class GraphWriter:
    """Write entities and relationships to Neo4j knowledge graph."""

    def __init__(
        self,
        uri: str,
        user: str,
        password: str,
        database: str = "rag",
    ):
        self.uri = uri
        self.user = user
        self.password = password
        self.database = database
        self._driver = None

    async def connect(self):
        """Initialize Neo4j driver."""
        if not self._driver:
            self._driver = AsyncGraphDatabase.driver(
                self.uri,
                auth=(self.user, self.password),
            )
            logger.info(f"Connected to Neo4j at {self.uri}")

    async def close(self):
        """Close Neo4j driver."""
        if self._driver:
            await self._driver.close()
            self._driver = None

    async def create_constraints(self):
        """Create unique constraints and indexes."""
        queries = [
            "CREATE CONSTRAINT entity_id_unique IF NOT EXISTS "
            "FOR (e:Entity) REQUIRE e.entity_id IS UNIQUE",
            "CREATE INDEX entity_type_index IF NOT EXISTS "
            "FOR (e:Entity) ON (e.entity_type)",
            "CREATE INDEX entity_tenant_index IF NOT EXISTS "
            "FOR (e:Entity) ON (e.tenant_id)",
            "CREATE INDEX chunk_id_index IF NOT EXISTS "
            "FOR (c:Chunk) ON (c.chunk_id)",
        ]
        async with self._driver.session(database=self.database) as session:
            for query in queries:
                try:
                    await session.run(query)
                    logger.debug(f"Created constraint/index: {query[:50]}...")
                except Exception as e:
                    logger.warning(f"Failed to create constraint: {e}")

    async def write_chunk(self, chunk: Chunk, tenant_id: str):
        """Write a chunk node to the graph."""
        query = """
        MERGE (c:Chunk {chunk_id: $chunk_id})
        SET c.document_id = $document_id,
            c.chunk_text = $chunk_text,
            c.header_path = $header_path,
            c.tenant_id = $tenant_id,
            c.indexed_at = datetime()
        """
        async with self._driver.session(database=self.database) as session:
            await session.run(query, {
                "chunk_id": chunk.chunk_id,
                "document_id": chunk.document_id,
                "chunk_text": chunk.chunk_text[:1000],
                "header_path": chunk.header_path,
                "tenant_id": tenant_id,
            })

    async def write_entities(
        self,
        entities: list[dict],
        chunk_id: str,
        tenant_id: str,
    ):
        """Write extracted entities and link to chunk."""
        entity_query = """
        MERGE (e:Entity {name: $name, entity_type: $type, tenant_id: $tenant_id})
        ON CREATE SET e.entity_id = randomUUID(), e.created_at = datetime()
        ON MATCH SET e.last_seen = datetime(), e.mentions = coalesce(e.mentions, 0) + 1
        MERGE (c:Chunk {chunk_id: $chunk_id})
        MERGE (c)-[r:MENTIONS {confidence: $confidence}]->(e)
        SET r.tenant_id = $tenant_id, r.mentioned_at = datetime()
        """
        async with self._driver.session(database=self.database) as session:
            for entity in entities:
                if entity.get("confidence", 0) < 0.8:
                    continue
                try:
                    await session.run(entity_query, {
                        "name": entity["name"],
                        "type": entity["type"],
                        "confidence": entity.get("confidence", 0.8),
                        "chunk_id": chunk_id,
                        "tenant_id": tenant_id,
                    })
                except Exception as e:
                    logger.error(f"Failed to write entity {entity}: {e}")

    async def write_relationships(
        self,
        relationships: list[dict],
        tenant_id: str,
    ):
        """Write entity-to-entity relationships."""
        rel_query = """
        MERGE (e1:Entity {name: $entity_1, tenant_id: $tenant_id})
        MERGE (e2:Entity {name: $entity_2, tenant_id: $tenant_id})
        MERGE (e1)-[r:RELATED_TO {
            relationship_type: $rel_type,
            confidence: $confidence
        }]->(e2)
        SET r.context = $context,
            r.source_document_id = $doc_id,
            r.created_at = datetime()
        """
        async with self._driver.session(database=self.database) as session:
            for rel in relationships:
                try:
                    await session.run(rel_query, {
                        "entity_1": rel["entity_1"],
                        "entity_2": rel["entity_2"],
                        "rel_type": rel.get("relationship_type", "RELATED_TO"),
                        "confidence": rel.get("confidence", 0.8),
                        "context": rel.get("context", "")[:500],
                        "doc_id": rel.get("document_id", ""),
                        "tenant_id": tenant_id,
                    })
                except Exception as e:
                    logger.error(f"Failed to write relationship {rel}: {e}")

    async def delete_document_graph(self, document_id: str, tenant_id: str):
        """Delete all graph nodes/relationships for a document."""
        query = """
        MATCH (c:Chunk {document_id: $document_id, tenant_id: $tenant_id})
        OPTIONAL MATCH (c)-[r:MENTIONS]->(e:Entity)
        DELETE r, c
        WITH e
        WHERE NOT EXISTS { (chunk:Chunk)-[:MENTIONS]->(e) }
        DELETE e
        """
        async with self._driver.session(database=self.database) as session:
            await session.run(
                query,
                {"document_id": document_id, "tenant_id": tenant_id},
            )
            logger.info(f"Deleted graph data for document {document_id}")

    async def search_related_entities(
        self,
        entity_names: list[str],
        hops: int = 2,
        tenant_id: str = "default",
        limit: int = 50,
    ) -> list[dict]:
        """Find entities and related chunks via graph traversal."""
        query = """
        MATCH (start:Entity {tenant_id: $tenant_id})
        WHERE start.name IN $entity_names
        MATCH path = (start)-[*1..$hops]-(related:Entity)
        MATCH (related)<-[:MENTIONS]-(c:Chunk {tenant_id: $tenant_id})
        WITH related, c, length(path) AS distance
        ORDER BY distance, related.mentions DESC
        RETURN DISTINCT
            related.name AS entity_name,
            related.entity_type AS entity_type,
            c.chunk_id AS chunk_id,
            distance,
            related.mentions AS mention_count
        LIMIT $limit
        """
        results = []
        async with self._driver.session(database=self.database) as session:
            cursor = await session.run(query, {
                "entity_names": entity_names,
                "hops": hops,
                "tenant_id": tenant_id,
                "limit": limit,
            })
            async for record in cursor:
                results.append(dict(record))
        return results