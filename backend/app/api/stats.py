"""
ContextOS Stats / Dashboard API Router.

Provides aggregate statistics and activity timelines for the frontend dashboard.
"""

import logging

from fastapi import APIRouter, Query

from app.core.database import get_database
from app.models.schemas import DocumentResponse, StatsResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/stats", tags=["stats"])


@router.get("", response_model=StatsResponse)
async def get_stats() -> StatsResponse:
    """Return dashboard statistics."""
    db = get_database()

    mem = await db.fetch_one("SELECT COUNT(*) as cnt FROM memories")
    doc = await db.fetch_one("SELECT COUNT(*) as cnt FROM documents")
    ent = await db.fetch_one("SELECT COUNT(*) as cnt FROM entities")
    rel = await db.fetch_one("SELECT COUNT(*) as cnt FROM relationships")
    src = await db.fetch_one("SELECT COUNT(*) as cnt FROM sources")
    queue = await db.fetch_one(
        "SELECT COUNT(*) as cnt FROM processing_jobs WHERE status IN ('queued', 'running')"
    )

    recent = await db.fetch_all(
        "SELECT * FROM documents ORDER BY created_at DESC LIMIT 10"
    )

    return StatsResponse(
        total_memories=mem["cnt"] if mem else 0,
        total_documents=doc["cnt"] if doc else 0,
        total_entities=ent["cnt"] if ent else 0,
        total_relationships=rel["cnt"] if rel else 0,
        total_sources=src["cnt"] if src else 0,
        recent_documents=[DocumentResponse(**r) for r in recent],
        processing_queue_size=queue["cnt"] if queue else 0,
    )


@router.get("/activity")
async def get_activity(limit: int = Query(default=20, ge=1, le=100)) -> list[dict]:
    """Return recent processing activity."""
    db = get_database()
    rows = await db.fetch_all(
        """SELECT pj.*, d.filename
           FROM processing_jobs pj
           LEFT JOIN documents d ON pj.document_id = d.id
           ORDER BY pj.created_at DESC
           LIMIT ?""",
        (limit,),
    )
    return rows


@router.get("/daily-digest")
async def get_daily_digest() -> dict:
    """Return executive daily memory digest synthesizing today's knowledge."""
    db = get_database()
    from datetime import datetime, timezone

    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Memories added today
    today_mems = await db.fetch_all(
        """SELECT m.content, m.summary, m.memory_type, d.filename, s.display_name as source_name
           FROM memories m
           JOIN documents d ON m.document_id = d.id
           JOIN sources s ON d.source_id = s.id
           WHERE DATE(m.created_at) = DATE('now') OR DATE(m.created_at) = ?
           ORDER BY m.created_at DESC
           LIMIT 20""",
        (today_str,),
    )

    # If few memories today, get recent memories to provide a meaningful digest
    if not today_mems:
        today_mems = await db.fetch_all(
            """SELECT m.content, m.summary, m.memory_type, d.filename, s.display_name as source_name
               FROM memories m
               JOIN documents d ON m.document_id = d.id
               JOIN sources s ON d.source_id = s.id
               ORDER BY m.created_at DESC
               LIMIT 10"""
        )

    # Top entities
    top_entities = await db.fetch_all(
        "SELECT entity_name, entity_type FROM entities ORDER BY mention_count DESC LIMIT 5"
    )

    doc_count = await db.fetch_one("SELECT COUNT(*) as cnt FROM documents")
    mem_count = await db.fetch_one("SELECT COUNT(*) as cnt FROM memories")

    entity_names = [e["entity_name"] for e in top_entities]
    entity_str = ", ".join(entity_names[:3]) if entity_names else "Transformers & Deep Learning"

    # Synthesize digest text
    if today_mems:
        filenames = list({m["filename"] for m in today_mems if m.get("filename")})
        sources = list({m["source_name"] for m in today_mems if m.get("source_name")})
        files_str = ", ".join(filenames[:2])

        summary_text = (
            f"You have actively indexed and connected {len(today_mems)} knowledge memories across "
            f"'{', '.join(sources)}'. Key focus areas include {entity_str}, with primary documents "
            f"such as {files_str} fully parsed and queryable."
        )
    else:
        summary_text = "ContextOS is monitoring your authorized folders. Ingested files, screenshots, and notes will automatically be summarized in your daily digest."

    highlights = [
        f"{mem_count['cnt'] if mem_count else 0} total memories active in vault",
        f"Key topics: {entity_str}",
        f"{doc_count['cnt'] if doc_count else 0} documents indexed with vector embeddings",
    ]

    return {
        "date": datetime.now(timezone.utc).strftime("%A, %d %B %Y"),
        "summary": summary_text,
        "highlights": highlights,
        "memories_today_count": len(today_mems),
        "top_entities": [dict(e) for e in top_entities],
    }
