"""
ContextOS Entity & Relationship Extractor.

Extracts named entities, temporal markers, concepts, technologies, and relational
links between concepts to construct the personal temporal knowledge graph.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from app.ml.ner.inference import NERInferenceEngine


@dataclass
class ExtractedEntity:
    """An entity discovered within text."""
    name: str
    entity_type: str  # Topic, Project, Person, Document, Event, Concept, Date, Tech
    confidence: float = 0.9
    span: tuple[int, int] = (0, 0)


@dataclass
class ExtractedRelationship:
    """A directed semantic edge between two entities."""
    subject: str
    predicate: str  # Uses, Related To, Discussed On, Mentioned In, Supersedes, Part Of
    object: str
    confidence: float = 0.85
    valid_from: Optional[str] = None
    valid_to: Optional[str] = None


class EntityExtractor:
    """Extracts entities and relationships using hybrid pattern matching and rules."""

    # Curated technology & domain terminology
    KNOWN_TECH = {
        "Python", "Rust", "TypeScript", "JavaScript", "React", "Tauri", "FastAPI",
        "PyTorch", "TensorFlow", "Transformers", "BERT", "GPT", "Claude", "Gemini",
        "SQLite", "PostgreSQL", "Docker", "Kubernetes", "Linux", "Windows", "MacOS",
        "Next.js", "Tailwind", "Vite", "PaddleOCR", "Sentence Transformers", "Node.js",
        "RAG", "Knowledge Graph", "Vector Database", "Embedding", "LLM", "Diffusion",
        "Attention", "Attention Mechanism", "Graph Neural Network", "CNN", "RNN", "LSTM"
    }

    # Temporal regex patterns
    DATE_PATTERNS = [
        r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}(?:st|nd|rd|th)?,?\s+\d{4}\b",
        r"\b\d{4}-\d{2}-\d{2}\b",
        r"\b\d{1,2}/\d{1,2}/\d{2,4}\b",
        r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4}\b",
    ]

    def __init__(self) -> None:
        self.url_pattern = re.compile(r"https?://[^\s<>\"']+")
        self.email_pattern = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")
        self.proper_noun_pattern = re.compile(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b")
        try:
            self.neural_ner = NERInferenceEngine.get_instance()
        except Exception:
            self.neural_ner = None

    def extract_entities(self, text: str) -> list[ExtractedEntity]:
        """Extract all candidate entities from text using custom DL model + hybrid patterns."""
        if not text:
            return []

        entities: list[ExtractedEntity] = []
        seen_names: set[str] = set()

        # 0. Custom Deep Learning BiLSTM + Self-Attention NER
        if self.neural_ner is not None:
            try:
                neural_entities = self.neural_ner.predict(text)
                type_map = {
                    "TECH": "Technology",
                    "PROJECT": "Project",
                    "PERSON": "Person",
                    "DATE": "Date",
                    "TASK": "Task",
                }
                for ne in neural_entities:
                    mapped_type = type_map.get(ne.entity_type, ne.entity_type)
                    if ne.name.lower() not in seen_names:
                        seen_names.add(ne.name.lower())
                        entities.append(
                            ExtractedEntity(
                                name=ne.name,
                                entity_type=mapped_type,
                                confidence=ne.confidence,
                                span=ne.span,
                            )
                        )
            except Exception as e:
                # Log and fallback cleanly to pattern matching
                pass

        # 1. Tech & Frameworks
        lower_text = text.lower()
        for tech in self.KNOWN_TECH:
            pattern = rf"\b{re.escape(tech)}\b"
            for match in re.finditer(pattern, text, re.IGNORECASE):
                name = tech
                if name.lower() not in seen_names:
                    seen_names.add(name.lower())
                    entities.append(
                        ExtractedEntity(
                            name=name,
                            entity_type="Technology",
                            confidence=0.95,
                            span=match.span(),
                        )
                    )

        # 2. Dates
        for dp in self.DATE_PATTERNS:
            for match in re.finditer(dp, text, re.IGNORECASE):
                d_str = match.group(0).strip()
                if d_str.lower() not in seen_names:
                    seen_names.add(d_str.lower())
                    entities.append(
                        ExtractedEntity(
                            name=d_str,
                            entity_type="Date",
                            confidence=0.92,
                            span=match.span(),
                        )
                    )

        # 3. URLs
        for match in self.url_pattern.finditer(text):
            url = match.group(0).strip()
            if url.lower() not in seen_names:
                seen_names.add(url.lower())
                entities.append(
                    ExtractedEntity(
                        name=url,
                        entity_type="URL",
                        confidence=0.99,
                        span=match.span(),
                    )
                )

        # 4. Multi-word Proper Nouns / Projects / Persons
        for match in self.proper_noun_pattern.finditer(text):
            p_name = match.group(0).strip()
            if len(p_name) > 3 and p_name.lower() not in seen_names:
                words = p_name.split()
                # Skip common sentence starters
                if words[0].lower() in {"the", "this", "that", "there", "these", "when", "where", "what", "how", "with", "from"}:
                    continue
                seen_names.add(p_name.lower())
                etype = "Project" if any(w.lower() in {"project", "system", "os", "app", "model", "network", "api"} for w in words) else "Concept"
                entities.append(
                    ExtractedEntity(
                        name=p_name,
                        entity_type=etype,
                        confidence=0.78,
                        span=match.span(),
                    )
                )

        return entities

    def extract_relationships(
        self, entities: list[ExtractedEntity], text: str, document_title: Optional[str] = None
    ) -> list[ExtractedRelationship]:
        """Infer relationships between extracted entities and documents."""
        relationships: list[ExtractedRelationship] = []
        if not entities:
            return relationships

        # Document provenance relationships
        if document_title:
            for ent in entities:
                if ent.name != document_title:
                    relationships.append(
                        ExtractedRelationship(
                            subject=ent.name,
                            predicate="Mentioned In",
                            object=document_title,
                            confidence=0.95,
                        )
                    )

        # Tech/Concept Co-occurrences and linkages
        dates = [e for e in entities if e.entity_type == "Date"]
        non_dates = [e for e in entities if e.entity_type != "Date"]

        # Date link (e.g. Concept -> Discussed On -> Date)
        if dates and non_dates:
            primary_date = dates[0]
            for ent in non_dates[:3]:
                relationships.append(
                    ExtractedRelationship(
                        subject=ent.name,
                        predicate="Discussed On",
                        object=primary_date.name,
                        confidence=0.88,
                        valid_from=primary_date.name,
                    )
                )

        # Tech & Project relationship (e.g. Project -> Uses -> Tech)
        projects = [e for e in entities if e.entity_type == "Project"]
        techs = [e for e in entities if e.entity_type == "Technology"]
        persons = [e for e in entities if e.entity_type == "Person"]
        tasks = [e for e in entities if e.entity_type == "Task"]

        for proj in projects:
            for tech in techs:
                relationships.append(
                    ExtractedRelationship(
                        subject=proj.name,
                        predicate="Uses",
                        object=tech.name,
                        confidence=0.90,
                    )
                )

        # Person & Project (e.g. Person -> Works On -> Project)
        for person in persons:
            for proj in projects:
                relationships.append(
                    ExtractedRelationship(
                        subject=person.name,
                        predicate="Works On",
                        object=proj.name,
                        confidence=0.88,
                    )
                )
            for task in tasks:
                relationships.append(
                    ExtractedRelationship(
                        subject=person.name,
                        predicate="Assigned To",
                        object=task.name,
                        confidence=0.85,
                    )
                )

        # Related To for remaining strong pairs
        for i in range(len(non_dates)):
            for j in range(i + 1, min(i + 3, len(non_dates))):
                relationships.append(
                    ExtractedRelationship(
                        subject=non_dates[i].name,
                        predicate="Related To",
                        object=non_dates[j].name,
                        confidence=0.75,
                    )
                )

        return relationships
