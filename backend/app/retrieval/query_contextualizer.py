"""
ContextOS Conversational Query Contextualizer.

Resolves anaphoric references (pronouns like "it", "this", "that", "the project", "the app")
in multi-turn conversations into explicit, standalone retrieval queries so vector and
hybrid search retrieve memories for the intended subject rather than unrelated documents.
"""

from __future__ import annotations

import logging
import re
from typing import Optional

from app.models.schemas import ChatMessage

logger = logging.getLogger(__name__)

PRONOUN_PATTERN = re.compile(
    r"\b(it|its|this|that|these|those|they|them|the app|the system|the project|the folder|the tool|the model|the architecture|the code|the file|the repo)\b",
    re.IGNORECASE,
)

GENERIC_FOLLOWUP_PATTERN = re.compile(
    r"^(what|how|why|where|can|does|is|are|tell me|explain|deepdive|elaborate|show me|list)\b",
    re.IGNORECASE,
)

COMMON_STOP_WORDS = {
    "can", "u", "you", "please", "into", "the", "folder", "what", "is", "a", "an",
    "in", "on", "about", "tell", "me", "deepdive", "more", "look", "at", "show",
    "file", "files", "here", "there", "have", "has", "had", "does", "do", "did",
    "are", "were", "was", "how", "why", "when", "which", "who", "whom", "will",
    "would", "could", "should", "give", "me", "some", "any", "all", "project",
}


def extract_topic_subject(text: str) -> Optional[str]:
    """Extract key entity/topic subject from a conversational message.

    Looks for proper nouns, capitalized terms, CamelCase identifiers, or distinctive
    keywords in the user query.
    """
    if not text:
        return None

    # Clean punctuation except dashes/underscores/dots inside filenames
    cleaned = re.sub(r"[^\w\s.\-]", " ", text)
    words = cleaned.split()

    candidates: list[str] = []
    for w in words:
        wl = w.lower()
        if wl in COMMON_STOP_WORDS or len(w) < 2:
            continue

        # Check for uppercase or mixed case (e.g. ContextOS, GeoBERT, Transformers)
        if any(c.isupper() for c in w) or "_" in w or "." in w or len(w) >= 4:
            candidates.append(w)

    if candidates:
        # Return first 1-2 key entity terms
        return " ".join(candidates[:2])

    return None


def contextualize_chat_query(
    current_message: str,
    history: list[ChatMessage],
    conversation_title: Optional[str] = None,
) -> tuple[str, Optional[str]]:
    """Contextualize the user's current message using conversation history.

    Args:
        current_message: The latest raw user message (e.g. "what ai features does it have?").
        history: Previous chat exchanges in the thread.
        conversation_title: Optional title of the conversation thread.

    Returns:
        tuple[search_query, active_subject]:
            - search_query: Enriched standalone query for hybrid search (e.g. "ContextOS what ai features does it have?")
            - active_subject: Extracted subject entity if found (e.g. "ContextOS"), else None.
    """
    raw_query = current_message.strip()
    if not raw_query:
        return raw_query, None

    has_pronoun = bool(PRONOUN_PATTERN.search(raw_query))
    is_short = len(raw_query.split()) <= 7
    is_followup = bool(GENERIC_FOLLOWUP_PATTERN.search(raw_query)) and is_short

    # If the user query is already self-contained and has no pronouns/anaphora, use as-is
    if not (has_pronoun or is_followup) and not is_short:
        return raw_query, None

    # Find the active subject from recent history (searching backwards)
    active_subject: Optional[str] = None

    if history:
        for msg in reversed(history):
            if msg.role == "user":
                subject = extract_topic_subject(msg.content)
                if subject and subject.lower() not in raw_query.lower():
                    active_subject = subject
                    break

    # Fallback to conversation title if no subject found in user messages
    if not active_subject and conversation_title:
        subject = extract_topic_subject(conversation_title)
        if subject and subject.lower() not in raw_query.lower():
            active_subject = subject

    if not active_subject:
        return raw_query, None

    logger.info(
        "Contextualized query: '%s' -> Active Subject: '%s'",
        raw_query,
        active_subject,
    )

    # 1. Substitute pronouns directly if possible
    # e.g., "what does it do?" -> "what does ContextOS do?"
    substituted = re.sub(
        r"\b(it|this|that)\b",
        active_subject,
        raw_query,
        flags=re.IGNORECASE,
    )

    # 2. Formulate enriched search query: prefix subject for strong vector + lexical BM25 matching
    if substituted.lower() != raw_query.lower():
        search_query = f"{active_subject} {substituted}"
    else:
        search_query = f"{active_subject} {raw_query}"

    return search_query, active_subject
