"""
ContextOS Document Processing Pipeline & Worker Queue.

Orchestrates file reading, multimodal extraction, chunking, embedding generation,
entity/relation discovery, and graph updates.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from app.core.database import get_database
from app.graph.knowledge_graph import KnowledgeGraphManager
from app.ml.classifier.inference import DocumentClassifierInferenceEngine
from app.processing.chunker import TextChunker
from app.processing.entity_extractor import EntityExtractor
from app.processing.extractors import get_extractor_for_file
from app.services.embedding_service import get_embedding_service

logger = logging.getLogger(__name__)


class ProcessingPipeline:
    """Processes individual documents end-to-end into searchable memories & knowledge graph."""

    def __init__(self) -> None:
        self.chunker = TextChunker(chunk_size=512, overlap=64)
        self.entity_extractor = EntityExtractor()
        self.graph_manager = KnowledgeGraphManager()
        self.embedding_service = get_embedding_service()
        try:
            self.classifier = DocumentClassifierInferenceEngine.get_instance()
        except Exception:
            self.classifier = None

    async def process_document(self, document_id: str) -> bool:
        """Execute the full processing pipeline for a document."""
        db = get_database()
        doc = await db.fetch_one("SELECT * FROM documents WHERE id = ?", (document_id,))
        if not doc:
            logger.error("Document %s not found for processing.", document_id)
            return False

        orig_path = doc["original_path"]
        path_obj = Path(orig_path)
        if not path_obj.exists():
            logger.error("Original file %s does not exist.", orig_path)
            await db.execute(
                "UPDATE documents SET processing_status = 'error' WHERE id = ?",
                (document_id,),
            )
            await db.commit()
            return False

        # Mark in-progress
        await db.execute(
            "UPDATE documents SET processing_status = 'processing' WHERE id = ?",
            (document_id,),
        )
        await db.commit()

        try:
            # 1. Content Extraction
            extractor = get_extractor_for_file(path_obj)
            if not extractor:
                logger.warning("No extractor available for %s", path_obj)
                await db.execute(
                    "UPDATE documents SET processing_status = 'unsupported' WHERE id = ?",
                    (document_id,),
                )
                await db.commit()
                return False

            result = await extractor.extract(path_obj)
            if not result.text or not result.text.strip():
                logger.info("Document %s extracted empty text.", document_id)
                await db.execute(
                    "UPDATE documents SET processing_status = 'completed' WHERE id = ?",
                    (document_id,),
                )
                await db.commit()
                return True

            # 2. Chunking
            chunks = self.chunker.chunk_text(
                result.text, metadata=result.metadata
            )
            if not chunks:
                chunks = self.chunker.chunk_text(result.text[:1000])

            # 3. Generate Embeddings for chunks
            chunk_texts = [c.content for c in chunks]
            try:
                embeddings = self.embedding_service.embed_batch(chunk_texts)
            except Exception as e:
                logger.warning("Embedding generation fallback: %s", e)
                embeddings = [[0.0] * 384 for _ in chunks]

            # 4. Save Memories
            now = datetime.now().isoformat()
            memory_ids: list[str] = []

            # 4.1 Semantic Category Classification via Custom Transformer Encoder
            predicted_category: Optional[str] = None
            if self.classifier is not None and result.text:
                try:
                    prediction = self.classifier.predict(result.text[:1000])
                    predicted_category = prediction.category
                    logger.info(
                        "Document %s classified as '%s' (confidence: %.2f)",
                        doc["filename"],
                        predicted_category,
                        prediction.confidence,
                    )
                except Exception as e:
                    logger.warning("Document classification failed: %s", e)

            for i, chunk in enumerate(chunks):
                mem_id = str(uuid.uuid4())
                memory_ids.append(mem_id)
                emb_bytes = self.embedding_service.embedding_to_bytes(embeddings[i])
                summary = chunk.content[:180] + ("..." if len(chunk.content) > 180 else "")

                await db.execute(
                    """INSERT INTO memories
                       (id, document_id, memory_type, content, summary, embedding, timestamp, confidence, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        mem_id,
                        document_id,
                        result.file_type,
                        chunk.content,
                        summary,
                        emb_bytes,
                        doc.get("modified_at") or now,
                        1.0,
                        now,
                    ),
                )

            # 5. Entity & Relationship Discovery
            extracted_entities = self.entity_extractor.extract_entities(result.text)
            extracted_rels = self.entity_extractor.extract_relationships(
                extracted_entities, result.text, document_title=doc["filename"]
            )

            # Insert entities into graph
            entity_id_map: dict[str, str] = {}
            for ent in extracted_entities:
                e_id = await self.graph_manager.upsert_entity(ent.name, ent.entity_type)
                entity_id_map[ent.name] = e_id

            # Insert category node and document linkage into graph
            if predicted_category:
                cat_id = await self.graph_manager.upsert_entity(predicted_category, "Category")
                doc_title = doc["filename"]
                doc_id = await self.graph_manager.upsert_entity(doc_title, "Document")
                primary_mem_id = memory_ids[0] if memory_ids else None
                await self.graph_manager.add_relationship(
                    subject_id=doc_id,
                    predicate="Categorized As",
                    object_id=cat_id,
                    source_memory_id=primary_mem_id,
                    confidence=0.95,
                )

            # Insert relationships into graph
            primary_mem_id = memory_ids[0] if memory_ids else None
            for rel in extracted_rels:
                subj_id = entity_id_map.get(rel.subject)
                obj_id = entity_id_map.get(rel.object)
                if subj_id and obj_id:
                    await self.graph_manager.add_relationship(
                        subject_id=subj_id,
                        predicate=rel.predicate,
                        object_id=obj_id,
                        source_memory_id=primary_mem_id,
                        confidence=rel.confidence,
                        valid_from=rel.valid_from,
                        valid_to=rel.valid_to,
                    )

            # Mark Document Completed
            await db.execute(
                "UPDATE documents SET processing_status = 'completed', ingested_at = ? WHERE id = ?",
                (now, document_id),
            )
            await db.commit()
            logger.info("Successfully processed document %s (%s memories created).", doc['filename'], len(memory_ids))
            return True

        except Exception as e:
            logger.exception("Error processing document %s: %s", document_id, e)
            await db.execute(
                "UPDATE documents SET processing_status = 'failed' WHERE id = ?",
                (document_id,),
            )
            await db.commit()
            return False


