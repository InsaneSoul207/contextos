"""
Inference wrapper for the custom BiLSTM + Attention NER model.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import torch
import torch.nn.functional as F

from app.ml.ner.dataset import (
    IDX2TAG,
    TAGS,
    Vocabulary,
    simple_tokenize,
)
from app.ml.ner.model import BiLSTMAttentionNER

logger = logging.getLogger(__name__)


@dataclass
class NeuralEntity:
    name: str
    entity_type: str
    confidence: float
    span: tuple[int, int]


class NERInferenceEngine:
    """Predicts entities from raw text using custom trained BiLSTMAttentionNER."""

    _instance: Optional[NERInferenceEngine] = None

    def __init__(self, model_path: Path | str, vocab_path: Path | str) -> None:
        self.device = torch.device("cpu")  # CPU is optimal and low-latency for desktop
        self.vocab = Vocabulary.load(vocab_path)

        checkpoint = torch.load(model_path, map_location=self.device)
        cfg = checkpoint.get("config", {})
        self.model = BiLSTMAttentionNER(
            vocab_size=cfg.get("vocab_size", len(self.vocab)),
            num_classes=cfg.get("num_classes", len(TAGS)),
            embed_dim=cfg.get("embed_dim", 128),
            hidden_dim=cfg.get("hidden_dim", 128),
            num_heads=cfg.get("num_heads", 4),
            num_lstm_layers=cfg.get("num_lstm_layers", 2),
            dropout=0.0,
            padding_idx=0,
        )
        self.model.load_state_dict(checkpoint["model_state_dict"])
        self.model.to(self.device)
        self.model.eval()
        logger.info("NERInferenceEngine successfully initialized.")

    @classmethod
    def get_instance(cls) -> Optional[NERInferenceEngine]:
        """Singleton getter; returns None if weights do not exist yet."""
        if cls._instance is not None:
            return cls._instance

        base_dir = Path(__file__).resolve().parent.parent / "weights"
        model_path = base_dir / "ner_model.pt"
        vocab_path = base_dir / "ner_vocab.json"

        if not model_path.exists() or not vocab_path.exists():
            return None

        try:
            cls._instance = cls(model_path, vocab_path)
            return cls._instance
        except Exception as e:
            logger.warning("Could not load neural NER model: %s", e)
            return None

    def predict(self, text: str) -> list[NeuralEntity]:
        """Extract entities and spans from arbitrary text."""
        if not text or not text.strip():
            return []

        tokens = simple_tokenize(text)
        if not tokens:
            return []

        # Find character offsets for each token
        token_spans: list[tuple[int, int]] = []
        char_idx = 0
        for t in tokens:
            pos = text.find(t, char_idx)
            if pos != -1:
                token_spans.append((pos, pos + len(t)))
                char_idx = pos + len(t)
            else:
                token_spans.append((char_idx, char_idx + len(t)))
                char_idx += len(t)

        input_ids = [self.vocab.token_to_id(t) for t in tokens]
        tensor_in = torch.tensor([input_ids], dtype=torch.long, device=self.device)
        mask = torch.ones_like(tensor_in, dtype=torch.bool, device=self.device)

        with torch.no_grad():
            logits = self.model(tensor_in, mask=mask)  # (1, seq_len, num_classes)
            probs = F.softmax(logits, dim=-1)[0]       # (seq_len, num_classes)
            pred_ids = torch.argmax(probs, dim=-1).cpu().tolist()

        entities: list[NeuralEntity] = []
        current_entity_type: Optional[str] = None
        current_tokens: list[str] = []
        current_confs: list[float] = []
        current_span_start = 0
        current_span_end = 0

        def flush_current():
            nonlocal current_entity_type, current_tokens, current_confs, current_span_start, current_span_end
            if current_entity_type and current_tokens:
                name = text[current_span_start:current_span_end].strip()
                avg_conf = sum(current_confs) / max(len(current_confs), 1)
                if name:
                    entities.append(
                        NeuralEntity(
                            name=name,
                            entity_type=current_entity_type,
                            confidence=round(avg_conf, 3),
                            span=(current_span_start, current_span_end),
                        )
                    )
            current_entity_type = None
            current_tokens = []
            current_confs = []

        for i, (token, tag_id, (sp_s, sp_e)) in enumerate(zip(tokens, pred_ids, token_spans)):
            tag = IDX2TAG[tag_id]
            conf = float(probs[i, tag_id].item())

            if tag.startswith("B-"):
                flush_current()
                current_entity_type = tag[2:]
                current_tokens = [token]
                current_confs = [conf]
                current_span_start = sp_s
                current_span_end = sp_e
            elif tag.startswith("I-") and current_entity_type == tag[2:]:
                current_tokens.append(token)
                current_confs.append(conf)
                current_span_end = sp_e
            else:
                flush_current()

        flush_current()
        return entities
