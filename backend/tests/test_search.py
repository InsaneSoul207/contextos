"""
Tests for Search and Retrieval mechanisms.
"""

from __future__ import annotations

import uuid
from datetime import datetime
import pytest

from app.core.database import DatabaseManager


@pytest.mark.asyncio
async def test_fts_search(test_db: DatabaseManager):
    """Test FTS5 keyword indexing and querying."""
    source_id = str(uuid.uuid4())
    doc_id = str(uuid.uuid4())
    mem_id = str(uuid.uuid4())
    now = datetime.now().isoformat()

    await test_db.execute(
        """INSERT INTO sources (id, source_type, source_path, display_name, created_at)
           VALUES (?, 'folder', '/test', 'Test', ?)""",
        (source_id, now),
    )
    await test_db.execute(
        """INSERT INTO documents (id, source_id, filename, file_type, file_size, original_path, created_at)
           VALUES (?, ?, 'sample.txt', 'txt', 50, '/test/sample.txt', ?)""",
        (doc_id, source_id, now),
    )
    await test_db.execute(
        """INSERT INTO memories (id, document_id, memory_type, content, summary, timestamp, created_at)
           VALUES (?, ?, 'txt', 'Temporal knowledge graph with transformers architecture', 'summary', ?, ?)""",
        (mem_id, doc_id, now, now),
    )
    await test_db.commit()

    # Search via FTS5
    results = await test_db.fetch_all(
        "SELECT rowid FROM memories_fts WHERE memories_fts MATCH 'transformers'"
    )
    assert len(results) == 1
