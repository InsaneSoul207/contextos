"""
Document & Memory Classifier built with custom Transformer Encoder blocks.
"""

from __future__ import annotations

from typing import Optional

import torch
import torch.nn as nn
import torch.nn.functional as F

from app.ml.classifier.transformer_blocks import (
    PositionalEncoding,
    TransformerEncoderBlock,
)


class AttentionPooling(nn.Module):
    """Learned attention pooling over the sequence dimension."""

    def __init__(self, d_model: int) -> None:
        super().__init__()
        self.scorer = nn.Sequential(
            nn.Linear(d_model, d_model // 2),
            nn.Tanh(),
            nn.Linear(d_model // 2, 1),
        )

    def forward(self, x: torch.Tensor, mask: Optional[torch.Tensor] = None) -> torch.Tensor:
        # x: (batch, seq_len, d_model)
        scores = self.scorer(x).squeeze(-1)  # (batch, seq_len)
        if mask is not None:
            scores = scores.masked_fill(~mask, float("-inf"))

        weights = F.softmax(scores, dim=-1)
        weights = torch.nan_to_num(weights, nan=0.0).unsqueeze(-1)  # (batch, seq_len, 1)
        pooled = torch.sum(x * weights, dim=1)  # (batch, d_model)
        return pooled


class DocumentTransformerClassifier(nn.Module):
    """Custom Transformer Encoder for semantic document and memory categorization."""

    def __init__(
        self,
        vocab_size: int,
        num_classes: int = 6,
        d_model: int = 128,
        num_heads: int = 4,
        d_ff: int = 256,
        num_layers: int = 2,
        max_seq_len: int = 256,
        dropout: float = 0.2,
        padding_idx: int = 0,
    ) -> None:
        super().__init__()
        self.padding_idx = padding_idx
        self.d_model = d_model

        # 1. Embedding & Positional Encoding
        self.embedding = nn.Embedding(vocab_size, d_model, padding_idx=padding_idx)
        self.pos_encoder = PositionalEncoding(d_model, max_len=max_seq_len, dropout=dropout)

        # 2. Transformer Encoder Layers
        self.encoder_layers = nn.ModuleList(
            [
                TransformerEncoderBlock(
                    d_model=d_model,
                    num_heads=num_heads,
                    d_ff=d_ff,
                    dropout=dropout,
                )
                for _ in range(num_layers)
            ]
        )
        self.final_norm = nn.LayerNorm(d_model)

        # 3. Pooling: Attention Pooling + Global Mean Pooling
        self.attn_pool = AttentionPooling(d_model)

        # 4. Classification Head
        self.classifier = nn.Sequential(
            nn.Linear(d_model * 2, d_model),
            nn.LayerNorm(d_model),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(d_model, num_classes),
        )

    def forward(
        self,
        input_ids: torch.Tensor,
        mask: Optional[torch.Tensor] = None,
    ) -> torch.Tensor:
        """Forward pass.

        Args:
            input_ids: (batch_size, seq_len)
            mask: (batch_size, seq_len) boolean tensor (True for valid tokens)

        Returns:
            logits: (batch_size, num_classes)
        """
        if mask is None:
            mask = input_ids != self.padding_idx

        # Embeddings + Sinusoidal Positions
        x = self.embedding(input_ids) * (self.d_model ** 0.5)
        x = self.pos_encoder(x)

        # Encoder stack
        for layer in self.encoder_layers:
            x = layer(x, mask=mask)
        x = self.final_norm(x)

        # Attention pooling
        pooled_attn = self.attn_pool(x, mask=mask)

        # Mean pooling over valid mask
        mask_expanded = mask.unsqueeze(-1).float()
        sum_x = torch.sum(x * mask_expanded, dim=1)
        lengths = torch.clamp(mask_expanded.sum(dim=1), min=1.0)
        pooled_mean = sum_x / lengths

        # Concatenate pooled features: (batch_size, d_model * 2)
        combined = torch.cat([pooled_attn, pooled_mean], dim=-1)

        # Logits
        logits = self.classifier(combined)
        return logits
