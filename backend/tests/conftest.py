"""
ContextOS Backend Pytest Fixtures.
"""

from __future__ import annotations

import os
import tempfile
import uuid
from pathlib import Path
from typing import AsyncGenerator

import pytest_asyncio

from app.core.database import DatabaseManager


@pytest_asyncio.fixture
async def test_db() -> AsyncGenerator[DatabaseManager, None]:
    """Provide a temporary SQLite database initialized with schema."""
    temp_dir = tempfile.gettempdir()
    db_path = os.path.join(temp_dir, f"test_contextos_{uuid.uuid4().hex}.db")

    manager = DatabaseManager(Path(db_path))
    await manager.init_db()

    yield manager

    await manager.disconnect()
    try:
        if os.path.exists(db_path):
            os.remove(db_path)
    except Exception:
        pass
