"""
Training script for BiLSTM + Multi-Head Self-Attention NER model.
"""

from __future__ import annotations

import logging
from pathlib import Path

import torch
import torch.nn as nn
from torch.utils.data import DataLoader

from app.ml.ner.dataset import (
    IDX2TAG,
    NERDataset,
    TAG2IDX,
    TAGS,
    Vocabulary,
    pad_collate_fn,
)
from app.ml.ner.model import BiLSTMAttentionNER
from app.ml.ner.synthetic_data import generate_dataset

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def train_ner(
    epochs: int = 15,
    batch_size: int = 32,
    lr: float = 2e-3,
    save_dir: Path | str | None = None,
) -> None:
    """Train and evaluate the BiLSTMAttentionNER model."""
    if save_dir is None:
        save_path = Path(__file__).resolve().parent.parent / "weights"
    else:
        save_path = Path(save_dir)
    save_path.mkdir(parents=True, exist_ok=True)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info("Using compute device: %s", device)

    # 1. Dataset Generation
    logger.info("Generating training and validation datasets...")
    train_samples, val_samples = generate_dataset(num_train=1200, num_val=250)

    # 2. Vocabulary Construction
    vocab = Vocabulary(min_freq=1)
    vocab.build_vocab([s["tokens"] for s in train_samples])
    vocab_path = save_path / "ner_vocab.json"
    vocab.save(vocab_path)
    logger.info("Vocabulary built with %d unique tokens. Saved to %s", len(vocab), vocab_path)

    # 3. DataLoaders
    train_ds = NERDataset(train_samples, vocab)
    val_ds = NERDataset(val_samples, vocab)

    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True, collate_fn=pad_collate_fn)
    val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False, collate_fn=pad_collate_fn)

    # 4. Model Instantiation
    model = BiLSTMAttentionNER(
        vocab_size=len(vocab),
        num_classes=len(TAGS),
        embed_dim=128,
        hidden_dim=128,
        num_heads=4,
        num_lstm_layers=2,
        dropout=0.2,
        padding_idx=0,
    ).to(device)

    # 5. Loss & Optimizer (ignoring index 0 / padding tokens in loss computation)
    criterion = nn.CrossEntropyLoss(ignore_index=-100)
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs, eta_min=1e-5)

    best_val_f1 = 0.0
    model_save_path = save_path / "ner_model.pt"

    logger.info("Starting training for %d epochs...", epochs)

    for epoch in range(1, epochs + 1):
        # --- Training Loop ---
        model.train()
        total_train_loss = 0.0

        for batch in train_loader:
            input_ids = batch["input_ids"].to(device)
            tag_ids = batch["tag_ids"].to(device)
            mask = batch["mask"].to(device)

            optimizer.zero_grad()
            logits = model(input_ids, mask=mask)  # (batch, seq_len, num_classes)

            # Flatten logits and targets for CrossEntropy
            # Set target of padded tokens to -100 so they are ignored
            targets = tag_ids.clone()
            targets[~mask] = -100

            loss = criterion(logits.view(-1, len(TAGS)), targets.view(-1))
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), max_norm=5.0)
            optimizer.step()

            total_train_loss += loss.item()

        scheduler.step()
        avg_train_loss = total_train_loss / len(train_loader)

        # --- Validation Loop ---
        model.eval()
        total_val_loss = 0.0
        correct_entities = 0
        predicted_entities = 0
        actual_entities = 0

        with torch.no_grad():
            for batch in val_loader:
                input_ids = batch["input_ids"].to(device)
                tag_ids = batch["tag_ids"].to(device)
                mask = batch["mask"].to(device)

                logits = model(input_ids, mask=mask)
                targets = tag_ids.clone()
                targets[~mask] = -100

                loss = criterion(logits.view(-1, len(TAGS)), targets.view(-1))
                total_val_loss += loss.item()

                preds = torch.argmax(logits, dim=-1)  # (batch, seq_len)

                # Entity-level evaluation (excluding 'O' = 0 and padding)
                for b in range(input_ids.shape[0]):
                    seq_m = mask[b]
                    p_seq = preds[b][seq_m].cpu().tolist()
                    t_seq = tag_ids[b][seq_m].cpu().tolist()

                    for p_tag, t_tag in zip(p_seq, t_seq):
                        if t_tag != 0:
                            actual_entities += 1
                        if p_tag != 0:
                            predicted_entities += 1
                        if p_tag != 0 and p_tag == t_tag:
                            correct_entities += 1

        avg_val_loss = total_val_loss / len(val_loader)
        precision = (correct_entities / predicted_entities) if predicted_entities > 0 else 0.0
        recall = (correct_entities / actual_entities) if actual_entities > 0 else 0.0
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0

        logger.info(
            f"Epoch {epoch:02d}/{epochs:02d} | Train Loss: {avg_train_loss:.4f} | "
            f"Val Loss: {avg_val_loss:.4f} | Precision: {precision:.3f} | "
            f"Recall: {recall:.3f} | F1: {f1:.3f}"
        )

        if f1 > best_val_f1:
            best_val_f1 = f1
            torch.save(
                {
                    "epoch": epoch,
                    "model_state_dict": model.state_dict(),
                    "f1": f1,
                    "config": {
                        "vocab_size": len(vocab),
                        "num_classes": len(TAGS),
                        "embed_dim": 128,
                        "hidden_dim": 128,
                        "num_heads": 4,
                        "num_lstm_layers": 2,
                    },
                },
                model_save_path,
            )
            logger.info("--> Saved new best checkpoint to %s (F1: %.3f)", model_save_path, f1)

    logger.info("Training complete! Best Validation F1: %.3f", best_val_f1)


if __name__ == "__main__":
    train_ner()
