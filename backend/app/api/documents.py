"""
ContextOS Documents API Router.

Endpoints for listing, inspecting, uploading, and deleting documents.
"""

import hashlib
import logging
import os
import shutil
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query, UploadFile, File, Request
from pydantic import BaseModel

from app.core.config import get_settings
from app.core.database import get_database
from app.models.schemas import DocumentResponse, DocumentDetail, MemoryResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.get("", response_model=list[DocumentResponse])
async def list_documents(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    source_id: str | None = Query(default=None),
    status: str | None = Query(default=None),
) -> list[DocumentResponse]:
    """List documents with pagination and optional filters."""
    db = get_database()
    where_clauses: list[str] = []
    params: list[str | int] = []

    if source_id:
        where_clauses.append("source_id = ?")
        params.append(source_id)
    if status:
        where_clauses.append("processing_status = ?")
        params.append(status)

    where_sql = (" WHERE " + " AND ".join(where_clauses)) if where_clauses else ""
    params.extend([limit, offset])

    rows = await db.fetch_all(
        f"SELECT * FROM documents{where_sql} ORDER BY created_at DESC LIMIT ? OFFSET ?",
        tuple(params),
    )
    return [DocumentResponse(**r) for r in rows]


@router.get("/{doc_id}", response_model=DocumentDetail)
async def get_document(doc_id: str) -> DocumentDetail:
    """Get full document detail including its memories."""
    db = get_database()
    row = await db.fetch_one("SELECT * FROM documents WHERE id = ?", (doc_id,))
    if not row:
        raise HTTPException(status_code=404, detail="Document not found")

    mem_rows = await db.fetch_all(
        "SELECT * FROM memories WHERE document_id = ? ORDER BY timestamp", (doc_id,)
    )
    memories = [MemoryResponse(**m) for m in mem_rows]
    return DocumentDetail(**row, memories=memories)


@router.delete("/{doc_id}", status_code=204)
async def delete_document(doc_id: str) -> None:
    """Delete a document and all its memories."""
    db = get_database()
    row = await db.fetch_one("SELECT * FROM documents WHERE id = ?", (doc_id,))
    if not row:
        raise HTTPException(status_code=404, detail="Document not found")

    await db.execute("DELETE FROM memories WHERE document_id = ?", (doc_id,))
    await db.execute("DELETE FROM processing_jobs WHERE document_id = ?", (doc_id,))
    await db.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
    await db.commit()
    logger.info("Document deleted: %s", doc_id)


@router.post("/upload", response_model=DocumentResponse, status_code=201)
async def upload_document(
    request: Request,
    file: UploadFile | None = File(default=None),
) -> DocumentResponse:
    """Manually upload a file for processing or accept JSON capture payload."""
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type or file is None:
        try:
            data = await request.json()
            capture_req = CaptureRequest(**data)
            return await capture_web_content(capture_req)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid payload: {e}")

    settings = get_settings()

    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    # Read file content
    content = await file.read()
    file_size = len(content)

    if file_size > settings.max_file_size_mb * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds maximum size of {settings.max_file_size_mb} MB",
        )

    # Compute hash
    file_hash = hashlib.sha256(content).hexdigest()

    db = get_database()

    # Check duplicate
    existing = await db.fetch_one(
        "SELECT id FROM documents WHERE file_hash = ?", (file_hash,)
    )
    if existing:
        raise HTTPException(status_code=409, detail="Duplicate file (same hash already exists)")

    # Determine file type
    ext = os.path.splitext(file.filename)[1].lower().lstrip(".")
    supported = {
        "pdf", "txt", "docx", "csv", "png", "jpg", "jpeg", "webp", "html",
        "mp3", "wav", "m4a", "ogg", "flac", "aac",
    }
    if ext not in supported:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext}")

    # Save to uploads directory
    dest = settings.uploads_dir / f"{uuid4().hex}_{file.filename}"
    with open(dest, "wb") as f:
        f.write(content)

    # Ensure an 'uploads' source exists
    upload_source = await db.fetch_one(
        "SELECT id FROM sources WHERE source_type = 'upload'"
    )
    if not upload_source:
        source_id = str(uuid4())
        now = datetime.now(timezone.utc).isoformat()
        await db.execute(
            """INSERT INTO sources (id, source_type, source_path, display_name, permission_status, status, created_at)
               VALUES (?, 'upload', ?, 'Uploads', 'granted', 'active', ?)""",
            (source_id, str(settings.uploads_dir), now),
        )
    else:
        source_id = upload_source["id"]

    doc_id = str(uuid4())
    now = datetime.now(timezone.utc).isoformat()

    await db.execute(
        """INSERT INTO documents
           (id, source_id, filename, file_hash, file_type, file_size, original_path, created_at, modified_at, ingested_at, processing_status)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending')""",
        (doc_id, source_id, file.filename, file_hash, ext, file_size, str(dest), now, now, now),
    )

    # Create processing job
    job_id = str(uuid4())
    await db.execute(
        """INSERT INTO processing_jobs (id, document_id, job_type, status, created_at)
           VALUES (?, ?, 'full', 'queued', ?)""",
        (job_id, doc_id, now),
    )
    await db.commit()
    logger.info("File uploaded: %s -> %s", file.filename, doc_id)

    return DocumentResponse(
        id=doc_id,
        source_id=source_id,
        filename=file.filename,
        file_type=ext,
        file_size=file_size,
        processing_status="pending",
        ingested_at=now,
        created_at=now,
    )


class CaptureRequest(BaseModel):
    type: str = "webpage"
    title: str = "Untitled"
    url: str = ""
    content: str = ""
    timestamp: str | None = None
    metadata: dict | None = None