class ProcessingQueue:
    """Background worker continuously polling and executing processing jobs."""

    def __init__(self, poll_interval: float = 3.0) -> None:
        self.poll_interval = poll_interval
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self.pipeline = ProcessingPipeline()

    async def start(self) -> None:
        """Start the background processing loop."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._worker_loop())
        logger.info("ContextOS ProcessingQueue started.")

    async def stop(self) -> None:
        """Stop the background processing loop gracefully."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("ContextOS ProcessingQueue stopped.")

    async def _worker_loop(self) -> None:
        db = get_database()
        while self._running:
            try:
                # Find queued jobs or pending documents
                job = await db.fetch_one(
                    "SELECT * FROM processing_jobs WHERE status = 'queued' ORDER BY created_at ASC LIMIT 1"
                )
                if job:
                    job_id = job["id"]
                    doc_id = job["document_id"]
                    now = datetime.now().isoformat()
                    await db.execute(
                        "UPDATE processing_jobs SET status = 'in_progress', started_at = ? WHERE id = ?",
                        (now, job_id),
                    )
                    await db.commit()

                    success = await self.pipeline.process_document(doc_id)
                    finished_at = datetime.now().isoformat()
                    status = "completed" if success else "failed"
                    await db.execute(
                        "UPDATE processing_jobs SET status = ?, completed_at = ? WHERE id = ?",
                        (status, finished_at, job_id),
                    )
                    await db.commit()
                    continue

                # Check for documents in 'pending' status without a job
                pending_doc = await db.fetch_one(
                    "SELECT id FROM documents WHERE processing_status = 'pending' LIMIT 1"
                )
                if pending_doc:
                    await self.pipeline.process_document(pending_doc["id"])
                    continue

            except Exception as e:
                logger.error("Error in processing worker loop: %s", e)

            await asyncio.sleep(self.poll_interval)


_queue_instance: Optional[ProcessingQueue] = None


def get_processing_queue() -> ProcessingQueue:
    """Return the global processing queue worker instance."""
    global _queue_instance
    if _queue_instance is None:
        _queue_instance = ProcessingQueue()
    return _queue_instance
