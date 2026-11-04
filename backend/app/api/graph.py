"""
ContextOS Knowledge Graph API Router.

Endpoints for exploring the entity-relationship graph.
"""

import logging

from fastapi import APIRouter, HTTPException, Query

from app.core.database import get_database
from app.models.schemas import (
    EntityDetail,
    EntityResponse,
    GraphData,
    GraphEdge,
    GraphNode,
    RelationshipResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/graph", tags=["graph"])


@router.get("", response_model=GraphData)
async def get_graph(
    entity_type: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
) -> GraphData:
    """Get graph data (entities as nodes, relationships as edges)."""
    db = get_database()

    # Nodes
    where = "WHERE entity_type = ?" if entity_type else ""
    params: list[str | int] = [entity_type] if entity_type else []
    params.append(limit)

    ent_rows = await db.fetch_all(
        f"SELECT * FROM entities {where} ORDER BY mention_count DESC LIMIT ?",
        tuple(params),
    )
    nodes = [
        GraphNode(id=e["id"], label=e["entity_name"], type=e["entity_type"], mention_count=e["mention_count"])
        for e in ent_rows
    ]

    # Also add documents as visible graph nodes
    if not entity_type or entity_type.lower() == "document":
        doc_rows = await db.fetch_all("SELECT id, filename, file_type FROM documents LIMIT 20")
        for d in doc_rows:
            clean_title = d["filename"].replace(".json", "")
            if "_" in clean_title:
                clean_title = clean_title.rsplit("_", 1)[0]
            nodes.append(
                GraphNode(
                    id=d["id"],
                    label=clean_title[:35],
                    type="Document",
                    mention_count=2,
                )
            )

    node_ids = {n.id for n in nodes}

    # Edges between visible nodes
    if not node_ids:
        return GraphData(nodes=[], edges=[])

    placeholders = ",".join(["?"] * len(node_ids))
    rel_rows = await db.fetch_all(
        f"""SELECT r.*, se.entity_name as subject_name, oe.entity_name as object_name
            FROM relationships r
            JOIN entities se ON r.subject_entity_id = se.id
            JOIN entities oe ON r.object_entity_id = oe.id
            WHERE r.subject_entity_id IN ({placeholders})
              AND r.object_entity_id IN ({placeholders})""",
        tuple(list(node_ids) + list(node_ids)),
    )
    edges = [
        GraphEdge(
            id=r["id"],
            source=r["subject_entity_id"],
            target=r["object_entity_id"],
            label=r["predicate"],
            confidence=r["confidence"],
        )
        for r in rel_rows
    ]

    # Connect entities to documents if not already connected
    seen_edges = {(e.source, e.target) for e in edges}
    doc_node_ids = {n.id for n in nodes if n.type == "Document"}
    entity_nodes = [n for n in nodes if n.type != "Document"]

    for doc_id in doc_node_ids:
        for ent in entity_nodes:
            pair = (ent.id, doc_id)
            if pair not in seen_edges:
                edges.append(
                    GraphEdge(
                        id=f"edge_{ent.id}_{doc_id[:8]}",
                        source=ent.id,
                        target=doc_id,
                        label="Mentioned In",
                        confidence=0.9,
                    )
                )
                seen_edges.add(pair)

    return GraphData(nodes=nodes, edges=edges)


@router.get("/entity/{entity_id}", response_model=EntityDetail)
async def get_entity(entity_id: str) -> EntityDetail:
    """Get an entity with all its relationships."""
    db = get_database()
    row = await db.fetch_one("SELECT * FROM entities WHERE id = ?", (entity_id,))
    if not row:
        raise HTTPException(status_code=404, detail="Entity not found")

    rel_rows = await db.fetch_all(
        """SELECT r.*, se.entity_name as subject_name, oe.entity_name as object_name
           FROM relationships r
           JOIN entities se ON r.subject_entity_id = se.id
           JOIN entities oe ON r.object_entity_id = oe.id
           WHERE r.subject_entity_id = ? OR r.object_entity_id = ?""",
        (entity_id, entity_id),
    )
    relationships = [RelationshipResponse(**r) for r in rel_rows]
    return EntityDetail(**row, relationships=relationships)


@router.get("/stats")
async def graph_stats() -> dict:
    """Return graph-level statistics."""
    db = get_database()
    entities_count = await db.fetch_one("SELECT COUNT(*) as cnt FROM entities")
    rels_count = await db.fetch_one("SELECT COUNT(*) as cnt FROM relationships")
    type_rows = await db.fetch_all(
        "SELECT entity_type, COUNT(*) as cnt FROM entities GROUP BY entity_type ORDER BY cnt DESC"
    )

    return {
        "total_entities": entities_count["cnt"] if entities_count else 0,
        "total_relationships": rels_count["cnt"] if rels_count else 0,
        "entity_types": {r["entity_type"]: r["cnt"] for r in type_rows},
    }


@router.get("/node/{node_id}")
async def get_node_detail(node_id: str) -> dict:
    """Get rich details for any graph node (Entity or Document), including memories and connections."""
    db = get_database()

    # 1. Check if node is an Entity
    ent_row = await db.fetch_one("SELECT * FROM entities WHERE id = ?", (node_id,))
    if ent_row:
        ent_name = ent_row["entity_name"]
        # Find memories mentioning this entity
        mem_rows = await db.fetch_all(
            "SELECT id, document_id, content, timestamp, summary FROM memories WHERE content LIKE ? LIMIT 10",
            (f"%{ent_name}%",),
        )

        # Find relationships
        rel_rows = await db.fetch_all(
            """SELECT r.*, se.entity_name as subject_name, oe.entity_name as object_name
               FROM relationships r
               JOIN entities se ON r.subject_entity_id = se.id
               JOIN entities oe ON r.object_entity_id = oe.id
               WHERE r.subject_entity_id = ? OR r.object_entity_id = ?""",
            (node_id, node_id),
        )

        connections = []
        for r in rel_rows:
            target_id = r["object_entity_id"] if r["subject_entity_id"] == node_id else r["subject_entity_id"]
            target_name = r["object_name"] if r["subject_entity_id"] == node_id else r["subject_name"]
            connections.append({
                "id": target_id,
                "label": target_name,
                "relationship": r["predicate"],
                "type": "Concept",
            })

        # Add documents that contain this entity as connections
        doc_ids = list({m["document_id"] for m in mem_rows if m.get("document_id")})
        if doc_ids:
            placeholders = ",".join(["?"] * len(doc_ids))
            docs = await db.fetch_all(
                f"SELECT id, filename, file_type FROM documents WHERE id IN ({placeholders})",
                tuple(doc_ids),
            )
            for d in docs:
                connections.append({
                    "id": d["id"],
                    "label": d["filename"].replace(".json", ""),
                    "relationship": "Mentioned In",
                    "type": "Document",
                })

        return {
            "id": ent_row["id"],
            "label": ent_name,
            "type": ent_row["entity_type"],
            "mention_count": ent_row["mention_count"],
            "first_seen": ent_row.get("first_seen"),
            "last_seen": ent_row.get("last_seen"),
            "memories": [
                {
                    "id": m["id"],
                    "content": m["content"],
                    "timestamp": m["timestamp"],
                    "summary": m.get("summary"),
                }
                for m in mem_rows
            ],
            "connections": connections,
        }

    # 2. Check if node is a Document
    doc_row = await db.fetch_one("SELECT * FROM documents WHERE id = ?", (node_id,))
    if doc_row:
        mem_rows = await db.fetch_all(
            "SELECT id, content, timestamp, summary FROM memories WHERE document_id = ? ORDER BY timestamp",
            (node_id,),
        )

        # Find entities mentioned in this document's memories
        connections = []
        all_text = " ".join(m["content"] for m in mem_rows)
        all_ents = await db.fetch_all("SELECT id, entity_name, entity_type FROM entities LIMIT 50")
        for e in all_ents:
            if e["entity_name"].lower() in all_text.lower():
                connections.append({
                    "id": e["id"],
                    "label": e["entity_name"],
                    "relationship": "Contains Mention",
                    "type": e["entity_type"],
                })

        clean_name = doc_row["filename"].replace(".json", "")
        if "_" in clean_name:
            clean_name = clean_name.rsplit("_", 1)[0]

        return {
            "id": doc_row["id"],
            "label": clean_name,
            "type": "Document",
            "file_type": doc_row.get("file_type", "Document"),
            "original_path": doc_row.get("original_path", ""),
            "created_at": doc_row.get("created_at"),
            "mention_count": len(mem_rows),
            "memories": [
                {
                    "id": m["id"],
                    "content": m["content"],
                    "timestamp": m["timestamp"],
                    "summary": m.get("summary"),
                }
                for m in mem_rows
            ],
            "connections": connections,
        }

    raise HTTPException(status_code=404, detail="Graph node not found")
