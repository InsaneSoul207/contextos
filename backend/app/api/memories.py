"""
ContextOS Memories API Router.

Endpoints for listing, inspecting, and deleting memories.
"""

import logging
from uuid import uuid4
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query

from app.core.database import get_database
from app.models.schemas import (
    MemoryCreate,
    MemoryDetail,
    MemoryResponse,
    EntityResponse,
    RelationshipResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/memories", tags=["memories"])


@router.get("", response_model=list[MemoryResponse])
async def list_memories(
    limit: int = Query(default=50, ge=1, le=5000),
    per_page: int | None = Query(default=None),
    offset: int = Query(default=0, ge=0),
    page: int | None = Query(default=None),
    memory_type: str | None = Query(default=None),
    document_id: str | None = Query(default=None),
) -> list[MemoryResponse]:
    """List memories with flexible pagination (supporting limit/per_page and offset/page)."""
    db = get_database()
    where_clauses: list[str] = []
    params: list[str | int] = []

    actual_limit = per_page if per_page is not None else limit
    if page is not None and page > 0:
        actual_offset = (page - 1) * actual_limit
    else:
        actual_offset = offset

    if memory_type:
        where_clauses.append("memory_type = ?")
        params.append(memory_type)
    if document_id:
        where_clauses.append("document_id = ?")
        params.append(document_id)

    where_sql = (" WHERE " + " AND ".join(where_clauses)) if where_clauses else ""
    params.extend([actual_limit, actual_offset])

    rows = await db.fetch_all(
        f"""SELECT m.*, d.filename as title, d.file_type, d.original_path as filepath
            FROM memories m
            LEFT JOIN documents d ON m.document_id = d.id
            {where_sql}
            ORDER BY m.created_at DESC LIMIT ? OFFSET ?""",
        tuple(params),
    )
    return [MemoryResponse(**r) for r in rows]


@router.get("/{memory_id}", response_model=MemoryDetail)
async def get_memory(memory_id: str) -> MemoryDetail:
    """Get full memory detail with related entities and source info."""
    db = get_database()
    row = await db.fetch_one("SELECT * FROM memories WHERE id = ?", (memory_id,))
    if not row:
        raise HTTPException(status_code=404, detail="Memory not found")

    # Get document and source info
    doc = await db.fetch_one(
        "SELECT filename, source_id FROM documents WHERE id = ?", (row["document_id"],)
    )
    doc_filename = doc["filename"] if doc else None
    source_name = None
    if doc:
        source = await db.fetch_one(
            "SELECT display_name FROM sources WHERE id = ?", (doc["source_id"],)
        )
        source_name = source["display_name"] if source else None

    # Get related entities via relationships
    rel_rows = await db.fetch_all(
        """SELECT r.*, 
                  se.entity_name as subject_name, 
                  oe.entity_name as object_name
           FROM relationships r
           JOIN entities se ON r.subject_entity_id = se.id
           JOIN entities oe ON r.object_entity_id = oe.id
           WHERE r.source_memory_id = ?""",
        (memory_id,),
    )
    relationships = [RelationshipResponse(**r) for r in rel_rows]

    # Collect unique entity IDs
    entity_ids: set[str] = set()
    for r in rel_rows:
        entity_ids.add(r["subject_entity_id"])
        entity_ids.add(r["object_entity_id"])

    entities: list[EntityResponse] = []
    for eid in entity_ids:
        ent = await db.fetch_one("SELECT * FROM entities WHERE id = ?", (eid,))
        if ent:
            entities.append(EntityResponse(**ent))

    return MemoryDetail(
        **row,
        document_filename=doc_filename,
        source_name=source_name,
        entities=entities,
        relationships=relationships,
    )


@router.post("", response_model=MemoryResponse, status_code=201)
async def create_memory(body: MemoryCreate) -> MemoryResponse:
    """Manually create a memory record."""
    db = get_database()

    doc = await db.fetch_one("SELECT id FROM documents WHERE id = ?", (body.document_id,))
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    memory_id = str(uuid4())
    now = datetime.now(timezone.utc).isoformat()

    await db.execute(
        """INSERT INTO memories (id, document_id, memory_type, content, summary, timestamp, confidence, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (memory_id, body.document_id, body.memory_type, body.content, body.summary, now, body.confidence, now),
    )
    await db.commit()

    return MemoryResponse(
        id=memory_id,
        document_id=body.document_id,
        memory_type=body.memory_type,
        content=body.content,
        summary=body.summary,
        timestamp=now,
        confidence=body.confidence,
        created_at=now,
    )


@router.delete("/{memory_id}", status_code=204)
async def delete_memory(memory_id: str) -> None:
    """Delete a memory."""
    db = get_database()
    row = await db.fetch_one("SELECT * FROM memories WHERE id = ?", (memory_id,))
    if not row:
        raise HTTPException(status_code=404, detail="Memory not found")
    await db.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
    await db.commit()
    logger.info("Memory deleted: %s", memory_id)


@router.get("/{memory_id}/related", response_model=list[MemoryResponse])
async def get_related_memories(
    memory_id: str,
    limit: int = Query(default=10, ge=1, le=50),
) -> list[MemoryResponse]:
    """Get memories related to this one via the knowledge graph."""
    db = get_database()
    row = await db.fetch_one("SELECT * FROM memories WHERE id = ?", (memory_id,))
    if not row:
        raise HTTPException(status_code=404, detail="Memory not found")

    # Find entities linked to this memory
    rel_rows = await db.fetch_all(
        """SELECT DISTINCT subject_entity_id, object_entity_id
           FROM relationships WHERE source_memory_id = ?""",
        (memory_id,),
    )
    entity_ids: set[str] = set()
    for r in rel_rows:
        entity_ids.add(r["subject_entity_id"])
        entity_ids.add(r["object_entity_id"])

    if not entity_ids:
        return []

    # Find other memories that share these entities
    placeholders = ",".join(["?"] * len(entity_ids))
    related_rows = await db.fetch_all(
        f"""SELECT DISTINCT m.* FROM memories m
            JOIN relationships r ON r.source_memory_id = m.id
            WHERE (r.subject_entity_id IN ({placeholders})
                   OR r.object_entity_id IN ({placeholders}))
              AND m.id != ?
            LIMIT ?""",
        tuple(list(entity_ids) + list(entity_ids) + [memory_id, limit]),
    )
    return [MemoryResponse(**r) for r in related_rows]
