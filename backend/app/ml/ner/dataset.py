"""
Dataset, Vocabulary, and Collation utilities for NER sequence tagging.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Optional

import torch
from torch.utils.data import Dataset

PAD_TOKEN = "<PAD>"
UNK_TOKEN = "<UNK>"
NUM_TOKEN = "<NUM>"

TAGS = [
    "O",
    "B-TECH",
    "I-TECH",
    "B-PROJECT",
    "I-PROJECT",
    "B-PERSON",
    "I-PERSON",
    "B-TASK",
    "I-TASK",
    "B-DATE",
    "I-DATE",
]

TAG2IDX = {tag: i for i, tag in enumerate(TAGS)}
IDX2TAG = {i: tag for i, tag in enumerate(TAGS)}


def simple_tokenize(text: str) -> list[str]:
    """Tokenize text into words and punctuation marks."""
    # Split words while keeping punctuation separate
    tokens = re.findall(r"\w+|[^\w\s]", text, re.UNICODE)
    return tokens


class Vocabulary:
    """Manages word-to-index mapping."""

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
        self.frozen = False

    def __len__(self) -> int:
        return len(self.w2i)

    def build_vocab(self, tokenized_sentences: list[list[str]]) -> None:
        """Build vocabulary from tokenized corpus."""
        counts: dict[str, int] = {}
        for sent in tokenized_sentences:
            for token in sent:
                word = token.lower()
                if word.isdigit():
                    continue
                counts[word] = counts.get(word, 0) + 1

        for word, count in counts.items():
            if count >= self.min_freq and word not in self.w2i:
                idx = len(self.w2i)
                self.w2i[word] = idx
                self.i2w[idx] = word
        self.frozen = True

    def token_to_id(self, token: str) -> int:
        """Map token to integer ID."""
        word = token.lower()
        if word.isdigit():
            return self.w2i[NUM_TOKEN]
        return self.w2i.get(word, self.w2i[UNK_TOKEN])

    def save(self, path: Path | str) -> None:
        """Save vocabulary to JSON."""
        data = {
            "w2i": self.w2i,
            "min_freq": self.min_freq,
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    @classmethod
    def load(cls, path: Path | str) -> Vocabulary:
        """Load vocabulary from JSON."""
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        vocab = cls(min_freq=data.get("min_freq", 1))
        vocab.w2i = data["w2i"]
        vocab.i2w = {int(v): k for k, v in vocab.w2i.items()}
        vocab.frozen = True
        return vocab


class NERDataset(Dataset):
    """PyTorch Dataset for sequence tagging."""

    def __init__(
        self,
        samples: list[dict[str, Any]],
        vocab: Vocabulary,
        max_len: int = 128,
    ) -> None:
        self.samples = samples
        self.vocab = vocab
        self.max_len = max_len

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int) -> dict[str, torch.Tensor]:
        item = self.samples[idx]
        tokens = item["tokens"][: self.max_len]
        tags = item["tags"][: self.max_len]

        input_ids = [self.vocab.token_to_id(t) for t in tokens]
        tag_ids = [TAG2IDX.get(tag, 0) for tag in tags]

        return {
            "input_ids": torch.tensor(input_ids, dtype=torch.long),
            "tag_ids": torch.tensor(tag_ids, dtype=torch.long),
            "seq_len": torch.tensor(len(input_ids), dtype=torch.long),
        }


def pad_collate_fn(batch: list[dict[str, torch.Tensor]]) -> dict[str, torch.Tensor]:
    """Pad batch of variable length sequences."""
    batch_size = len(batch)
    max_len = max(int(b["seq_len"].item()) for b in batch)

    padded_inputs = torch.zeros(batch_size, max_len, dtype=torch.long)
    padded_tags = torch.zeros(batch_size, max_len, dtype=torch.long)
    masks = torch.zeros(batch_size, max_len, dtype=torch.bool)

    for i, b in enumerate(batch):
        length = int(b["seq_len"].item())
        padded_inputs[i, :length] = b["input_ids"]
        padded_tags[i, :length] = b["tag_ids"]
        masks[i, :length] = True

    return {
        "input_ids": padded_inputs,
        "tag_ids": padded_tags,
        "mask": masks,
    }
