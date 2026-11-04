"""
ContextOS Knowledge Graph Manager.

Provides entity insertion/upsert, relationship linking with provenance,
temporal tracking, and multi-hop graph traversal.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Any, Optional

from app.core.database import get_database

logger = logging.getLogger(__name__)


class KnowledgeGraphManager:
    """Manages knowledge graph nodes (entities) and edges (relationships) in SQLite."""

    def __init__(self) -> None:
        self.db = get_database()

    async def upsert_entity(self, name: str, entity_type: str) -> str:
        """Insert entity or increment mention count if already exists."""
        clean_name = name.strip()
        now = datetime.now().isoformat()

        row = await self.db.fetch_one(
            "SELECT id, mention_count FROM entities WHERE LOWER(entity_name) = LOWER(?)",
            (clean_name,),
        )
        if row:
            ent_id = row["id"]
            await self.db.execute(
                "UPDATE entities SET mention_count = mention_count + 1, last_seen = ? WHERE id = ?",
                (now, ent_id),
            )
            await self.db.commit()
            return ent_id

        ent_id = str(uuid.uuid4())
        await self.db.execute(
            """INSERT INTO entities (id, entity_name, entity_type, first_seen, last_seen, mention_count)
               VALUES (?, ?, ?, ?, ?, 1)""",
            (ent_id, clean_name, entity_type, now, now),
        )
        await self.db.commit()
        return ent_id

    async def add_relationship(
        self,
        subject_id: str,
        predicate: str,
        object_id: str,
        source_memory_id: Optional[str] = None,
        confidence: float = 1.0,
        valid_from: Optional[str] = None,
        valid_to: Optional[str] = None,
    ) -> str:
        """Add a directed relationship between two entities."""
        # Avoid self-referencing redundant relationships
        if subject_id == object_id:
            return ""

        # Check if already exists
        existing = await self.db.fetch_one(
            """SELECT id FROM relationships
               WHERE subject_entity_id = ? AND predicate = ? AND object_entity_id = ?""",
            (subject_id, predicate, object_id),
        )
        if existing:
            return existing["id"]

        rel_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        await self.db.execute(
            """INSERT INTO relationships
               (id, subject_entity_id, predicate, object_entity_id, source_memory_id, confidence, valid_from, valid_to, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                rel_id,
                subject_id,
                predicate,
                object_id,
                source_memory_id,
                confidence,
                valid_from,
                valid_to,
                now,
            ),
        )
        await self.db.commit()
        return rel_id

    async def get_related_entities(self, entity_id: str, max_hops: int = 2) -> list[dict[str, Any]]:
        """Breadth-first traversal up to max_hops from an entity."""
        visited: set[str] = {entity_id}
        queue: list[tuple[str, int]] = [(entity_id, 0)]
        results: list[dict[str, Any]] = []

        while queue:
            curr_id, depth = queue.pop(0)
            if depth >= max_hops:
                continue

            rows = await self.db.fetch_all(
                """SELECT r.predicate, r.confidence,
                          e.id as target_id, e.entity_name as target_name, e.entity_type as target_type
                   FROM relationships r
                   JOIN entities e ON (r.object_entity_id = e.id OR r.subject_entity_id = e.id)
                   WHERE (r.subject_entity_id = ? OR r.object_entity_id = ?) AND e.id != ?""",
                (curr_id, curr_id, curr_id),
            )

            for row in rows:
                target_id = row["target_id"]
                results.append(dict(row))
                if target_id not in visited:
                    visited.add(target_id)
                    queue.append((target_id, depth + 1))

        return results