class QuickCaptureRequest(BaseModel):
    content: str
    title: str | None = None
    tags: list[str] | None = None


@router.post("/quick-capture", response_model=DocumentResponse, status_code=201)
async def quick_capture(body: QuickCaptureRequest) -> DocumentResponse:
    """Instantly capture clipboard text or manual notes into ContextOS memory."""
    settings = get_settings()
    db = get_database()
    now = datetime.now(timezone.utc).isoformat()
    raw_text = body.content.strip()
    if not raw_text:
        raise HTTPException(status_code=400, detail="Content cannot be empty")

    source = await db.fetch_one("SELECT id FROM sources WHERE source_type = 'quick_capture'")
    if not source:
        source_id = str(uuid4())
        await db.execute(
            """INSERT INTO sources (id, source_type, source_path, display_name, permission_status, status, created_at)
               VALUES (?, 'quick_capture', 'contextos://quick-notes', 'Quick Notes & Clipboard', 'granted', 'active', ?)""",
            (source_id, now),
        )
    else:
        source_id = source["id"]

    title = body.title or (raw_text[:30].replace("\n", " ").strip() or "Quick Note")
    clean_title = "".join(c for c in title if c.isalnum() or c in (" ", "_", "-")).strip() or "note"
    file_hash = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()
    filename = f"{clean_title}_{file_hash[:8]}.txt"
    dest = settings.uploads_dir / filename

    with open(dest, "w", encoding="utf-8") as f:
        f.write(raw_text)

    doc_id = str(uuid4())
    file_size = len(raw_text.encode("utf-8"))
    await db.execute(
        """INSERT INTO documents
           (id, source_id, filename, file_hash, file_type, file_size, original_path, created_at, modified_at, ingested_at, processing_status)
           VALUES (?, ?, ?, ?, 'text', ?, ?, ?, ?, ?, 'pending')""",
        (doc_id, source_id, filename, file_hash, file_size, str(dest), now, now, now),
    )

    job_id = str(uuid4())
    await db.execute(
        """INSERT INTO processing_jobs (id, document_id, job_type, status, created_at)
           VALUES (?, ?, 'full', 'queued', ?)""",
        (job_id, doc_id, now),
    )
    await db.commit()
    logger.info("Quick capture saved: %s (%s)", filename, doc_id)

    return DocumentResponse(
        id=doc_id,
        source_id=source_id,
        filename=filename,
        file_type="text",
        file_size=file_size,
        processing_status="pending",
        ingested_at=now,
        created_at=now,
    )


@router.get("/export/all")
async def export_all_memories() -> dict:
    """Export all indexed documents, memories, and entity graphs for backup or Obsidian vault conversion."""
    db = get_database()
    docs = await db.fetch_all("SELECT * FROM documents")
    mems = await db.fetch_all("SELECT id, document_id, memory_type, content, summary, timestamp FROM memories")
    ents = await db.fetch_all("SELECT * FROM entities")
    rels = await db.fetch_all("SELECT * FROM relationships")

    return {
        "version": "0.1.0",
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "stats": {
            "documents_count": len(docs),
            "memories_count": len(mems),
            "entities_count": len(ents),
            "relationships_count": len(rels),
        },
        "documents": [dict(d) for d in docs],
        "memories": [dict(m) for m in mems],
        "entities": [dict(e) for e in ents],
        "relationships": [dict(r) for r in rels],
    }


@router.post("/capture", response_model=DocumentResponse, status_code=201)
async def capture_web_content(body: CaptureRequest) -> DocumentResponse:
    """Capture web content, pages, or text selections from the browser extension."""
    import json
    settings = get_settings()
    db = get_database()

    content_str = json.dumps(body.model_dump(), ensure_ascii=False, indent=2)
    content_bytes = content_str.encode("utf-8")
    file_size = len(content_bytes)
    file_hash = hashlib.sha256(content_bytes).hexdigest()

    # Ensure extension source exists
    source = await db.fetch_one("SELECT id FROM sources WHERE source_type = 'extension'")
    now = datetime.now(timezone.utc).isoformat()
    if not source:
        source_id = str(uuid4())
        await db.execute(
            """INSERT INTO sources (id, source_type, source_path, display_name, permission_status, status, created_at)
               VALUES (?, 'extension', 'browser://contextos', 'Browser Extension', 'granted', 'active', ?)""",
            (source_id, now),
        )
    else:
        source_id = source["id"]

    safe_title = "".join(c for c in body.title if c.isalnum() or c in (" ", "_", "-")).strip()[:40] or "webpage"
    filename = f"{safe_title}_{file_hash[:8]}.json"
    dest = settings.uploads_dir / filename

    with open(dest, "w", encoding="utf-8") as f:
        f.write(content_str)

    doc_id = str(uuid4())
    await db.execute(
        """INSERT INTO documents
           (id, source_id, filename, file_hash, file_type, file_size, original_path, created_at, modified_at, ingested_at, processing_status)
           VALUES (?, ?, ?, ?, 'webpage', ?, ?, ?, ?, ?, 'pending')""",
        (doc_id, source_id, filename, file_hash, file_size, str(dest), now, now, now),
    )

    # Queue processing job
    job_id = str(uuid4())
    await db.execute(
        """INSERT INTO processing_jobs (id, document_id, job_type, status, created_at)
           VALUES (?, ?, 'full', 'queued', ?)""",
        (job_id, doc_id, now),
    )
    await db.commit()
    logger.info("Captured web content saved and queued: %s (%s)", filename, doc_id)

    return DocumentResponse(
        id=doc_id,
        source_id=source_id,
        filename=filename,
        file_type="webpage",
        file_size=file_size,
        processing_status="pending",
        ingested_at=now,
        created_at=now,
    )
