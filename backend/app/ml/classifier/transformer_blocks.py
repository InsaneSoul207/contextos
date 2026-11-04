"""
Custom Transformer building blocks implemented from scratch using PyTorch primitives.

Implements the fundamental mathematical operations of "Attention Is All You Need":
- Sinusoidal Positional Encoding
- Scaled Dot-Product Attention
- Multi-Head Attention
- Position-wise Feed-Forward Network
- Pre-LN Transformer Encoder Layer
"""

from __future__ import annotations

import math
from typing import Optional

import torch
import torch.nn as nn
import torch.nn.functional as F


class PositionalEncoding(nn.Module):
    """Sinusoidal positional encoding to inject sequence order information."""

    def __init__(self, d_model: int, max_len: int = 512, dropout: float = 0.1) -> None:
        super().__init__()
        self.dropout = nn.Dropout(p=dropout)

        # Compute the positional encodings once in log space
        pe = torch.zeros(max_len, d_model)
        position = torch.arange(0, max_len, dtype=torch.float).unsqueeze(1)
        div_term = torch.exp(
            torch.arange(0, d_model, 2).float() * (-math.log(10000.0) / d_model)
        )

        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        pe = pe.unsqueeze(0)  # Shape: (1, max_len, d_model)

        self.register_buffer("pe", pe)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Add positional encodings to token embeddings.

        Args:
            x: Tensor of shape (batch_size, seq_len, d_model)
        """
        seq_len = x.size(1)
        x = x + self.pe[:, :seq_len]  # type: ignore[index]
        return self.dropout(x)


class ScaledDotProductAttention(nn.Module):
    """Computes Scaled Dot-Product Attention: softmax(Q * K^T / sqrt(d_k)) * V."""

    def __init__(self, dropout: float = 0.1) -> None:
        super().__init__()
        self.dropout = nn.Dropout(dropout)

    def forward(
        self,
        q: torch.Tensor,
        k: torch.Tensor,
        v: torch.Tensor,
        mask: Optional[torch.Tensor] = None,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        d_k = q.size(-1)
        scores = torch.matmul(q, k.transpose(-2, -1)) / math.sqrt(d_k)

        if mask is not None:
            scores = scores.masked_fill(~mask, float("-inf"))

        attn_weights = F.softmax(scores, dim=-1)
        attn_weights = torch.nan_to_num(attn_weights, nan=0.0)
        attn_weights = self.dropout(attn_weights)
        output = torch.matmul(attn_weights, v)
        return output, attn_weights


class MultiHeadAttention(nn.Module):
    """Multi-Head Attention block with separate Q, K, V projections and linear output head."""

    def __init__(self, d_model: int, num_heads: int = 4, dropout: float = 0.1) -> None:
        super().__init__()
        if d_model % num_heads != 0:
            raise ValueError(f"d_model ({d_model}) must be divisible by num_heads ({num_heads})")

        self.d_model = d_model
        self.num_heads = num_heads
        self.d_k = d_model // num_heads

        self.w_q = nn.Linear(d_model, d_model)
        self.w_k = nn.Linear(d_model, d_model)
        self.w_v = nn.Linear(d_model, d_model)
        self.w_o = nn.Linear(d_model, d_model)

        self.attention = ScaledDotProductAttention(dropout=dropout)

    def forward(
        self,
        q: torch.Tensor,
        k: torch.Tensor,
        v: torch.Tensor,
        mask: Optional[torch.Tensor] = None,
    ) -> torch.Tensor:
        batch_size = q.size(0)

        # 1. Linear projections: (batch, seq_len, d_model) -> (batch, num_heads, seq_len, d_k)
        q_proj = self.w_q(q).view(batch_size, -1, self.num_heads, self.d_k).transpose(1, 2)
        k_proj = self.w_k(k).view(batch_size, -1, self.num_heads, self.d_k).transpose(1, 2)
        v_proj = self.w_v(v).view(batch_size, -1, self.num_heads, self.d_k).transpose(1, 2)

        # 2. Adjust mask shape for multi-head attention: (batch, 1, 1, seq_len)
        if mask is not None and mask.dim() == 2:
            mask = mask.unsqueeze(1).unsqueeze(2)

        # 3. Apply scaled dot product attention
        context, _ = self.attention(q_proj, k_proj, v_proj, mask=mask)

        # 4. Concatenate heads and project output
        context = context.transpose(1, 2).contiguous().view(batch_size, -1, self.d_model)
        return self.w_o(context)


class PositionwiseFeedForward(nn.Module):
    """Two-layer feed-forward network with non-linear activation."""

    def __init__(self, d_model: int, d_ff: int, dropout: float = 0.1) -> None:
        super().__init__()
        self.linear1 = nn.Linear(d_model, d_ff)
        self.linear2 = nn.Linear(d_ff, d_model)
        self.dropout = nn.Dropout(dropout)
        self.activation = nn.GELU()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.linear2(self.dropout(self.activation(self.linear1(x))))


class TransformerEncoderBlock(nn.Module):
    """A single Transformer Encoder block using Pre-Layer Normalization architecture."""

    def __init__(self, d_model: int, num_heads: int, d_ff: int, dropout: float = 0.1) -> None:
        super().__init__()
        self.self_attn = MultiHeadAttention(d_model, num_heads=num_heads, dropout=dropout)
        self.ffn = PositionwiseFeedForward(d_model, d_ff=d_ff, dropout=dropout)

        self.norm1 = nn.LayerNorm(d_model)
        self.norm2 = nn.LayerNorm(d_model)
        self.dropout = nn.Dropout(dropout)

    def forward(self, x: torch.Tensor, mask: Optional[torch.Tensor] = None) -> torch.Tensor:
        # Pre-LN Self-Attention with residual connection
        norm_x = self.norm1(x)
        attn_out = self.self_attn(norm_x, norm_x, norm_x, mask=mask)
        x = x + self.dropout(attn_out)

        # Pre-LN Feed-Forward with residual connection
        norm_x = self.norm2(x)
        ffn_out = self.ffn(norm_x)
        x = x + self.dropout(ffn_out)

        return x
