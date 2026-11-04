"""
Inference wrapper for the custom DocumentTransformerClassifier.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import torch
import torch.nn.functional as F

from app.ml.classifier.dataset import (
    CATEGORIES,
    ClassifierVocabulary,
    simple_tokenize,
)
from app.ml.classifier.model import DocumentTransformerClassifier

logger = logging.getLogger(__name__)


@dataclass
class DocumentCategoryPrediction:
    category: str
    confidence: float
    probabilities: dict[str, float]


class DocumentClassifierInferenceEngine:
    """Predicts document or chunk category using trained Transformer."""

    _instance: Optional[DocumentClassifierInferenceEngine] = None

    def __init__(self, model_path: Path | str, vocab_path: Path | str) -> None:
        self.device = torch.device("cpu")
        self.vocab = ClassifierVocabulary.load(vocab_path)

        checkpoint = torch.load(model_path, map_location=self.device)
        cfg = checkpoint.get("config", {})

        self.model = DocumentTransformerClassifier(
            vocab_size=cfg.get("vocab_size", len(self.vocab)),
            num_classes=cfg.get("num_classes", len(CATEGORIES)),
            d_model=cfg.get("d_model", 128),
            num_heads=cfg.get("num_heads", 4),
            d_ff=cfg.get("d_ff", 256),
            num_layers=cfg.get("num_layers", 2),
            dropout=0.0,
            padding_idx=0,
        )
        self.model.load_state_dict(checkpoint["model_state_dict"])
        self.model.to(self.device)
        self.model.eval()
        logger.info("DocumentClassifierInferenceEngine successfully initialized.")

    @classmethod
    def get_instance(cls) -> Optional[DocumentClassifierInferenceEngine]:
        """Singleton getter; returns None if weights do not exist yet."""
        if cls._instance is not None:
            return cls._instance

        base_dir = Path(__file__).resolve().parent.parent / "weights"
        model_path = base_dir / "classifier_model.pt"
        vocab_path = base_dir / "classifier_vocab.json"

        if not model_path.exists() or not vocab_path.exists():
            return None

        try:
            cls._instance = cls(model_path, vocab_path)
            return cls._instance
        except Exception as e:
            logger.warning("Could not load neural document classifier: %s", e)
            return None

    def predict(self, text: str, max_len: int = 256) -> DocumentCategoryPrediction:
        """Predict category for text passage."""
        if not text or not text.strip():
            return DocumentCategoryPrediction(
                category="General & Personal",
                confidence=0.0,
                probabilities={cat: 0.0 for cat in CATEGORIES},
            )

        tokens = simple_tokenize(text)[:max_len]
        input_ids = [self.vocab.token_to_id(t) for t in tokens]
        if not input_ids:
            input_ids = [0]

        tensor_in = torch.tensor([input_ids], dtype=torch.long, device=self.device)
        mask = torch.ones_like(tensor_in, dtype=torch.bool, device=self.device)

        with torch.no_grad():
            logits = self.model(tensor_in, mask=mask)
            probs = F.softmax(logits, dim=-1)[0]
            pred_id = int(torch.argmax(probs).item())

        prob_dict = {
            CATEGORIES[i]: round(float(probs[i].item()), 4)
            for i in range(len(CATEGORIES))
        }

        return DocumentCategoryPrediction(
            category=CATEGORIES[pred_id],
            confidence=round(float(probs[pred_id].item()), 4),
            probabilities=prob_dict,
        )
