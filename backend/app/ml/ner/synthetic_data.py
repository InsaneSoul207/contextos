"""
Annotated dataset generator for training the ContextOS NER model.

Produces training and validation samples covering technologies, projects,
people, actionable tasks, dates, and non-entity narrative tokens.
"""

from __future__ import annotations

import random
from typing import Any

from app.ml.ner.dataset import simple_tokenize

PEOPLE = [
    "Eshaan Mishra", "Alice Chen", "Bob Smith", "Dr. Sharma", "Sarah Jenkins",
    "David Miller", "Prof. Andrew Ng", "Geoffrey Hinton", "Linus Torvalds",
    "Yann LeCun", "Ada Lovelace", "Alan Turing", "Guido van Rossum",
    "Demis Hassabis", "Ilya Sutskever", "Sam Altman", "Satya Nadella",
]

TECHS = [
    "PyTorch", "TensorFlow", "FastAPI", "React", "Tauri", "SQLite", "PostgreSQL",
    "Docker", "Kubernetes", "TypeScript", "Python", "Rust", "Tailwind", "Vite",
    "PaddleOCR", "Transformers", "BERT", "ResNet", "Next.js", "Redis", "Kafka",
    "Linux", "Windows", "Node.js", "GraphQL", "MongoDB", "OpenCV", "Scikit-Learn",
    "GeoBERT", "ContextOS", "Numpy", "Pandas", "Matplotlib",
]

PROJECTS = [
    "ContextOS", "Project Titan", "NeuralEngine", "GeoBERT", "DeepSearch",
    "MemoryGraph", "Vanguard", "VisionPipeline", "AlphaZero", "Apollo",
    "Nexus", "CorePlatform", "DataHub", "OmniParser", "AgentMatrix",
]

DATES = [
    "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "yesterday",
    "November 2026", "December 15", "October 2024", "next week", "tomorrow",
    "2026-11-03", "January 2025", "Q4 2026", "2025-05-20",
]

TASKS = [
    "fix the memory leak",
    "implement hybrid retrieval",
    "refactor database queries",
    "benchmark sentence embeddings",
    "update API documentation",
    "deploy staging server",
    "optimize attention mechanism",
    "train sequence tagger",
    "test cross-encoder reranker",
    "review pull request",
    "clean up docker images",
]

TEMPLATES = [
    ("{PERSON} started working on {PROJECT} using {TECH} on {DATE}.",
     ["PERSON", "PROJECT", "TECH", "DATE"]),
    ("We migrated the service to {TECH} and connected it to {TECH}.",
     ["TECH", "TECH"]),
    ("TODO: {TASK} before {DATE}.",
     ["TASK", "DATE"]),
    ("{PERSON} suggested using {TECH} for the {PROJECT} backend.",
     ["PERSON", "TECH", "PROJECT"]),
    ("The team discussed {PROJECT} milestones with {PERSON} on {DATE}.",
     ["PROJECT", "PERSON", "DATE"]),
    ("Please {TASK} and notify {PERSON}.",
     ["TASK", "PERSON"]),
    ("Our benchmark showed that {TECH} outperforms {TECH} on {PROJECT}.",
     ["TECH", "TECH", "PROJECT"]),
    ("{PROJECT} was initialized by {PERSON} using {TECH} and {TECH}.",
     ["PROJECT", "PERSON", "TECH", "TECH"]),
    ("Meeting scheduled for {DATE} to evaluate {PROJECT} architecture.",
     ["DATE", "PROJECT"]),
    ("{PERSON} and {PERSON} are testing the new {TECH} pipeline.",
     ["PERSON", "PERSON", "TECH"]),
    ("Action item: {TASK} for {PROJECT}.",
     ["TASK", "PROJECT"]),
    ("Implemented {TECH} integration in {PROJECT} on {DATE}.",
     ["TECH", "PROJECT", "DATE"]),
    ("Check the system logs for {PROJECT} errors from {DATE}.",
     ["PROJECT", "DATE"]),
    ("{PERSON} published a new paper on {TECH} algorithms.",
     ["PERSON", "TECH"]),
    ("Don't forget to {TASK} before meeting {PERSON} on {DATE}.",
     ["TASK", "PERSON", "DATE"]),
    ("The architecture of {PROJECT} relies heavily on {TECH} and local {TECH} storage.",
     ["PROJECT", "TECH", "TECH"]),
    ("We replaced {TECH} with {TECH} to reduce latency in {PROJECT}.",
     ["TECH", "TECH", "PROJECT"]),
    ("{PERSON} submitted the final report for {PROJECT} on {DATE}.",
     ["PERSON", "PROJECT", "DATE"]),
]

