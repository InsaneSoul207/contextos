"""
ContextOS Sources API Router.

Endpoints for managing monitored folders and data sources.
"""

import logging
import os
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query

from app.core.database import get_database
from app.models.schemas import SourceCreate, SourceResponse, SourceUpdate

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/sources", tags=["sources"])


@router.post("", response_model=SourceResponse, status_code=201)
async def add_source(body: SourceCreate) -> SourceResponse:
    """Add a new monitored folder source."""
    path = os.path.expanduser(body.source_path)
    if not os.path.isdir(path):
        raise HTTPException(status_code=400, detail=f"Path does not exist or is not a directory: {path}")

    db = get_database()
    source_id = str(uuid4())
    now = datetime.now(timezone.utc).isoformat()
    display_name = body.display_name or os.path.basename(path) or path

    await db.execute(
        """INSERT INTO sources (id, source_type, source_path, display_name, permission_status, status, created_at)
           VALUES (?, ?, ?, ?, 'granted', 'active', ?)""",
        (source_id, body.source_type, path, display_name, now),
    )
    await db.commit()

    # Trigger initial scan in the background (import here to avoid circular dep)
    try:
        from app.ingestion.scanner import FolderScanner
        scanner = FolderScanner()
        import asyncio
        asyncio.create_task(scanner.scan_folder(source_id, path))
    except Exception:
        logger.exception("Failed to start initial scan for source %s", source_id)

    logger.info("Source added: %s (%s)", display_name, path)

    return SourceResponse(
        id=source_id,
        source_type=body.source_type,
        source_path=path,
        display_name=display_name,
        permission_status="granted",
        status="active",
        created_at=now,
        document_count=0,
    )


@router.get("", response_model=list[SourceResponse])
async def list_sources() -> list[SourceResponse]:
    """List all registered sources."""
    db = get_database()
    rows = await db.fetch_all("SELECT * FROM sources ORDER BY created_at DESC")
    results: list[SourceResponse] = []
    for r in rows:
        count_row = await db.fetch_one(
            "SELECT COUNT(*) as cnt FROM documents WHERE source_id = ?", (r["id"],)
        )
        doc_count = count_row["cnt"] if count_row else 0
        results.append(SourceResponse(**r, document_count=doc_count))
    return results


@router.get("/{source_id}", response_model=SourceResponse)
async def get_source(source_id: str) -> SourceResponse:
    """Get a single source by ID."""
    db = get_database()
    row = await db.fetch_one("SELECT * FROM sources WHERE id = ?", (source_id,))
    if not row:
        raise HTTPException(status_code=404, detail="Source not found")
    count_row = await db.fetch_one(
        "SELECT COUNT(*) as cnt FROM documents WHERE source_id = ?", (source_id,)
    )
    return SourceResponse(**row, document_count=count_row["cnt"] if count_row else 0)


@router.put("/{source_id}", response_model=SourceResponse)
async def update_source(source_id: str, body: SourceUpdate) -> SourceResponse:
    """Update a source (pause/resume/rename)."""
    db = get_database()
    row = await db.fetch_one("SELECT * FROM sources WHERE id = ?", (source_id,))
    if not row:
        raise HTTPException(status_code=404, detail="Source not found")

    updates: list[str] = []
    params: list[str] = []
    if body.display_name is not None:
        updates.append("display_name = ?")
        params.append(body.display_name)
    if body.status is not None:
        if body.status not in ("active", "paused"):
            raise HTTPException(status_code=400, detail="Status must be 'active' or 'paused'")
        updates.append("status = ?")
        params.append(body.status)

    if updates:
        params.append(source_id)
        await db.execute(
            f"UPDATE sources SET {', '.join(updates)} WHERE id = ?", tuple(params)
        )
        await db.commit()

    return await get_source(source_id)


@router.delete("/{source_id}")
async def delete_source(source_id: str) -> dict[str, str]:
    """Delete a source and its associated documents, jobs, and memories."""
    db = get_database()
    row = await db.fetch_one("SELECT * FROM sources WHERE id = ?", (source_id,))
    if not row:
        raise HTTPException(status_code=404, detail="Source not found")

    # Clean up memories and jobs for all documents belonging to this source
    await db.execute(
        "DELETE FROM memories WHERE document_id IN (SELECT id FROM documents WHERE source_id = ?)",
        (source_id,),
    )
    await db.execute(
        "DELETE FROM processing_jobs WHERE document_id IN (SELECT id FROM documents WHERE source_id = ?)",
        (source_id,),
    )
    await db.execute("DELETE FROM documents WHERE source_id = ?", (source_id,))
    await db.execute("DELETE FROM sources WHERE id = ?", (source_id,))
    await db.commit()
    logger.info("Source and related documents deleted: %s", source_id)
    return {"status": "deleted", "source_id": source_id}


@router.post("/{source_id}/sync", status_code=202)
async def sync_source(source_id: str) -> dict[str, str]:
    """Trigger a manual rescan of a source folder."""
    db = get_database()
    row = await db.fetch_one("SELECT * FROM sources WHERE id = ?", (source_id,))
    if not row:
        raise HTTPException(status_code=404, detail="Source not found")

    now = datetime.now(timezone.utc).isoformat()
    await db.execute(
        "UPDATE sources SET last_synced = ? WHERE id = ?", (now, source_id)
    )
    await db.commit()

    try:
        from app.ingestion.scanner import FolderScanner
        import asyncio
        scanner = FolderScanner()
        asyncio.create_task(scanner.scan_folder(source_id, row["source_path"]))
    except Exception:
        logger.exception("Failed to start sync for source %s", source_id)

    return {"status": "sync_started", "source_id": source_id}
