"""
Dataset, Vocabulary, and Collation for Document & Memory Classification.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import torch
from torch.utils.data import Dataset

PAD_TOKEN = "<PAD>"
UNK_TOKEN = "<UNK>"
NUM_TOKEN = "<NUM>"

CATEGORIES = [
    "Code & Technical Docs",
    "Research & Academic",
    "Meeting & Sync Notes",
    "Coursework & Study",
    "Financial & Receipts",
    "Personal & Notes",
]

CAT2IDX = {cat: i for i, cat in enumerate(CATEGORIES)}
IDX2CAT = {i: cat for i, cat in enumerate(CATEGORIES)}


def simple_tokenize(text: str) -> list[str]:
    """Tokenize text into words."""
    tokens = re.findall(r"\w+|[^\w\s]", text, re.UNICODE)
    return tokens


class ClassifierVocabulary:
    """Manages word-to-index vocabulary."""

    def __init__(self, min_freq: int = 1) -> None:
        self.min_freq = min_freq
        self.w2i: dict[str, int] = {
            PAD_TOKEN: 0,
            UNK_TOKEN: 1,
            NUM_TOKEN: 2,
        }
        self.i2w: dict[int, str] = {
            0: PAD_TOKEN,
            1: UNK_TOKEN,
            2: NUM_TOKEN,
        }

    def __len__(self) -> int:
        return len(self.w2i)

    def build_vocab(self, tokenized_texts: list[list[str]]) -> None:
        counts: dict[str, int] = {}
        for tokens in tokenized_texts:
            for token in tokens:
                word = token.lower()
                if word.isdigit():
                    continue
                counts[word] = counts.get(word, 0) + 1

        for word, count in counts.items():
            if count >= self.min_freq and word not in self.w2i:
                idx = len(self.w2i)
                self.w2i[word] = idx
                self.i2w[idx] = word

    def token_to_id(self, token: str) -> int:
        word = token.lower()
        if word.isdigit():
            return self.w2i[NUM_TOKEN]
        return self.w2i.get(word, self.w2i[UNK_TOKEN])

    def save(self, path: Path | str) -> None:
        data = {"w2i": self.w2i, "min_freq": self.min_freq}
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    @classmethod
    def load(cls, path: Path | str) -> ClassifierVocabulary:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        vocab = cls(min_freq=data.get("min_freq", 1))
        vocab.w2i = data["w2i"]
        vocab.i2w = {int(v): k for k, v in vocab.w2i.items()}
        return vocab


class TextClassificationDataset(Dataset):
    """PyTorch Dataset for text classification."""

    def __init__(
        self,
        samples: list[dict[str, Any]],
        vocab: ClassifierVocabulary,
        max_len: int = 256,
    ) -> None:
        self.samples = samples
        self.vocab = vocab
        self.max_len = max_len

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int) -> dict[str, torch.Tensor]:
        item = self.samples[idx]
        tokens = item["tokens"][: self.max_len]
        input_ids = [self.vocab.token_to_id(t) for t in tokens]
        label = item["label"]

        return {
            "input_ids": torch.tensor(input_ids, dtype=torch.long),
            "label": torch.tensor(label, dtype=torch.long),
            "length": torch.tensor(len(input_ids), dtype=torch.long),
        }


def classifier_collate_fn(batch: list[dict[str, torch.Tensor]]) -> dict[str, torch.Tensor]:
    """Pad batch of variable length token sequences."""
    batch_size = len(batch)
    max_len = max(int(b["length"].item()) for b in batch)

    padded_inputs = torch.zeros(batch_size, max_len, dtype=torch.long)
    masks = torch.zeros(batch_size, max_len, dtype=torch.bool)
    labels = torch.zeros(batch_size, dtype=torch.long)

    for i, b in enumerate(batch):
        length = int(b["length"].item())
        padded_inputs[i, :length] = b["input_ids"]
        masks[i, :length] = True
        labels[i] = b["label"]

    return {
        "input_ids": padded_inputs,
        "mask": masks,
        "labels": labels,
    }
