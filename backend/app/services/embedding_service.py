"""
ContextOS Embedding Service.

Lazily loads a sentence-transformer model and provides methods for
generating embeddings, computing similarity, and searching similar memories.
"""

import logging
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Manages text embeddings using sentence-transformers."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2") -> None:
        self._model_name = model_name
        self._model: Optional[object] = None

    def _load_model(self) -> None:
        """Lazily load the sentence-transformer model."""
        if self._model is not None:
            return
        logger.info("Loading embedding model: %s", self._model_name)
        try:
            import os
            from pathlib import Path
            cache_dir = Path.home() / ".cache" / "huggingface" / "hub"
            cache_dir.mkdir(parents=True, exist_ok=True)
            os.environ["HF_HOME"] = str(Path.home() / ".cache" / "huggingface")
            from sentence_transformers import SentenceTransformer
            try:
                self._model = SentenceTransformer(
                    self._model_name,
                    cache_folder=str(cache_dir),
                    model_kwargs={"local_files_only": True},
                )
            except Exception:
                self._model = SentenceTransformer(self._model_name, cache_folder=str(cache_dir))
            logger.info("Embedding model loaded successfully.")
        except Exception:
            logger.exception("Failed to load embedding model %s", self._model_name)
            raise

    def embed_text(self, text: str) -> list[float]:
        """Generate an embedding vector for a single text string.

        Args:
            text: The text to embed.

        Returns:
            A list of floats representing the embedding vector.
        """
        self._load_model()
        embedding = self._model.encode(text, show_progress_bar=False)  # type: ignore[union-attr]
        return embedding.tolist()

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embedding vectors for a batch of texts.

        Args:
            texts: List of text strings.

        Returns:
            A list of embedding vectors.
        """
        if not texts:
            return []
        self._load_model()
        embeddings = self._model.encode(texts, show_progress_bar=False, batch_size=32)  # type: ignore[union-attr]
        return [e.tolist() for e in embeddings]

    @staticmethod
    def cosine_similarity(a: list[float], b: list[float]) -> float:
        """Compute cosine similarity between two vectors.

        Args:
            a: First embedding vector.
            b: Second embedding vector.

        Returns:
            Cosine similarity in [-1, 1].
        """
        a_arr = np.array(a, dtype=np.float32)
        b_arr = np.array(b, dtype=np.float32)
        dot = np.dot(a_arr, b_arr)
        norm_a = np.linalg.norm(a_arr)
        norm_b = np.linalg.norm(b_arr)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(dot / (norm_a * norm_b))

    @staticmethod
    def embedding_to_bytes(embedding: list[float]) -> bytes:
        """Serialize an embedding list to bytes for SQLite BLOB storage."""
        return np.array(embedding, dtype=np.float32).tobytes()

    @staticmethod
    def bytes_to_embedding(data: bytes) -> list[float]:
        """Deserialize bytes from SQLite back to a float list."""
        return np.frombuffer(data, dtype=np.float32).tolist()

    async def search_similar(
        self, query_embedding: list[float], limit: int = 20
    ) -> list[dict]:
        """Search memories by vector similarity (MVP: brute-force in Python).

        Args:
            query_embedding: The query embedding vector.
            limit: Maximum number of results.

        Returns:
            List of dicts with memory_id and similarity score, sorted descending.
        """
        from app.core.database import get_database

        db = get_database()
        rows = await db.fetch_all(
            "SELECT id, embedding FROM memories WHERE embedding IS NOT NULL"
        )

        scored: list[dict] = []
        for row in rows:
            try:
                mem_emb = self.bytes_to_embedding(row["embedding"])
                sim = self.cosine_similarity(query_embedding, mem_emb)
                scored.append({"memory_id": row["id"], "similarity": sim})
            except Exception:
                continue

        scored.sort(key=lambda x: x["similarity"], reverse=True)
        return scored[:limit]


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_instance: Optional[EmbeddingService] = None


def get_embedding_service() -> EmbeddingService:
    """Return (or create) the singleton EmbeddingService."""
    global _instance
    if _instance is None:
        from app.core.config import get_settings
        _instance = EmbeddingService(model_name=get_settings().local_embedding_model)
    return _instance
