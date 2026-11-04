"""
ContextOS Main Application Entry Point.

FastAPI application providing endpoints for desktop UI and background services.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import Depends, FastAPI, HTTPException, Request, Security, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security.api_key import APIKeyHeader

from app.api import collections, documents, graph, memories, ml, search, sources, stats
from app.core.config import get_settings
from app.core.database import get_database, init_db
from app.ingestion.watcher import get_file_watcher
from app.processing.pipeline import get_processing_queue

logger = logging.getLogger("contextos")
settings = get_settings()

logging.basicConfig(
    level=settings.log_level.upper(),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager initializing DB and background workers."""
    logger.info("Initializing ContextOS Storage & Database...")
    await init_db()

    # Start Processing Queue background worker
    queue = get_processing_queue()
    await queue.start()

    # Start Watchdog Folder Ingestion Service
    watcher = get_file_watcher()
    try:
        watcher.start()
    except Exception as e:
        logger.warning("Could not auto-start watcher: %s", e)

    logger.info("ContextOS AI Backend online and ready.")
    yield

    logger.info("ContextOS AI Backend shutting down...")
    await queue.stop()
    try:
        watcher.stop()
    except Exception:
        pass
    await get_database().disconnect()
    logger.info("ContextOS AI Backend shut down complete.")


app = FastAPI(
    title="ContextOS AI Backend",
    description="Personal multimodal, temporal and relational memory infrastructure",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS configuration for desktop and web/extension access
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:1420",
        "http://127.0.0.1:1420",
        "tauri://localhost",
        "http://tauri.localhost",
        "*",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers
app.include_router(sources.router)
app.include_router(documents.router)
app.include_router(memories.router)
app.include_router(collections.router)
app.include_router(search.router)
app.include_router(graph.router)
app.include_router(stats.router)
app.include_router(ml.router)


@app.get("/health", tags=["system"])
async def health_check() -> dict:
    """System health check endpoint."""
    return {
        "status": "healthy",
        "version": "0.1.0",
        "service": "ContextOS AI Backend",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=False,
    )