PLAIN_TEXTS = [
    "The quarterly meeting was held to review company goals and department performance metrics.",
    "Ensure all unit tests pass before merging code into the main production branch.",
    "All users must update their local environment configuration according to the guidelines.",
    "The overall system memory consumption remained stable during overnight execution.",
    "Please send an email update once the evaluation process is completed.",
    "Comprehensive documentation is required for all new software components and features.",
    "Performance analysis indicated significant reduction in disk I/O operations.",
    "The user interface has been updated with modern responsive design principles.",
]


def _build_labeled_sentence(template: str, slot_types: list[str]) -> dict[str, Any]:
    """Fill template slots and produce token-level BIO tags."""
    replacements: list[tuple[str, str, str]] = []  # (placeholder, value, type)
    for st in slot_types:
        if st == "PERSON":
            val = random.choice(PEOPLE)
        elif st == "TECH":
            val = random.choice(TECHS)
        elif st == "PROJECT":
            val = random.choice(PROJECTS)
        elif st == "DATE":
            val = random.choice(DATES)
        elif st == "TASK":
            val = random.choice(TASKS)
        else:
            val = "Unknown"
        replacements.append((f"{{{st}}}", val, st))

    # Substitute one by one while keeping track of spans
    text = template
    span_tags: list[tuple[int, int, str]] = []
    for placeholder, val, ent_type in replacements:
        idx = text.find(placeholder)
        if idx != -1:
            text = text[:idx] + val + text[idx + len(placeholder):]
            span_tags.append((idx, idx + len(val), ent_type))

    # Tokenize
    tokens = simple_tokenize(text)
    tags = ["O"] * len(tokens)

    # Reconstruct character positions to map tokens to spans
    char_pos = 0
    token_spans: list[tuple[int, int]] = []
    for t in tokens:
        idx = text.find(t, char_pos)
        token_spans.append((idx, idx + len(t)))
        char_pos = idx + len(t)

    # Assign BIO tags
    for start, end, ent_type in span_tags:
        is_first = True
        for i, (t_start, t_end) in enumerate(token_spans):
            # Token falls inside entity span
            if t_start >= start and t_end <= end:
                prefix = "B-" if is_first else "I-"
                tags[i] = f"{prefix}{ent_type}"
                is_first = False

    return {"text": text, "tokens": tokens, "tags": tags}


def generate_dataset(num_train: int = 1200, num_val: int = 250, seed: int = 42) -> tuple[list[dict], list[dict]]:
    """Generate training and validation splits."""
    random.seed(seed)
    train_data: list[dict] = []
    val_data: list[dict] = []

    def make_samples(n: int) -> list[dict]:
        samples = []
        for _ in range(int(n * 0.85)):
            tpl, slots = random.choice(TEMPLATES)
            samples.append(_build_labeled_sentence(tpl, slots))
        for _ in range(int(n * 0.15)):
            pt = random.choice(PLAIN_TEXTS)
            toks = simple_tokenize(pt)
            samples.append({"text": pt, "tokens": toks, "tags": ["O"] * len(toks)})
        random.shuffle(samples)
        return samples

    train_data = make_samples(num_train)
    val_data = make_samples(num_val)
    return train_data, val_data
