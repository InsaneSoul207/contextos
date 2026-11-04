"""
BiLSTM + Multi-Head Self-Attention Network for Sequence Tagging (NER).

Built from scratch using PyTorch primitives to extract technical entities,
projects, persons, dates, and actionable tasks from desktop documents.
"""

from __future__ import annotations

import math
from typing import Optional

import torch
import torch.nn as nn
import torch.nn.functional as F


class MultiHeadSelfAttention(nn.Module):
    """Multi-Head Self-Attention layer with key padding mask support."""

    def __init__(self, embed_dim: int, num_heads: int = 4, dropout: float = 0.1) -> None:
        super().__init__()
        if embed_dim % num_heads != 0:
            raise ValueError(f"embed_dim ({embed_dim}) must be divisible by num_heads ({num_heads})")

        self.embed_dim = embed_dim
        self.num_heads = num_heads
        self.head_dim = embed_dim // num_heads

        self.q_proj = nn.Linear(embed_dim, embed_dim)
        self.k_proj = nn.Linear(embed_dim, embed_dim)
        self.v_proj = nn.Linear(embed_dim, embed_dim)
        self.out_proj = nn.Linear(embed_dim, embed_dim)

        self.dropout = nn.Dropout(dropout)
        self.scale = 1.0 / math.sqrt(self.head_dim)

    def forward(self, x: torch.Tensor, mask: Optional[torch.Tensor] = None) -> torch.Tensor:
        """Forward pass for multi-head self-attention.

        Args:
            x: Tensor of shape (batch_size, seq_len, embed_dim)
            mask: Optional boolean or float mask of shape (batch_size, seq_len)
                  where True/1 indicates valid tokens and False/0 indicates padding.

        Returns:
            Tensor of shape (batch_size, seq_len, embed_dim)
        """
        batch_size, seq_len, _ = x.shape

        # Linear projections & split into heads: (batch, num_heads, seq_len, head_dim)
        q = self.q_proj(x).view(batch_size, seq_len, self.num_heads, self.head_dim).transpose(1, 2)
        k = self.k_proj(x).view(batch_size, seq_len, self.num_heads, self.head_dim).transpose(1, 2)
        v = self.v_proj(x).view(batch_size, seq_len, self.num_heads, self.head_dim).transpose(1, 2)

        # Scaled dot-product: (batch, num_heads, seq_len, seq_len)
        scores = torch.matmul(q, k.transpose(-2, -1)) * self.scale

        if mask is not None:
            # Expand mask for heads: (batch, 1, 1, seq_len)
            mask_expanded = mask.unsqueeze(1).unsqueeze(2)
            scores = scores.masked_fill(~mask_expanded, float("-inf"))

        attn_weights = F.softmax(scores, dim=-1)
        # In case all tokens in a row were masked (e.g. trailing padding), replace NaN with 0
        attn_weights = torch.nan_to_num(attn_weights, nan=0.0)
        attn_weights = self.dropout(attn_weights)

        # Context output: (batch, num_heads, seq_len, head_dim)
        context = torch.matmul(attn_weights, v)

        # Concatenate heads back to (batch_size, seq_len, embed_dim)
        context = context.transpose(1, 2).contiguous().view(batch_size, seq_len, self.embed_dim)
        return self.out_proj(context)


class BiLSTMAttentionNER(nn.Module):
    """Bidirectional LSTM with Self-Attention for token classification / NER."""

    def __init__(
        self,
        vocab_size: int,
        num_classes: int,
        embed_dim: int = 128,
        hidden_dim: int = 128,
        num_heads: int = 4,
        num_lstm_layers: int = 2,
        dropout: float = 0.2,
        padding_idx: int = 0,
    ) -> None:
        super().__init__()
        self.padding_idx = padding_idx

        # 1. Embedding Layer
        self.embedding = nn.Embedding(
            num_embeddings=vocab_size,
            embedding_dim=embed_dim,
            padding_idx=padding_idx,
        )

        # 2. Bidirectional LSTM
        lstm_hidden = hidden_dim // 2
        self.lstm = nn.LSTM(
            input_size=embed_dim,
            hidden_size=lstm_hidden,
            num_layers=num_lstm_layers,
            bidirectional=True,
            batch_first=True,
            dropout=dropout if num_lstm_layers > 1 else 0.0,
        )

        # 3. Layer Normalization
        self.norm1 = nn.LayerNorm(hidden_dim)

        # 4. Multi-Head Self-Attention
        self.self_attention = MultiHeadSelfAttention(
            embed_dim=hidden_dim,
            num_heads=num_heads,
            dropout=dropout,
        )
        self.norm2 = nn.LayerNorm(hidden_dim)

        # 5. Non-linear Projection & Classification Head
        self.ffn = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout),
        )
        self.classifier = nn.Linear(hidden_dim, num_classes)

        self.dropout = nn.Dropout(dropout)

    def forward(
        self,
        input_ids: torch.Tensor,
        mask: Optional[torch.Tensor] = None,
    ) -> torch.Tensor:
        """Forward pass.

        Args:
            input_ids: (batch_size, seq_len) of token indices.
            mask: Optional (batch_size, seq_len) boolean tensor (True for real tokens).

        Returns:
            logits: (batch_size, seq_len, num_classes)
        """
        if mask is None:
            mask = input_ids != self.padding_idx

        # Token embedding
        embedded = self.dropout(self.embedding(input_ids))

        # BiLSTM representation
        lstm_out, _ = self.lstm(embedded)
        lstm_out = self.norm1(lstm_out)

        # Attention enrichment with residual connection
        attn_out = self.self_attention(lstm_out, mask=mask)
        x = self.norm2(lstm_out + attn_out)

        # Position-wise feedforward & classification
        feat = self.ffn(x)
        logits = self.classifier(feat)
        return logits
