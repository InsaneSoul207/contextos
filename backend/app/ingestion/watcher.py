"""
ContextOS File Watcher.

Uses the ``watchdog`` library to monitor source folders for file changes
and queue documents for processing.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import os
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from uuid import uuid4

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {
    ".pdf", ".txt", ".docx", ".csv",
    ".png", ".jpg", ".jpeg", ".webp",
    ".html", ".htm",
}


def _is_supported(path: str) -> bool:
    """Return True if the file extension is supported."""
    return Path(path).suffix.lower() in SUPPORTED_EXTENSIONS


def _compute_file_hash(path: str) -> str:
    """Return the SHA-256 hash of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


class _DebouncedHandler(FileSystemEventHandler):
    """Watchdog handler that debounces events to avoid processing files
    that are still being written to."""

    def __init__(self, watcher: FileWatcher, source_id: str, debounce_seconds: float = 2.0) -> None:
        super().__init__()
        self._watcher = watcher
        self._source_id = source_id
        self._debounce = debounce_seconds
        self._pending: dict[str, float] = {}
        self._lock = threading.Lock()
        self._timer: Optional[threading.Timer] = None
        self._start_flush_timer()

    def _start_flush_timer(self) -> None:
        """Start a recurring flush timer."""
        self._timer = threading.Timer(self._debounce, self._flush)
        self._timer.daemon = True
        self._timer.start()

    def _flush(self) -> None:
        """Process all debounced events whose delay has elapsed."""
        now = time.time()
        to_process: list[str] = []
        with self._lock:
            for path, ts in list(self._pending.items()):
                if now - ts >= self._debounce:
                    to_process.append(path)
                    del self._pending[path]

        for path in to_process:
            if os.path.exists(path):
                self._watcher._enqueue_file(self._source_id, path, "created")

        self._start_flush_timer()

    def on_created(self, event: FileSystemEvent) -> None:
        if event.is_directory or not _is_supported(event.src_path):
            if not event.is_directory:
                logger.debug("Unsupported file type: %s", event.src_path)
            return
        with self._lock:
            self._pending[event.src_path] = time.time()

    def on_modified(self, event: FileSystemEvent) -> None:
        if event.is_directory or not _is_supported(event.src_path):
            return
        with self._lock:
            self._pending[event.src_path] = time.time()

    def on_deleted(self, event: FileSystemEvent) -> None:
        if event.is_directory or not _is_supported(event.src_path):
            return
        self._watcher._enqueue_file(self._source_id, event.src_path, "deleted")

    def on_moved(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        if hasattr(event, "dest_path") and _is_supported(event.dest_path):
            self._watcher._enqueue_file(
                self._source_id, event.dest_path, "moved", old_path=event.src_path
            )

    def stop(self) -> None:
        if self._timer:
            self._timer.cancel()


class FileWatcher:
    """Monitors multiple source directories for file changes."""

    def __init__(self) -> None:
        self._observer = Observer()
        self._watches: dict[str, tuple] = {}  # source_id -> (watch, handler)
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._started = False

    def start(self, loop: Optional[asyncio.AbstractEventLoop] = None) -> None:
        """Start the observer thread."""
        if self._started:
            return
        self._loop = loop or asyncio.get_event_loop()
        self._observer.start()
        self._started = True
        logger.info("FileWatcher started.")

    def stop(self) -> None:
        """Stop the observer thread."""
        for _sid, (watch, handler) in self._watches.items():
            handler.stop()
        self._observer.stop()
        self._observer.join(timeout=5)
        self._started = False
        logger.info("FileWatcher stopped.")

    def add_watch(self, source_id: str, path: str) -> None:
        """Add a directory watch for a given source."""
        if source_id in self._watches:
            logger.warning("Watch already exists for source %s", source_id)
            return
        if not os.path.isdir(path):
            logger.error("Cannot watch non-directory path: %s", path)
            return
        handler = _DebouncedHandler(self, source_id)
        watch = self._observer.schedule(handler, path, recursive=True)
        self._watches[source_id] = (watch, handler)
        logger.info("Watching source %s at %s", source_id, path)

    def remove_watch(self, source_id: str) -> None:
        """Remove the directory watch for a source."""
        entry = self._watches.pop(source_id, None)
        if entry:
            watch, handler = entry
            handler.stop()
            self._observer.unschedule(watch)
            logger.info("Stopped watching source %s", source_id)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _enqueue_file(
        self,
        source_id: str,
        path: str,
        event_type: str,
        old_path: str | None = None,
    ) -> None:
        """Schedule the async DB work on the event loop."""
        if self._loop is None:
            logger.error("No event loop available for enqueue")
            return
        asyncio.run_coroutine_threadsafe(
            self._handle_file_event(source_id, path, event_type, old_path),
            self._loop,
        )

    async def _handle_file_event(
        self, source_id: str, path: str, event_type: str, old_path: str | None
    ) -> None:
        """Process a file event and update the database."""
        from app.core.database import get_database

        db = get_database()

        try:
            if event_type == "deleted":
                await db.execute(
                    "UPDATE documents SET processing_status = 'deleted' WHERE original_path = ? AND source_id = ?",
                    (path, source_id),
                )
                await db.commit()
                logger.info("Marked deleted: %s", path)
                return

            if event_type == "moved" and old_path:
                await db.execute(
                    "UPDATE documents SET original_path = ?, filename = ? WHERE original_path = ? AND source_id = ?",
                    (path, os.path.basename(path), old_path, source_id),
                )
                await db.commit()
                logger.info("Updated moved file: %s -> %s", old_path, path)
                return

            # created or modified
            file_hash = _compute_file_hash(path)
            existing = await db.fetch_one(
                "SELECT id FROM documents WHERE file_hash = ?", (file_hash,)
            )
            if existing:
                logger.debug("Duplicate file skipped: %s", path)
                return

            stat = os.stat(path)
            ext = Path(path).suffix.lower().lstrip(".")
            doc_id = str(uuid4())
            now = datetime.now(timezone.utc).isoformat()

            await db.execute(
                """INSERT INTO documents
                   (id, source_id, filename, file_hash, file_type, file_size, original_path,
                    created_at, modified_at, ingested_at, processing_status)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending')""",
                (
                    doc_id, source_id, os.path.basename(path), file_hash, ext,
                    stat.st_size, path, now, now, now,
                ),
            )

            job_id = str(uuid4())
            await db.execute(
                """INSERT INTO processing_jobs (id, document_id, job_type, status, created_at)
                   VALUES (?, ?, 'full', 'queued', ?)""",
                (job_id, doc_id, now),
            )
            await db.commit()
            logger.info("Queued document for processing: %s (%s)", os.path.basename(path), doc_id)

        except Exception:
            logger.exception("Error handling file event for %s", path)


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_watcher: Optional[FileWatcher] = None


def get_file_watcher() -> FileWatcher:
    """Return the module-level FileWatcher singleton."""
    global _watcher
    if _watcher is None:
        _watcher = FileWatcher()
    return _watcher
