"""
ContextOS Hybrid Search & Retrieval Engine.

Combines SQLite FTS5 lexical BM25-style search, dense vector cosine similarity,
temporal boundary filtering, and knowledge graph enrichment.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from app.core.database import get_database
from app.models.schemas import EntityResponse, SearchResponse, SearchResult
from app.services.embedding_service import get_embedding_service

logger = logging.getLogger(__name__)


class HybridSearchEngine:
    """Hybrid retrieval combining full-text search, dense embeddings, and metadata filters."""

    def __init__(self) -> None:
        self.db = get_database()
        self.embedding_service = get_embedding_service()

    async def search(
        self,
        query: str,
        filters: Optional[dict[str, Any]] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> SearchResponse:
        """Perform hybrid retrieval with Reciprocal Rank Fusion (RRF)."""
        filters = filters or {}
        cleaned_query = query.strip()
        if not cleaned_query:
            return SearchResponse(query=query, total=0, results=[], filters_applied=filters)

        # 1. Lexical search via FTS5
        fts_scores: dict[str, float] = {}
        try:
            # Clean words for FTS5 syntax
            fts_terms = " OR ".join([f'"{w}"' for w in cleaned_query.split() if len(w) > 1])
            if fts_terms:
                fts_sql = """
                    SELECT m.id, bm25(memories_fts) as rank_score
                    FROM memories_fts fts
                    JOIN memories m ON fts.rowid = m.rowid
                    WHERE memories_fts MATCH ?
                    LIMIT 100
                """
                fts_rows = await self.db.fetch_all(fts_sql, (fts_terms,))
                for i, row in enumerate(fts_rows):
                    # Invert negative BM25 rank score or use 1 / (rank + 60) RRF
                    fts_scores[row["id"]] = 1.0 / (60.0 + i + 1.0)
        except Exception as e:
            logger.debug("FTS5 query failed or empty: %s", e)

        # 2. Semantic dense vector search
        vector_scores: dict[str, float] = {}
        try:
            query_embedding = self.embedding_service.embed_text(cleaned_query)
            sim_results = await self.embedding_service.search_similar(query_embedding, limit=100)
            for r in sim_results:
                sim = float(r.get("similarity", 0.0))
                # Discard low-similarity noise. For all-MiniLM-L6-v2, < 0.38 is irrelevant
                if sim >= 0.38:
                    vector_scores[r["memory_id"]] = sim
        except Exception as e:
            logger.debug("Vector search error: %s", e)

        # 3. Combine scores with strict relevance filtering
        all_candidate_ids = set(fts_scores.keys()) | set(vector_scores.keys())
        if not all_candidate_ids:
            return SearchResponse(query=query, total=0, results=[], filters_applied=filters)

        combined_scores: dict[str, float] = {}
        for m_id in all_candidate_ids:
            has_fts = m_id in fts_scores
            v_score = vector_scores.get(m_id, 0.0)

            if has_fts and v_score > 0:
                combined_scores[m_id] = 0.5 + 0.5 * v_score
            elif v_score >= 0.38:
                combined_scores[m_id] = v_score
            elif has_fts:
                combined_scores[m_id] = 0.5

        # Discard any candidate below the minimum relevance threshold
        ranked_ids = [m_id for m_id, s in sorted(combined_scores.items(), key=lambda x: x[1], reverse=True) if s >= 0.38]

        if not ranked_ids:
            return SearchResponse(query=query, total=0, results=[], filters_applied=filters)

        # 4. Fetch full memory details & apply filters
        placeholders = ",".join(["?"] * len(ranked_ids))
        query_sql = f"""
            SELECT m.id, m.document_id, m.memory_type, m.content, m.summary, m.timestamp,
                   d.filename as document_filename, d.file_type, s.display_name as source_name, s.source_type
            FROM memories m
            JOIN documents d ON m.document_id = d.id
            JOIN sources s ON d.source_id = s.id
            WHERE m.id IN ({placeholders})
        """
        mem_rows = await self.db.fetch_all(query_sql, tuple(ranked_ids))
        row_dict = {r["id"]: r for r in mem_rows}

        results: list[SearchResult] = []
        for m_id in ranked_ids:
            if m_id not in row_dict:
                continue
            r = row_dict[m_id]

            # Apply filters
            if filters.get("file_type") and r["file_type"] != filters["file_type"]:
                continue
            if filters.get("source_type") and r["source_type"] != filters["source_type"]:
                continue
            if filters.get("date_from") and r["timestamp"] < filters["date_from"]:
                continue
            if filters.get("date_to") and r["timestamp"] > filters["date_to"]:
                continue

            # Fetch connected entities for context
            ent_rows = await self.db.fetch_all(
                """SELECT e.* FROM entities e
                   JOIN relationships rel ON (rel.subject_entity_id = e.id OR rel.object_entity_id = e.id)
                   WHERE rel.source_memory_id = ? LIMIT 5""",
                (m_id,),
            )
            entities = [
                EntityResponse(
                    id=e["id"],
                    entity_name=e["entity_name"],
                    entity_type=e["entity_type"],
                    first_seen=e["first_seen"],
                    last_seen=e["last_seen"],
                    mention_count=e["mention_count"],
                )
                for e in ent_rows
            ]

            results.append(
                SearchResult(
                    memory_id=r["id"],
                    content=r["content"],
                    summary=r.get("summary") or r["content"][:150],
                    score=round(combined_scores.get(m_id, 0.0), 4),
                    document_id=r["document_id"],
                    document_filename=r.get("document_filename"),
                    source_name=r.get("source_name"),
                    memory_type=r["memory_type"],
                    timestamp=r["timestamp"],
                    entities=entities,
                )
            )

        # Slice by offset and limit
        total_count = len(results)
        paged_results = results[offset : offset + limit]

        return SearchResponse(
            query=query,
            total=total_count,
            results=paged_results,
            filters_applied=filters,
        )
