"""
ContextOS Collections API Router.

Provides endpoints for creating, managing, and browsing custom and smart memory collections.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.core.database import get_database

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/collections", tags=["collections"])


class CollectionCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    color: Optional[str] = "#6366f1"
    icon: Optional[str] = "folder"


class CollectionUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    color: Optional[str] = None
    icon: Optional[str] = None


class AddMemoryRequest(BaseModel):
    memory_id: str


@router.get("")
async def list_collections() -> list[dict[str, Any]]:
    """List all user collections along with smart auto-generated source collections."""
    db = get_database()

    # 1. Fetch custom collections from database
    custom_rows = await db.fetch_all(
        "SELECT * FROM collections ORDER BY updated_at DESC"
    )

    collections: list[dict[str, Any]] = []
    for row in custom_rows:
        c_dict = dict(row)
        # Count items
        count_row = await db.fetch_one(
            "SELECT COUNT(*) as cnt FROM collection_items WHERE collection_id = ?",
            (c_dict["id"],),
        )
        c_dict["item_count"] = count_row["cnt"] if count_row else 0
        c_dict["is_smart"] = False
        collections.append(c_dict)

    # 2. Add smart collections derived from active monitored sources
    sources = await db.fetch_all("SELECT * FROM sources WHERE status != 'deleted'")
    for s in sources:
        # Count memories for this source
        mem_count_row = await db.fetch_one(
            """
            SELECT COUNT(m.id) as cnt
            FROM memories m
            JOIN documents d ON m.document_id = d.id
            WHERE d.source_id = ?
            """,
            (s["id"],),
        )
        mem_count = mem_count_row["cnt"] if mem_count_row else 0

        # Colors & icons based on source_type
        type_colors = {
            "projects": "#3b82f6",
            "research": "#8b5cf6",
            "documents": "#10b981",
            "notes": "#f59e0b",
            "quick_capture": "#ec4899",
            "extension": "#06b6d4",
        }
        color = type_colors.get(s["source_type"], "#6366f1")

        collections.append({
            "id": f"smart-source-{s['id']}",
            "name": s["display_name"],
            "description": f"Auto-curated collection for {s['display_name']} ({s['source_path']})",
            "color": color,
            "icon": "folder",
            "item_count": mem_count,
            "is_smart": True,
            "source_id": s["id"],
            "created_at": s["created_at"],
            "updated_at": s["created_at"],
        })

    return collections


@router.post("", status_code=201)
async def create_collection(body: CollectionCreate) -> dict[str, Any]:
    """Create a new custom memory collection."""
    db = get_database()
    col_id = str(uuid4())
    now = datetime.now(timezone.utc).isoformat()

    await db.execute(
        """
        INSERT INTO collections (id, name, description, color, icon, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (col_id, body.name.strip(), body.description, body.color, body.icon, now, now),
    )
    await db.commit()

    return {
        "id": col_id,
        "name": body.name.strip(),
        "description": body.description,
        "color": body.color,
        "icon": body.icon,
        "item_count": 0,
        "is_smart": False,
        "created_at": now,
        "updated_at": now,
    }


@router.get("/{collection_id}")
async def get_collection(collection_id: str) -> dict[str, Any]:
    """Get collection details and all its member memories."""
    db = get_database()

    # Check if smart collection
    if collection_id.startswith("smart-source-"):
        source_id = collection_id.replace("smart-source-", "")
        source = await db.fetch_one("SELECT * FROM sources WHERE id = ?", (source_id,))
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")

        # Get memories for this source
        mem_rows = await db.fetch_all(
            """
            SELECT m.id, m.document_id, m.memory_type, m.content, m.summary, m.timestamp, m.confidence, m.created_at,
                   d.filename as document_filename, d.original_path as filepath
            FROM memories m
            JOIN documents d ON m.document_id = d.id
            WHERE d.source_id = ?
            ORDER BY m.created_at DESC
            LIMIT 100
            """,
            (source_id,),
        )
        return {
            "id": collection_id,
            "name": source["display_name"],
            "description": f"Auto-curated collection for {source['display_name']}",
            "color": "#6366f1",
            "icon": "folder",
            "is_smart": True,
            "source_id": source_id,
            "item_count": len(mem_rows),
            "memories": [dict(r) for r in mem_rows],
            "created_at": source["created_at"],
            "updated_at": source["created_at"],
        }

    # Custom collection
    col = await db.fetch_one("SELECT * FROM collections WHERE id = ?", (collection_id,))
    if not col:
        raise HTTPException(status_code=404, detail="Collection not found")

    col_dict = dict(col)
    mem_rows = await db.fetch_all(
        """
        SELECT m.id, m.document_id, m.memory_type, m.content, m.summary, m.timestamp, m.confidence, m.created_at,
               d.filename as document_filename, d.original_path as filepath,
               ci.added_at
        FROM collection_items ci
        JOIN memories m ON ci.memory_id = m.id
        LEFT JOIN documents d ON m.document_id = d.id
        WHERE ci.collection_id = ?
        ORDER BY ci.added_at DESC
        """,
        (collection_id,),
    )
    col_dict["is_smart"] = False
    col_dict["item_count"] = len(mem_rows)
    col_dict["memories"] = [dict(r) for r in mem_rows]
    return col_dict


@router.post("/{collection_id}/memories", status_code=201)
async def add_memory_to_collection(
    collection_id: str, body: AddMemoryRequest
) -> dict[str, str]:
    """Add a memory into a custom collection."""
    if collection_id.startswith("smart-source-"):
        raise HTTPException(status_code=400, detail="Cannot manually add to a smart auto-collection")

    db = get_database()
    col = await db.fetch_one("SELECT id FROM collections WHERE id = ?", (collection_id,))
    if not col:
        raise HTTPException(status_code=404, detail="Collection not found")

    now = datetime.now(timezone.utc).isoformat()
    item_id = str(uuid4())

    try:
        await db.execute(
            """
            INSERT OR IGNORE INTO collection_items (id, collection_id, memory_id, added_at)
            VALUES (?, ?, ?, ?)
            """,
            (item_id, collection_id, body.memory_id, now),
        )
        await db.execute(
            "UPDATE collections SET updated_at = ? WHERE id = ?",
            (now, collection_id),
        )
        await db.commit()
    except Exception as e:
        logger.error("Failed to add memory to collection: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

    return {"status": "added", "collection_id": collection_id, "memory_id": body.memory_id}


@router.delete("/{collection_id}/memories/{memory_id}")
async def remove_memory_from_collection(
    collection_id: str, memory_id: str
) -> dict[str, str]:
    """Remove a memory from a custom collection."""
    if collection_id.startswith("smart-source-"):
        raise HTTPException(status_code=400, detail="Cannot delete from smart auto-collection")

    db = get_database()
    await db.execute(
        "DELETE FROM collection_items WHERE collection_id = ? AND memory_id = ?",
        (collection_id, memory_id),
    )
    await db.commit()
    return {"status": "removed", "collection_id": collection_id, "memory_id": memory_id}


@router.delete("/{collection_id}", status_code=200)
async def delete_collection(collection_id: str) -> dict[str, str]:
    """Delete a custom collection."""
    if collection_id.startswith("smart-source-"):
        raise HTTPException(status_code=400, detail="Cannot delete a smart auto-collection")

    db = get_database()
    await db.execute("DELETE FROM collection_items WHERE collection_id = ?", (collection_id,))
    await db.execute("DELETE FROM collections WHERE id = ?", (collection_id,))
    await db.commit()
    return {"status": "deleted", "collection_id": collection_id}
