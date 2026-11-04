"""
Custom Deep Learning API Endpoints.

Provides direct access to test and inspect the self-made PyTorch neural networks:
- BiLSTMAttentionNER: Sequence tagging for technical knowledge graph discovery
- DocumentTransformerClassifier: Custom Transformer encoder for document classification
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.ml.classifier.dataset import CATEGORIES
from app.ml.classifier.inference import DocumentClassifierInferenceEngine
from app.ml.ner.dataset import TAGS
from app.ml.ner.inference import NERInferenceEngine

router = APIRouter(prefix="/api/ml", tags=["custom-deep-learning"])


class TextPayload(BaseModel):
    text: str


@router.get("/models")
async def get_models_info() -> dict[str, Any]:
    """Return architecture details and metadata for custom deep learning models."""
    ner_engine = NERInferenceEngine.get_instance()
    clf_engine = DocumentClassifierInferenceEngine.get_instance()

    ner_params = sum(p.numel() for p in ner_engine.model.parameters()) if ner_engine else 0
    clf_params = sum(p.numel() for p in clf_engine.model.parameters()) if clf_engine else 0

    return {
        "models": [
            {
                "name": "BiLSTM + Multi-Head Self-Attention NER",
                "purpose": "Sequence tagging for Knowledge Graph entities (Tech, Project, Person, Task, Date)",
                "framework": "PyTorch (built from scratch)",
                "trainable_parameters": ner_params,
                "status": "ready" if ner_engine else "not_loaded",
                "classes": TAGS,
            },
            {
                "name": "Custom Transformer Document Classifier",
                "purpose": "Semantic taxonomy and auto-categorization of ingested documents",
                "framework": "PyTorch (built from scratch: sinusoidal PE + MultiHeadAttention + FFN)",
                "trainable_parameters": clf_params,
                "status": "ready" if clf_engine else "not_loaded",
                "classes": CATEGORIES,
            },
        ]
    }


@router.post("/ner")
async def extract_entities_neural(payload: TextPayload) -> dict[str, Any]:
    """Run inference with the custom BiLSTMAttentionNER model."""
    ner_engine = NERInferenceEngine.get_instance()
    if not ner_engine:
        raise HTTPException(status_code=503, detail="NER neural model not loaded.")

    entities = ner_engine.predict(payload.text)
    return {
        "text": payload.text,
        "entity_count": len(entities),
        "entities": [
            {
                "name": e.name,
                "type": e.entity_type,
                "confidence": e.confidence,
                "span": list(e.span),
            }
            for e in entities
        ],
    }


@router.post("/classify")
async def classify_document_neural(payload: TextPayload) -> dict[str, Any]:
    """Run inference with the custom DocumentTransformerClassifier model."""
    clf_engine = DocumentClassifierInferenceEngine.get_instance()
    if not clf_engine:
        raise HTTPException(status_code=503, detail="Document classifier model not loaded.")

    prediction = clf_engine.predict(payload.text)
    return {
        "predicted_category": prediction.category,
        "confidence": prediction.confidence,
        "probabilities": prediction.probabilities,
    }
