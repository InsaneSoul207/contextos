"""
ContextOS Chat Storage Service with PostgreSQL and SQLite Dual Support.

Persists full conversation threads and messages to PostgreSQL (if configured)
or local SQLite database with automatic fallback.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from app.core.config import get_settings
from app.core.database import get_database

logger = logging.getLogger(__name__)


class ChatStorageService:
    """Manages chat conversations and message history with multi-turn context."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self._pg_pool = None
        self._pg_initialized = False

    async def _get_pg_pool(self):
        """Lazily initialize and return asyncpg connection pool if configured."""
        if self._pg_pool is not None:
            return self._pg_pool

        pg_url = (self.settings.postgres_url or "").strip()
        if not pg_url:
            return None

        try:
            import asyncpg
            self._pg_pool = await asyncpg.create_pool(pg_url, min_size=1, max_size=5, timeout=5.0)
            if not self._pg_initialized:
                async with self._pg_pool.acquire() as conn:
                    await conn.execute("""
                        CREATE TABLE IF NOT EXISTS conversations (
                            id VARCHAR(64) PRIMARY KEY,
                            title TEXT NOT NULL,
                            created_at TIMESTAMPTZ NOT NULL,
                            updated_at TIMESTAMPTZ NOT NULL
                        );
                        CREATE TABLE IF NOT EXISTS chat_messages (
                            id VARCHAR(64) PRIMARY KEY,
                            conversation_id VARCHAR(64) NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
                            role VARCHAR(16) NOT NULL,
                            content TEXT NOT NULL,
                            sources JSONB,
                            timestamp TIMESTAMPTZ NOT NULL
                        );
                    """)
                self._pg_initialized = True
                logger.info("Connected and initialized chat storage in PostgreSQL.")
            return self._pg_pool
        except Exception as e:
            logger.warning("PostgreSQL connection failed (%s). Falling back to local SQLite.", e)
            self._pg_pool = None
            return None

    async def get_storage_status(self) -> dict[str, Any]:
        """Return the active storage engine (PostgreSQL or SQLite)."""
        pool = await self._get_pg_pool()
        if pool is not None:
            return {
                "engine": "postgresql",
                "connected": True,
                "url": self.settings.postgres_url.split("@")[-1] if "@" in self.settings.postgres_url else "configured",
            }
        return {
            "engine": "sqlite",
            "connected": True,
            "path": str(self.settings.database_path),
            "note": "Configure postgres_url in settings for PostgreSQL storage.",
        }

    async def configure_postgres(self, url: str) -> dict[str, Any]:
        """Test and configure PostgreSQL connection string dynamically."""
        url = (url or "").strip()
        if not url:
            if self._pg_pool is not None:
                try:
                    await self._pg_pool.close()
                except Exception:
                    pass
            self._pg_pool = None
            self._pg_initialized = False
            self.settings.postgres_url = ""
            return {"success": True, "engine": "sqlite", "message": "Switched to local SQLite storage."}

        try:
            import asyncpg
            new_pool = await asyncpg.create_pool(url, min_size=1, max_size=3, timeout=5.0)
            async with new_pool.acquire() as conn:
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS conversations (
                        id VARCHAR(64) PRIMARY KEY,
                        title TEXT NOT NULL,
                        created_at TIMESTAMPTZ NOT NULL,
                        updated_at TIMESTAMPTZ NOT NULL
                    );
                    CREATE TABLE IF NOT EXISTS chat_messages (
                        id VARCHAR(64) PRIMARY KEY,
                        conversation_id VARCHAR(64) NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
                        role VARCHAR(16) NOT NULL,
                        content TEXT NOT NULL,
                        sources JSONB,
                        timestamp TIMESTAMPTZ NOT NULL
                    );
                """)
            if self._pg_pool is not None:
                try:
                    await self._pg_pool.close()
                except Exception:
                    pass
            self._pg_pool = new_pool
            self._pg_initialized = True
            self.settings.postgres_url = url
            logger.info("Successfully connected to PostgreSQL at %s", url.split("@")[-1] if "@" in url else "host")
            return {"success": True, "engine": "postgresql", "message": "Successfully connected to PostgreSQL!"}
        except Exception as e:
            logger.warning("PostgreSQL connection error: %s", e)
            return {"success": False, "engine": "sqlite", "error": str(e), "message": f"Connection failed: {e}"}

    async def create_conversation(self, title: str = "New Chat") -> dict[str, Any]:
        """Create a new chat conversation session."""
        conv_id = str(uuid4())
        now = datetime.now(timezone.utc).isoformat()
        clean_title = title.strip()[:60] or "New Chat"

        pool = await self._get_pg_pool()
        if pool is not None:
            async with pool.acquire() as conn:
                await conn.execute(
                    "INSERT INTO conversations (id, title, created_at, updated_at) VALUES ($1, $2, $3, $4)",
                    conv_id, clean_title, datetime.now(timezone.utc), datetime.now(timezone.utc),
                )
        else:
            db = get_database()
            await db.execute(
                "INSERT INTO conversations (id, title, created_at, updated_at) VALUES (?, ?, ?, ?)",
                (conv_id, clean_title, now, now),
            )
            await db.commit()

        return {"id": conv_id, "title": clean_title, "created_at": now, "updated_at": now}

    async def list_conversations(self, limit: int = 50) -> list[dict[str, Any]]:
        """List previous conversations sorted by most recent."""
        pool = await self._get_pg_pool()
        if pool is not None:
            async with pool.acquire() as conn:
                rows = await conn.fetch(
                    "SELECT id, title, created_at, updated_at FROM conversations ORDER BY updated_at DESC LIMIT $1",
                    limit,
                )
                return [
                    {
                        "id": r["id"],
                        "title": r["title"],
                        "created_at": r["created_at"].isoformat() if hasattr(r["created_at"], "isoformat") else str(r["created_at"]),
                        "updated_at": r["updated_at"].isoformat() if hasattr(r["updated_at"], "isoformat") else str(r["updated_at"]),
                    }
                    for r in rows
                ]

        db = get_database()
        rows = await db.fetch_all(
            "SELECT id, title, created_at, updated_at FROM conversations ORDER BY updated_at DESC LIMIT ?",
            (limit,),
        )
        return [dict(r) for r in rows]

    async def get_conversation(self, conv_id: str) -> Optional[dict[str, Any]]:
        """Retrieve conversation metadata and all its historical messages."""
        pool = await self._get_pg_pool()
        if pool is not None:
            async with pool.acquire() as conn:
                conv = await conn.fetchrow("SELECT * FROM conversations WHERE id = $1", conv_id)
                if not conv:
                    return None
                msg_rows = await conn.fetch(
                    "SELECT id, role, content, sources, timestamp FROM chat_messages WHERE conversation_id = $1 ORDER BY timestamp ASC",
                    conv_id,
                )
                messages = []
                for m in msg_rows:
                    sources_data = m["sources"]
                    if isinstance(sources_data, str):
                        try:
                            sources_data = json.loads(sources_data)
                        except Exception:
                            sources_data = []
                    messages.append({
                        "id": m["id"],
                        "role": m["role"],
                        "content": m["content"],
                        "sources": sources_data or [],
                        "timestamp": m["timestamp"].isoformat() if hasattr(m["timestamp"], "isoformat") else str(m["timestamp"]),
                    })
                return {
                    "id": conv["id"],
                    "title": conv["title"],
                    "created_at": str(conv["created_at"]),
                    "updated_at": str(conv["updated_at"]),
                    "messages": messages,
                }

        db = get_database()
        conv = await db.fetch_one("SELECT * FROM conversations WHERE id = ?", (conv_id,))
        if not conv:
            return None

        msg_rows = await db.fetch_all(
            "SELECT id, role, content, sources, timestamp FROM chat_messages WHERE conversation_id = ? ORDER BY timestamp ASC",
            (conv_id,),
        )
        messages = []
        for m in msg_rows:
            sources_val = []
            if m.get("sources"):
                try:
                    sources_val = json.loads(m["sources"])
                except Exception:
                    sources_val = []
            messages.append({
                "id": m["id"],
                "role": m["role"],
                "content": m["content"],
                "sources": sources_val,
                "timestamp": m["timestamp"],
            })

        return {
            "id": conv["id"],
            "title": conv["title"],
            "created_at": conv["created_at"],
            "updated_at": conv["updated_at"],
            "messages": messages,
        }

    async def delete_conversation(self, conv_id: str) -> None:
        """Delete a conversation and all its messages."""
        pool = await self._get_pg_pool()
        if pool is not None:
            async with pool.acquire() as conn:
                await conn.execute("DELETE FROM chat_messages WHERE conversation_id = $1", conv_id)
                await conn.execute("DELETE FROM conversations WHERE id = $1", conv_id)
                return

        db = get_database()
        await db.execute("DELETE FROM chat_messages WHERE conversation_id = ?", (conv_id,))
        await db.execute("DELETE FROM conversations WHERE id = ?", (conv_id,))
        await db.commit()

    async def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        sources: Optional[list[Any]] = None,
    ) -> dict[str, Any]:
        """Save a new user or assistant message to the conversation."""
        msg_id = str(uuid4())
        now_dt = datetime.now(timezone.utc)
        now_str = now_dt.isoformat()
        sources_json = json.dumps(sources or [], default=str)

        pool = await self._get_pg_pool()
        if pool is not None:
            async with pool.acquire() as conn:
                await conn.execute(
                    """INSERT INTO chat_messages (id, conversation_id, role, content, sources, timestamp)
                       VALUES ($1, $2, $3, $4, $5, $6)""",
                    msg_id, conversation_id, role, content, sources_json, now_dt,
                )
                await conn.execute(
                    "UPDATE conversations SET updated_at = $1 WHERE id = $2",
                    now_dt, conversation_id,
                )
        else:
            db = get_database()
            await db.execute(
                """INSERT INTO chat_messages (id, conversation_id, role, content, sources, timestamp)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (msg_id, conversation_id, role, content, sources_json, now_str),
            )
            await db.execute(
                "UPDATE conversations SET updated_at = ? WHERE id = ?",
                (now_str, conversation_id),
            )
            await db.commit()

        return {
            "id": msg_id,
            "conversation_id": conversation_id,
            "role": role,
            "content": content,
            "sources": sources or [],
            "timestamp": now_str,
        }

    async def get_recent_history(
        self, conversation_id: str, max_exchanges: int = 5
    ) -> list[dict[str, str]]:
        """Get the last N conversational exchanges (up to max_exchanges * 2 messages) in chronological order for AI context memory."""
        limit = max_exchanges * 2
        pool = await self._get_pg_pool()
        if pool is not None:
            async with pool.acquire() as conn:
                rows = await conn.fetch(
                    """SELECT role, content FROM chat_messages
                       WHERE conversation_id = $1
                       ORDER BY timestamp DESC
                       LIMIT $2""",
                    conversation_id, limit,
                )
                # Reverse to get chronological order
                return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]

        db = get_database()
        rows = await db.fetch_all(
            """SELECT role, content FROM chat_messages
               WHERE conversation_id = ?
               ORDER BY timestamp DESC
               LIMIT ?""",
            (conversation_id, limit),
        )
        return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]


_chat_storage: Optional[ChatStorageService] = None


def get_chat_storage() -> ChatStorageService:
    """Return singleton ChatStorageService."""
    global _chat_storage
    if _chat_storage is None:
        _chat_storage = ChatStorageService()
    return _chat_storage
