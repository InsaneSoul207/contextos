"""
ContextOS Database Manager.

Async SQLite database manager using aiosqlite with WAL mode, FTS5, and
proper schema for the ContextOS knowledge base.
"""

import logging
from pathlib import Path
from typing import Any, Optional

import aiosqlite

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# SQL DDL
# ---------------------------------------------------------------------------

_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS sources (
    id TEXT PRIMARY KEY,
    source_type TEXT NOT NULL,
    source_path TEXT NOT NULL,
    display_name TEXT NOT NULL,
    permission_status TEXT DEFAULT 'granted',
    last_synced TEXT,
    status TEXT DEFAULT 'active',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS documents (
    id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
    filename TEXT NOT NULL,
    file_hash TEXT UNIQUE,
    file_type TEXT NOT NULL,
    file_size INTEGER NOT NULL,
    original_path TEXT NOT NULL,
    created_at TEXT NOT NULL,
    modified_at TEXT,
    ingested_at TEXT,
    processing_status TEXT DEFAULT 'pending'
);

CREATE TABLE IF NOT EXISTS memories (
    id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    memory_type TEXT NOT NULL,
    content TEXT NOT NULL,
    summary TEXT,
    embedding BLOB,
    timestamp TEXT NOT NULL,
    confidence REAL DEFAULT 1.0,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS entities (
    id TEXT PRIMARY KEY,
    entity_name TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    first_seen TEXT NOT NULL,
    last_seen TEXT NOT NULL,
    mention_count INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS relationships (
    id TEXT PRIMARY KEY,
    subject_entity_id TEXT NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
    predicate TEXT NOT NULL,
    object_entity_id TEXT NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
    source_memory_id TEXT REFERENCES memories(id) ON DELETE SET NULL,
    confidence REAL DEFAULT 1.0,
    valid_from TEXT,
    valid_to TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS processing_jobs (
    id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    job_type TEXT NOT NULL,
    status TEXT DEFAULT 'queued',
    error TEXT,
    started_at TEXT,
    completed_at TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS memory_versions (
    id TEXT PRIMARY KEY,
    memory_id TEXT NOT NULL REFERENCES memories(id) ON DELETE CASCADE,
    version INTEGER NOT NULL,
    content TEXT NOT NULL,
    change_reason TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS search_history (
    id TEXT PRIMARY KEY,
    query TEXT NOT NULL,
    result_count INTEGER DEFAULT 0,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS conversations (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS chat_messages (
    id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    sources TEXT,
    timestamp TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS collections (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    color TEXT DEFAULT '#6366f1',
    icon TEXT DEFAULT 'folder',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS collection_items (
    id TEXT PRIMARY KEY,
    collection_id TEXT NOT NULL REFERENCES collections(id) ON DELETE CASCADE,
    memory_id TEXT NOT NULL REFERENCES memories(id) ON DELETE CASCADE,
    added_at TEXT NOT NULL,
    UNIQUE(collection_id, memory_id)
);
"""

_FTS_SQL = """
CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
    content,
    summary,
    content='memories',
    content_rowid='rowid'
);

-- Triggers to keep FTS in sync
CREATE TRIGGER IF NOT EXISTS memories_ai AFTER INSERT ON memories BEGIN
    INSERT INTO memories_fts(rowid, content, summary)
    VALUES (new.rowid, new.content, new.summary);
END;

CREATE TRIGGER IF NOT EXISTS memories_ad AFTER DELETE ON memories BEGIN
    INSERT INTO memories_fts(memories_fts, rowid, content, summary)
    VALUES ('delete', old.rowid, old.content, old.summary);
END;

CREATE TRIGGER IF NOT EXISTS memories_au AFTER UPDATE ON memories BEGIN
    INSERT INTO memories_fts(memories_fts, rowid, content, summary)
    VALUES ('delete', old.rowid, old.content, old.summary);
    INSERT INTO memories_fts(rowid, content, summary)
    VALUES (new.rowid, new.content, new.summary);
END;
"""

_INDEXES_SQL = """
CREATE INDEX IF NOT EXISTS idx_documents_source_id ON documents(source_id);
CREATE INDEX IF NOT EXISTS idx_documents_processing_status ON documents(processing_status);
CREATE INDEX IF NOT EXISTS idx_documents_file_type ON documents(file_type);
CREATE INDEX IF NOT EXISTS idx_memories_document_id ON memories(document_id);
CREATE INDEX IF NOT EXISTS idx_memories_memory_type ON memories(memory_type);
CREATE INDEX IF NOT EXISTS idx_memories_timestamp ON memories(timestamp);
CREATE INDEX IF NOT EXISTS idx_entities_entity_type ON entities(entity_type);
CREATE INDEX IF NOT EXISTS idx_entities_entity_name ON entities(entity_name);
CREATE INDEX IF NOT EXISTS idx_relationships_subject ON relationships(subject_entity_id);
CREATE INDEX IF NOT EXISTS idx_relationships_object ON relationships(object_entity_id);
CREATE INDEX IF NOT EXISTS idx_relationships_predicate ON relationships(predicate);
CREATE INDEX IF NOT EXISTS idx_processing_jobs_status ON processing_jobs(status);
CREATE INDEX IF NOT EXISTS idx_processing_jobs_document_id ON processing_jobs(document_id);
CREATE INDEX IF NOT EXISTS idx_memory_versions_memory_id ON memory_versions(memory_id);
CREATE INDEX IF NOT EXISTS idx_search_history_created_at ON search_history(created_at);
"""


class DatabaseManager:
    """Async SQLite database manager (singleton-style)."""

    def __init__(self, db_path: Optional[Path] = None) -> None:
        self._db_path = str(db_path) if db_path else None
        self._connection: Optional[aiosqlite.Connection] = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def connect(self) -> None:
        """Open the database connection and enable WAL mode."""
        if self._connection is not None:
            return
        if self._db_path is None:
            from app.core.config import get_settings
            self._db_path = str(get_settings().database_path)
        logger.info("Connecting to database at %s", self._db_path)
        self._connection = await aiosqlite.connect(self._db_path)
        self._connection.row_factory = aiosqlite.Row
        await self._connection.execute("PRAGMA journal_mode=WAL")
        await self._connection.execute("PRAGMA foreign_keys=ON")
        await self._connection.commit()

    async def disconnect(self) -> None:
        """Close the database connection."""
        if self._connection:
            await self._connection.close()
            self._connection = None
            logger.info("Database connection closed.")

    @property
    def connection(self) -> aiosqlite.Connection:
        """Return the active connection (raises if not connected)."""
        if self._connection is None:
            raise RuntimeError("Database is not connected. Call connect() first.")
        return self._connection

    # ------------------------------------------------------------------
    # Schema bootstrap
    # ------------------------------------------------------------------

    async def init_db(self) -> None:
        """Create all tables, FTS virtual tables, and indexes."""
        await self.connect()
        conn = self.connection
        await conn.executescript(_TABLES_SQL)
        await conn.executescript(_FTS_SQL)
        await conn.executescript(_INDEXES_SQL)
        await conn.commit()
        logger.info("Database schema initialized.")

    # ------------------------------------------------------------------
    # Generic helpers
    # ------------------------------------------------------------------

    async def execute(
        self, sql: str, params: tuple[Any, ...] | list[Any] = ()
    ) -> aiosqlite.Cursor:
        """Execute a single SQL statement."""
        return await self.connection.execute(sql, params)

    async def executemany(
        self, sql: str, params_seq: list[tuple[Any, ...]]
    ) -> aiosqlite.Cursor:
        """Execute a SQL statement for each parameter set."""
        return await self.connection.executemany(sql, params_seq)

    async def fetch_one(
        self, sql: str, params: tuple[Any, ...] | list[Any] = ()
    ) -> Optional[dict[str, Any]]:
        """Fetch a single row as a dict."""
        cursor = await self.connection.execute(sql, params)
        row = await cursor.fetchone()
        if row is None:
            return None
        return dict(row)

    async def fetch_all(
        self, sql: str, params: tuple[Any, ...] | list[Any] = ()
    ) -> list[dict[str, Any]]:
        """Fetch all rows as a list of dicts."""
        cursor = await self.connection.execute(sql, params)
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

    async def commit(self) -> None:
        """Commit the current transaction."""
        await self.connection.commit()


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_db: Optional[DatabaseManager] = None


def get_database() -> DatabaseManager:
    """Return the module-level DatabaseManager singleton."""
    global _db
    if _db is None:
        _db = DatabaseManager()
    return _db


async def init_db() -> None:
    """Convenience function to initialise the database."""
    db = get_database()
    await db.init_db()
