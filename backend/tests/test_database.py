"""
Tests for ContextOS Database initialization and CRUD.
"""

from __future__ import annotations

import uuid
from datetime import datetime
import pytest

from app.core.database import DatabaseManager


@pytest.mark.asyncio
async def test_database_init(test_db: DatabaseManager):
    """Verify tables were created."""
    rows = await test_db.fetch_all(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    )
    table_names = {r["name"] for r in rows}
    assert "sources" in table_names
    assert "documents" in table_names
    assert "memories" in table_names
    assert "entities" in table_names
    assert "relationships" in table_names


@pytest.mark.asyncio
async def test_source_and_document_crud(test_db: DatabaseManager):
    """Verify source and document insertions."""
    source_id = str(uuid.uuid4())
    now = datetime.now().isoformat()

    await test_db.execute(
        """INSERT INTO sources (id, source_type, source_path, display_name, created_at)
           VALUES (?, 'folder', '/test/path', 'Test Folder', ?)""",
        (source_id, now),
    )
    await test_db.commit()

    source = await test_db.fetch_one("SELECT * FROM sources WHERE id = ?", (source_id,))
    assert source is not None
    assert source["display_name"] == "Test Folder"

    doc_id = str(uuid.uuid4())
    await test_db.execute(
        """INSERT INTO documents (id, source_id, filename, file_hash, file_type, file_size, original_path, created_at)
           VALUES (?, ?, 'doc.txt', 'hash123', 'txt', 100, '/test/path/doc.txt', ?)""",
        (doc_id, source_id, now),
    )
    await test_db.commit()

    doc = await test_db.fetch_one("SELECT * FROM documents WHERE id = ?", (doc_id,))
    assert doc is not None
    assert doc["filename"] == "doc.txt"
