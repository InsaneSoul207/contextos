"""
ContextOS Semantic & Sliding Window Text Chunker.

Splits text into chunks preserving sentence boundaries, metadata, and page numbers.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class TextChunk:
    """Represents a chunk of text with position and metadata."""
    content: str
    chunk_index: int
    start_pos: int
    end_pos: int
    page_num: Optional[int] = None
    metadata: Optional[dict] = None


class TextChunker:
    """Chunking engine supporting sentence boundary splitting and character windows."""

    def __init__(self, chunk_size: int = 512, overlap: int = 64) -> None:
        self.chunk_size = chunk_size
        self.overlap = overlap
        self._sentence_split_regex = re.compile(r"(?<=[.!?])\s+")

    def chunk_text(
        self,
        text: str,
        page_num: Optional[int] = None,
        metadata: Optional[dict] = None,
    ) -> list[TextChunk]:
        """Split text into overlapping chunks respecting sentence boundaries."""
        if not text or not text.strip():
            return []

        cleaned_text = text.strip()
        sentences = self._sentence_split_regex.split(cleaned_text)

        chunks: list[TextChunk] = []
        current_chunk_sentences: list[str] = []
        current_len = 0
        chunk_idx = 0
        char_offset = 0

        for sent in sentences:
            sent_len = len(sent)
            if current_len + sent_len > self.chunk_size and current_chunk_sentences:
                chunk_str = " ".join(current_chunk_sentences)
                chunks.append(
                    TextChunk(
                        content=chunk_str,
                        chunk_index=chunk_idx,
                        start_pos=char_offset,
                        end_pos=char_offset + len(chunk_str),
                        page_num=page_num,
                        metadata=metadata,
                    )
                )
                chunk_idx += 1
                char_offset += len(chunk_str) - self.overlap

                # Retain overlap sentences
                overlap_sentences: list[str] = []
                overlap_len = 0
                for s in reversed(current_chunk_sentences):
                    if overlap_len + len(s) <= self.overlap:
                        overlap_sentences.insert(0, s)
                        overlap_len += len(s)
                    else:
                        break
                current_chunk_sentences = overlap_sentences
                current_len = sum(len(s) for s in current_chunk_sentences)

            current_chunk_sentences.append(sent)
            current_len += sent_len

        if current_chunk_sentences:
            chunk_str = " ".join(current_chunk_sentences)
            chunks.append(
                TextChunk(
                    content=chunk_str,
                    chunk_index=chunk_idx,
                    start_pos=char_offset,
                    end_pos=char_offset + len(chunk_str),
                    page_num=page_num,
                    metadata=metadata,
                )
            )

        return chunks
