"""
ContextOS Pydantic Models / Schemas.

Defines request and response schemas for every API resource.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field, model_validator


# ---------------------------------------------------------------------------
# Sources
# ---------------------------------------------------------------------------

class SourceCreate(BaseModel):
    """Request body for creating a new monitored source."""
    source_type: str = Field(default="folder", description="Type of source: folder, upload, etc.")
    source_path: Optional[str] = Field(None, description="Absolute path to the source folder.")
    path: Optional[str] = Field(None, description="Alias for source_path")
    display_name: Optional[str] = Field(None, description="Human-readable name.")

    @model_validator(mode="after")
    def validate_path(self) -> SourceCreate:
        if not self.source_path and self.path:
            self.source_path = self.path
        if not self.source_path:
            raise ValueError("source_path or path is required")
        return self


class SourceUpdate(BaseModel):
    """Request body for updating a source."""
    display_name: Optional[str] = None
    status: Optional[str] = None  # active, paused


class SourceResponse(BaseModel):
    """Public representation of a source."""
    id: str
    source_type: str
    source_path: str
    display_name: str
    permission_status: str
    last_synced: Optional[str] = None
    status: str
    created_at: str
    document_count: int = 0


# ---------------------------------------------------------------------------
# Documents
# ---------------------------------------------------------------------------

class DocumentResponse(BaseModel):
    """Summary representation of a document."""
    id: str
    source_id: str
    filename: str
    file_type: str
    file_size: int
    processing_status: str
    ingested_at: Optional[str] = None
    created_at: str


class DocumentDetail(DocumentResponse):
    """Full document detail including memories."""
    file_hash: Optional[str] = None
    original_path: str = ""
    modified_at: Optional[str] = None
    memories: list[MemoryResponse] = []


# ---------------------------------------------------------------------------
# Memories
# ---------------------------------------------------------------------------

class MemoryResponse(BaseModel):
    """Summary representation of a memory."""
    id: str
    document_id: str
    memory_type: str
    content: str
    summary: Optional[str] = None
    timestamp: str
    confidence: float = 1.0
    created_at: str
    title: Optional[str] = None
    file_type: Optional[str] = None
    filepath: Optional[str] = None


class MemoryDetail(MemoryResponse):
    """Full memory detail with related entities."""
    document_filename: Optional[str] = None
    source_name: Optional[str] = None
    entities: list[EntityResponse] = []
    relationships: list[RelationshipResponse] = []


class MemoryCreate(BaseModel):
    """Request body for manually creating a memory."""
    document_id: str
    memory_type: str = "text"
    content: str
    summary: Optional[str] = None
    confidence: float = 1.0


# ---------------------------------------------------------------------------
# Entities
# ---------------------------------------------------------------------------

class EntityResponse(BaseModel):
    """Summary representation of an entity."""
    id: str
    entity_name: str
    entity_type: str
    first_seen: str
    last_seen: str
    mention_count: int = 1


class EntityDetail(EntityResponse):
    """Entity with its relationships."""
    relationships: list[RelationshipResponse] = []


# ---------------------------------------------------------------------------
# Relationships
# ---------------------------------------------------------------------------

class RelationshipResponse(BaseModel):
    """Representation of a relationship between two entities."""
    id: str
    subject_entity_id: str
    predicate: str
    object_entity_id: str
    source_memory_id: Optional[str] = None
    confidence: float = 1.0
    valid_from: Optional[str] = None
    valid_to: Optional[str] = None
    created_at: str
    subject_name: Optional[str] = None
    object_name: Optional[str] = None


class RelationshipCreate(BaseModel):
    """Request body for creating a relationship."""
    subject_entity_id: str
    predicate: str
    object_entity_id: str
    source_memory_id: Optional[str] = None
    confidence: float = 1.0


# ---------------------------------------------------------------------------
# Processing
# ---------------------------------------------------------------------------

class ProcessingJobResponse(BaseModel):
    """Representation of a processing job."""
    id: str
    document_id: str
    job_type: str
    status: str
    error: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    created_at: str


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------

class SearchQuery(BaseModel):
    """Search request body."""
    query: str = Field(..., min_length=1)
    filters: Optional[dict[str, Any]] = Field(
        None,
        description=(
            "Optional filters: source_type, date_from, date_to, file_type, topic"
        ),
    )
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


class SearchResult(BaseModel):
    """A single search result."""
    memory_id: str
    content: str
    summary: Optional[str] = None
    score: float
    document_id: str
    document_filename: Optional[str] = None
    source_name: Optional[str] = None
    memory_type: str = "text"
    timestamp: str = ""
    entities: list[EntityResponse] = []


class SearchResponse(BaseModel):
    """Aggregated search response."""
    query: str
    total: int
    results: list[SearchResult]
    filters_applied: dict[str, Any] = {}


# ---------------------------------------------------------------------------
# Chat
# ---------------------------------------------------------------------------

class ChatMessage(BaseModel):
    """A single chat message."""
    role: str = Field(..., description="'user' or 'assistant'")
    content: str


class ChatRequest(BaseModel):
    """Chat request body."""
    message: str = Field(..., min_length=1)
    conversation_id: Optional[str] = None
    history: list[ChatMessage] = []


class ChatResponse(BaseModel):
    """Chat response with source citations."""
    answer: str
    message: Optional[dict[str, Any]] = None
    conversation_id: Optional[str] = None
    sources: list[Any] = []
    llm_used: bool = False


# ---------------------------------------------------------------------------
# Stats / Dashboard
# ---------------------------------------------------------------------------

class StatsResponse(BaseModel):
    """Dashboard statistics."""
    total_memories: int = 0
    total_documents: int = 0
    total_entities: int = 0
    total_relationships: int = 0
    total_sources: int = 0
    recent_documents: list[DocumentResponse] = []
    processing_queue_size: int = 0


# ---------------------------------------------------------------------------
# Graph
# ---------------------------------------------------------------------------

class GraphNode(BaseModel):
    """A node in the knowledge graph visualisation."""
    id: str
    label: str
    type: str
    mention_count: int = 1


class GraphEdge(BaseModel):
    """An edge in the knowledge graph visualisation."""
    id: str
    source: str
    target: str
    label: str
    confidence: float = 1.0


class GraphData(BaseModel):
    """Full graph payload for the frontend."""
    nodes: list[GraphNode] = []
    edges: list[GraphEdge] = []


# ---------------------------------------------------------------------------
# Rebuild forward refs so nested models resolve correctly
# ---------------------------------------------------------------------------

DocumentDetail.model_rebuild()
MemoryDetail.model_rebuild()
EntityDetail.model_rebuild()
