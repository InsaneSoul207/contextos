"""
ContextOS Search & Chat API Router with PostgreSQL and Multi-turn Context Memory.

Provides hybrid search, chat with memory, multi-session management, and conversation history.
"""

import logging
from typing import Any, Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query

from app.models.schemas import (
    ChatMessage,
    ChatRequest,
    ChatResponse,
    SearchQuery,
    SearchResponse,
)
from app.services.chat_storage import get_chat_storage

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["search", "chat"])


@router.post("/search", response_model=SearchResponse)
async def search(body: SearchQuery) -> SearchResponse:
    """Perform hybrid search across all memories."""
    from app.retrieval.hybrid_search import HybridSearchEngine

    engine = HybridSearchEngine()
    return await engine.search(body.query, body.filters, body.limit, body.offset)


@router.get("/conversations")
async def list_conversations(limit: int = Query(default=50, ge=1, le=100)) -> list[dict[str, Any]]:
    """List all past chat conversations, ordered by most recent."""
    storage = get_chat_storage()
    return await storage.list_conversations(limit=limit)


@router.post("/conversations", status_code=201)
async def create_conversation(body: dict[str, Any] | None = None) -> dict[str, Any]:
    """Create a new chat conversation thread."""
    title = (body or {}).get("title", "New Chat")
    storage = get_chat_storage()
    return await storage.create_conversation(title=title)


@router.get("/conversations/{conversation_id}")
async def get_conversation(conversation_id: str) -> dict[str, Any]:
    """Get full conversation details and all message history."""
    storage = get_chat_storage()
    conv = await storage.get_conversation(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conv


@router.delete("/conversations/{conversation_id}", status_code=200)
async def delete_conversation(conversation_id: str) -> dict[str, str]:
    """Delete a conversation thread and its messages."""
    storage = get_chat_storage()
    await storage.delete_conversation(conversation_id)
    return {"status": "deleted", "conversation_id": conversation_id}


@router.get("/chat/storage-status")
async def get_storage_status() -> dict[str, Any]:
    """Check whether chats are being saved to PostgreSQL or SQLite."""
    storage = get_chat_storage()
    return await storage.get_storage_status()


@router.post("/chat/storage-config")
async def update_storage_config(body: dict[str, Any]) -> dict[str, Any]:
    """Configure PostgreSQL connection string or switch to SQLite."""
    postgres_url = (body or {}).get("postgres_url", "")
    storage = get_chat_storage()
    return await storage.configure_postgres(postgres_url)


@router.post("/chat", response_model=ChatResponse)
async def chat(body: ChatRequest) -> ChatResponse:
    """Chat with memory — maintains multi-turn context memory of last 5 chats and saves to PostgreSQL/SQLite."""
    from datetime import datetime, timezone
    from app.retrieval.hybrid_search import HybridSearchEngine
    from app.services.llm_service import get_llm_service

    storage = get_chat_storage()
    conv_id = body.conversation_id

    # 1. Resolve or create conversation
    if not conv_id:
        clean_title = body.message.replace("\n", " ").strip()[:45]
        new_conv = await storage.create_conversation(title=clean_title)
        conv_id = new_conv["id"]

    # 2. Retrieve last 5 exchanges (10 messages) for multi-turn conversational context memory
    recent_history = await storage.get_recent_history(conv_id, max_exchanges=5)
    history_messages = [
        ChatMessage(role=m["role"], content=m["content"])
        for m in recent_history
    ]
    if body.history:
        history_messages = body.history[-10:]

    # 3. Save incoming user message to persistent database (PostgreSQL/SQLite)
    await storage.add_message(
        conversation_id=conv_id,
        role="user",
        content=body.message,
    )

    # 4. Contextualize query for multi-turn coreference (e.g. "it", "this", "that" -> "ContextOS")
    from app.retrieval.query_contextualizer import contextualize_chat_query

    conv_data = await storage.get_conversation(conv_id)
    conv_title = conv_data.get("title") if conv_data else None

    search_query, active_subject = contextualize_chat_query(
        current_message=body.message,
        history=history_messages,
        conversation_title=conv_title,
    )

    # 5. Perform hybrid search across personal memory using contextualized search query
    engine = HybridSearchEngine()
    search_results = await engine.search(search_query, limit=10)

    # If an active subject was identified (e.g. "ContextOS"), boost results matching the intended subject
    if active_subject:
        subj_lower = active_subject.lower()
        for r in search_results.results:
            fn = (r.document_filename or "").lower()
            sn = (r.source_name or "").lower()
            cnt = (r.content or "").lower()
            if subj_lower in fn or subj_lower in sn:
                r.score = min(1.0, r.score + 0.20)
            elif subj_lower in cnt:
                r.score = min(1.0, r.score + 0.08)
        search_results.results.sort(key=lambda x: x.score, reverse=True)

    # Filter out low-confidence noise (< 0.35)
    relevant_results = [r for r in search_results.results if r.score >= 0.35]

    # 6. Generate conversational ChatGPT-style response with the 5 recent context memories
    llm = get_llm_service()
    response = await llm.generate(
        query=body.message,
        context=relevant_results,
        history=history_messages,
    )

    answer_text = response["answer"]
    sources_to_save = [
        {
            "document_filename": r.document_filename or r.source_name,
            "content": r.content[:200],
            "score": round(r.score, 3),
        }
        for r in relevant_results[:5]
    ]

    # 6. Save assistant response to persistent database (PostgreSQL/SQLite)
    asst_msg = await storage.add_message(
        conversation_id=conv_id,
        role="assistant",
        content=answer_text,
        sources=sources_to_save,
    )

    return ChatResponse(
        answer=answer_text,
        conversation_id=conv_id,
        message={
            "id": asst_msg["id"],
            "role": "assistant",
            "content": answer_text,
            "timestamp": asst_msg["timestamp"],
        },
        sources=relevant_results[:5],
        llm_used=response.get("llm_used", False),
    )
