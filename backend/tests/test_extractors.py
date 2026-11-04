"""
Tests for Text Chunker, Entity Extractor, and Extractors.
"""

from __future__ import annotations

import tempfile
import uuid
from pathlib import Path
import pytest

from app.processing.chunker import TextChunker
from app.processing.entity_extractor import EntityExtractor
from app.processing.extractors import TextExtractor


def test_chunker_basic():
    chunker = TextChunker(chunk_size=100, overlap=20)
    sample = "Hello world! This is a test sentence for ContextOS. Another sentence follows right here."
    chunks = chunker.chunk_text(sample)
    assert len(chunks) >= 1
    assert any("ContextOS" in c.content for c in chunks)


def test_entity_extractor():
    extractor = EntityExtractor()
    text = "Project Capsule uses React Native and PyTorch. Discussed on September 12, 2026."
    entities = extractor.extract_entities(text)
    names = {e.name for e in entities}
    assert "PyTorch" in names or "React Native" in names or "React" in names
    assert any(e.entity_type == "Date" for e in entities)


@pytest.mark.asyncio
async def test_text_extractor():
    tmp_path = Path(tempfile.gettempdir()) / f"test_{uuid.uuid4().hex}.txt"
    tmp_path.write_text("ContextOS personal memory infrastructure sample.", encoding="utf-8")

    extractor = TextExtractor()
    result = await extractor.extract(tmp_path)
    assert "ContextOS" in result.text

    try:
        tmp_path.unlink(missing_ok=True)
    except Exception:
        pass
