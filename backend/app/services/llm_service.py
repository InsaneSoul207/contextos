"""
ContextOS LLM Service.

Provides a pluggable LLM abstraction.  When no real LLM is configured the
service falls back to a template-based answer formatter that presents
retrieved memories as a readable response with source citations.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, Optional

from app.core.config import get_settings
from app.models.schemas import ChatMessage, SearchResult

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Abstract base
# ---------------------------------------------------------------------------

class LLMProvider(ABC):
    """Base class for LLM providers."""

    @abstractmethod
    async def generate(
        self,
        query: str,
        context: list[SearchResult],
        history: list[ChatMessage] | None = None,
    ) -> dict[str, Any]:
        """Generate an answer given a query and retrieved context.

        Returns:
            dict with at least ``answer`` (str) and ``llm_used`` (bool).
        """
        ...


# ---------------------------------------------------------------------------
# Template-based (no LLM)
# ---------------------------------------------------------------------------

class LocalTemplateProvider(LLMProvider):
    """Fallback provider that formats retrieved memories into a natural, conversational response
    without calling an external LLM."""

    async def generate(
        self,
        query: str,
        context: list[SearchResult],
        history: list[ChatMessage] | None = None,
    ) -> dict[str, Any]:
        """Format context memories into a conversational, human-friendly answer."""
        if not context:
            return {
                "answer": (
                    "I searched through your personal memory, but I couldn't find anything "
                    f"specifically related to **\"{query}\"** just yet.\n\n"
                    "You can capture this topic using the **+ Quick Capture** button above, "
                    "or by saving a webpage via the ContextOS browser extension!"
                ),
                "llm_used": False,
            }

        # Clean topic from query
        clean_topic = query.strip()
        for prefix in [
            "what do my memories tell me about",
            "what does my memory say about",
            "what do you know about",
            "tell me about",
            "what is",
            "who is",
            "explain",
        ]:
            if clean_topic.lower().startswith(prefix):
                clean_topic = clean_topic[len(prefix):].strip(" ?:.")
                break

        # Collect unique insights
        unique_snippets: list[str] = []
        seen_texts = set()
        for r in context[:5]:
            text = r.content.strip()
            if text and text not in seen_texts:
                seen_texts.add(text)
                unique_snippets.append(text)

        lines: list[str] = [
            f"Based on your saved memories and notes, here is what you have on **{clean_topic or query}**:\n"
        ]

        # Conversational breakdown of the memories
        for idx, text in enumerate(unique_snippets, 1):
            if len(unique_snippets) == 1:
                lines.append(f"{text}\n")
            else:
                lines.append(f"• **Key Insight #{idx}**: {text}\n")

        lines.append(
            "\nYou can click any of the cited sources below to inspect the original captures, "
            "or ask me to explore related notes in your knowledge graph!"
        )

        return {"answer": "\n".join(lines), "llm_used": False}


# ---------------------------------------------------------------------------
# OpenAI-compatible provider
# ---------------------------------------------------------------------------

class OpenAIProvider(LLMProvider):
    """Provider that calls an OpenAI-compatible API (if configured)."""

    def __init__(self, api_key: str, model: str, base_url: str = "https://api.openai.com/v1") -> None:
        self._api_key = api_key
        self._model = model
        self._base_url = base_url.rstrip("/")

    async def generate(
        self,
        query: str,
        context: list[SearchResult],
        history: list[ChatMessage] | None = None,
    ) -> dict[str, Any]:
        """Call the OpenAI chat completions endpoint."""
        import httpx

        ctx_text = "\n\n".join(
            f"[Source: {r.document_filename or 'personal note'}]\n{r.content}"
            for r in context[:8]
        )

        system_msg = (
            "You are ContextOS, the user's personal AI memory and knowledge companion. "
            "You talk directly to the user in a natural, warm, insightful, and highly conversational tone—just like ChatGPT.\n\n"
            "Guidelines:\n"
            "- Speak naturally to the user (e.g. 'From what you've saved...', 'In your notes...').\n"
            "- Synthesize and explain the context thoroughly rather than quoting raw database fields or filenames.\n"
            "- Use clean markdown formatting with paragraphs and bullet points.\n"
            "- If the saved context is incomplete, explain what you know and politely note what's missing.\n\n"
            f"--- PERSONAL MEMORY CONTEXT ---\n{ctx_text}\n--- END CONTEXT ---"
        )

        messages: list[dict[str, str]] = [{"role": "system", "content": system_msg}]
        if history:
            for msg in history[-6:]:
                messages.append({"role": msg.role, "content": msg.content})
        messages.append({"role": "user", "content": query})

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(
                    f"{self._base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self._api_key}",
                        "Content-Type": "application/json",
                    },
                    json={"model": self._model, "messages": messages, "temperature": 0.4},
                )
                resp.raise_for_status()
                data = resp.json()
                answer = data["choices"][0]["message"]["content"]
                return {"answer": answer, "llm_used": True}
        except Exception:
            logger.exception("OpenAI API call failed, falling back to template")
            fallback = LocalTemplateProvider()
            return await fallback.generate(query, context, history)


# ---------------------------------------------------------------------------
# Ollama Local Offline Provider
# ---------------------------------------------------------------------------

class OllamaProvider(LLMProvider):
    """Provider for local offline LLMs running via Ollama (e.g. llama3.1, qwen, deepseek)."""

    def __init__(self, base_url: str = "http://127.0.0.1:11434", model: str | None = None) -> None:
        self._base_url = base_url.rstrip("/")
        self._preferred_model = model

    async def _resolve_model(self) -> str:
        """Find the best available local model running on Ollama."""
        if self._preferred_model and self._preferred_model not in ("auto", "local"):
            return self._preferred_model

        try:
            import httpx
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self._base_url}/api/tags")
                if resp.status_code == 200:
                    models = [m.get("name", "") for m in resp.json().get("models", [])]
                    # Priority preference order for high-quality conversational LLMs
                    for candidate in ["llama3.1:8b", "llama3.1", "qwen3:latest", "deepseek-r1:7b", "llama3:latest", "mistral:latest"]:
                        if candidate in models:
                            return candidate
                    # Pick first non-embedding text model
                    text_models = [m for m in models if "embed" not in m.lower() and "moondream" not in m.lower()]
                    if text_models:
                        return text_models[0]
        except Exception as e:
            logger.warning("Could not auto-detect Ollama models: %s", e)

        return "llama3.1:8b"

    async def generate(
        self,
        query: str,
        context: list[SearchResult],
        history: list[ChatMessage] | None = None,
    ) -> dict[str, Any]:
        import httpx

        # If no relevant context in personal memory, decline immediately with no hallucinations
        if not context:
            fallback = LocalTemplateProvider()
            return await fallback.generate(query, context, history)

        model = await self._resolve_model()
        logger.info("Generating response with Ollama model: %s", model)

        ctx_text = "\n\n".join(
            f"[Source: {r.document_filename or 'personal note'}]\n{r.content}"
            for r in context[:8]
        )

        system_msg = (
            "You are ContextOS, a strictly grounded personal AI memory companion.\n"
            "You talk directly to the user in a natural, warm, and articulate tone—just like ChatGPT.\n\n"
            "STRICT GROUNDING INSTRUCTIONS:\n"
            "1. Answer ONLY using the user's personal memory context provided below.\n"
            "2. If the user's question asks about something NOT mentioned in the personal memory context below, DO NOT attempt to answer from general world knowledge or invent explanations. You must clearly state: 'I searched your personal memory, but I don't have any saved documents or notes about [topic].'\n"
            "3. Speak conversationally as a personal thinking assistant (e.g. 'Based on what you've saved...', 'In your notes on...').\n"
            "4. Never dump raw file extensions (.json), database IDs, or match scores into your response.\n"
            "5. CONVERSATION CONTINUITY & PRONOUN RESOLUTION: When the user asks a follow-up question using pronouns ('it', 'this', 'that', 'the project', 'the folder'), resolve the pronoun to the subject of the ongoing conversation. Never switch to an unrelated document (e.g. do NOT answer with GeoBERT if the user was asking about ContextOS).\n\n"
            f"--- PERSONAL MEMORY CONTEXT ---\n{ctx_text}\n--- END CONTEXT ---"
        )

        messages: list[dict[str, str]] = [{"role": "system", "content": system_msg}]
        if history:
            for msg in history[-4:]:
                messages.append({"role": msg.role, "content": msg.content})
        messages.append({"role": "user", "content": query})

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                # Use Ollama /api/chat endpoint
                resp = await client.post(
                    f"{self._base_url}/api/chat",
                    json={
                        "model": model,
                        "messages": messages,
                        "stream": False,
                    },
                )
                if resp.status_code == 200:
                    data = resp.json()
                    answer = data.get("message", {}).get("content", "").strip()
                    if answer:
                        return {"answer": answer, "llm_used": True, "provider": f"ollama ({model})"}
        except Exception as e:
            logger.warning("Ollama chat generation failed: %s", e)

        # Fallback to conversational template
        fallback = LocalTemplateProvider()
        return await fallback.generate(query, context, history)


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

_instance: Optional[LLMProvider] = None


def get_llm_service() -> LLMProvider:
    """Return the configured LLM provider (singleton)."""
    global _instance
    if _instance is not None:
        return _instance

    settings = get_settings()

    if settings.llm_provider == "openai" and settings.llm_api_key:
        _instance = OpenAIProvider(
            api_key=settings.llm_api_key,
            model=settings.llm_model or "gpt-3.5-turbo",
        )
        logger.info("LLM provider: OpenAI (%s)", settings.llm_model)
    else:
        # Default to local Ollama with auto model selection (llama3.1:8b, etc.)
        _instance = OllamaProvider(
            base_url="http://127.0.0.1:11434",
            model=settings.llm_model if settings.llm_model and settings.llm_model != "local" else None,
        )
        logger.info("LLM provider: Ollama auto-detect with conversational fallback")

    return _instance
