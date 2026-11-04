"""
ContextOS Folder Scanner.

Performs an initial or manual full scan of a source folder, discovering
all supported files and queuing them for processing.
"""

import hashlib
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from app.core.database import get_database

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {
    ".pdf", ".txt", ".docx", ".csv",
    ".png", ".jpg", ".jpeg", ".webp",
    ".html", ".htm",
}


class FolderScanner:
    """Walks a directory tree and registers all supported files as documents."""

    async def scan_folder(self, source_id: str, path: str) -> dict[str, int]:
        """Scan *path* for supported files and create document + job records.

        Args:
            source_id: The source record ID this folder belongs to.
            path: Absolute filesystem path to scan.

        Returns:
            Dict with counts: ``discovered``, ``new``, ``skipped``, ``errors``.
        """
        db = get_database()
        stats = {"discovered": 0, "new": 0, "skipped": 0, "errors": 0}

        logger.info("Starting scan of %s for source %s", path, source_id)

        for root, _dirs, files in os.walk(path):
            for fname in files:
                fpath = os.path.join(root, fname)
                ext = Path(fpath).suffix.lower()
                if ext not in SUPPORTED_EXTENSIONS:
                    continue

                stats["discovered"] += 1

                try:
                    file_hash = self._compute_hash(fpath)
                    existing = await db.fetch_one(
                        "SELECT id FROM documents WHERE file_hash = ?", (file_hash,)
                    )
                    if existing:
                        stats["skipped"] += 1
                        continue

                    stat = os.stat(fpath)
                    doc_id = str(uuid4())
                    now = datetime.now(timezone.utc).isoformat()

                    await db.execute(
                        """INSERT INTO documents
                           (id, source_id, filename, file_hash, file_type, file_size,
                            original_path, created_at, modified_at, ingested_at, processing_status)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending')""",
                        (
                            doc_id, source_id, fname, file_hash,
                            ext.lstrip("."), stat.st_size, fpath, now, now, now,
                        ),
                    )

                    job_id = str(uuid4())
                    await db.execute(
                        """INSERT INTO processing_jobs
                           (id, document_id, job_type, status, created_at)
                           VALUES (?, ?, 'full', 'queued', ?)""",
                        (job_id, doc_id, now),
                    )
                    stats["new"] += 1

                except Exception:
                    logger.exception("Error scanning file %s", fpath)
                    stats["errors"] += 1

        await db.commit()

        # Update source last_synced timestamp
        now = datetime.now(timezone.utc).isoformat()
        await db.execute(
            "UPDATE sources SET last_synced = ? WHERE id = ?", (now, source_id)
        )
        await db.commit()

        logger.info(
            "Scan complete for source %s: %d discovered, %d new, %d skipped, %d errors",
            source_id, stats["discovered"], stats["new"], stats["skipped"], stats["errors"],
        )
        return stats

    @staticmethod
    def _compute_hash(path: str) -> str:
        """Return the SHA-256 hash of a file."""
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()
