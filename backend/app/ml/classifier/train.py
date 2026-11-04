"""
Training script for the Custom Transformer Document Classifier.
"""

from __future__ import annotations

import logging
from pathlib import Path

import torch
import torch.nn as nn
from torch.utils.data import DataLoader

from app.ml.classifier.dataset import (
    CATEGORIES,
    ClassifierVocabulary,
    TextClassificationDataset,
    classifier_collate_fn,
)
from app.ml.classifier.model import DocumentTransformerClassifier
from app.ml.classifier.synthetic_data import generate_classification_dataset

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def train_classifier(
    epochs: int = 12,
    batch_size: int = 32,
    lr: float = 1.5e-3,
    save_dir: Path | str | None = None,
) -> None:
    """Train and evaluate the custom Transformer classifier."""
    if save_dir is None:
        save_path = Path(__file__).resolve().parent.parent / "weights"
    else:
        save_path = Path(save_dir)
    save_path.mkdir(parents=True, exist_ok=True)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info("Using device: %s", device)

    # 1. Dataset Generation
    logger.info("Generating classification datasets...")
    train_samples, val_samples = generate_classification_dataset(num_train=1800, num_val=360)

    # 2. Vocabulary Construction
    vocab = ClassifierVocabulary(min_freq=1)
    vocab.build_vocab([s["tokens"] for s in train_samples])
    vocab_path = save_path / "classifier_vocab.json"
    vocab.save(vocab_path)
    logger.info("Classifier vocabulary size: %d tokens. Saved to %s", len(vocab), vocab_path)

    # 3. DataLoaders
    train_ds = TextClassificationDataset(train_samples, vocab, max_len=256)
    val_ds = TextClassificationDataset(val_samples, vocab, max_len=256)

    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True, collate_fn=classifier_collate_fn)
    val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False, collate_fn=classifier_collate_fn)

    # 4. Model Instantiation
    model = DocumentTransformerClassifier(
        vocab_size=len(vocab),
        num_classes=len(CATEGORIES),
        d_model=128,
        num_heads=4,
        d_ff=256,
        num_layers=2,
        max_seq_len=256,
        dropout=0.2,
        padding_idx=0,
    ).to(device)

    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs, eta_min=1e-5)

    best_val_acc = 0.0
    model_save_path = save_path / "classifier_model.pt"

    logger.info("Training custom Transformer for %d epochs...", epochs)

    for epoch in range(1, epochs + 1):
        # --- Training Loop ---
        model.train()
        total_loss = 0.0
        correct_train = 0
        total_train = 0

        for batch in train_loader:
            input_ids = batch["input_ids"].to(device)
            mask = batch["mask"].to(device)
            labels = batch["labels"].to(device)

            optimizer.zero_grad()
            logits = model(input_ids, mask=mask)
            loss = criterion(logits, labels)
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), max_norm=3.0)
            optimizer.step()

            total_loss += loss.item()
            preds = torch.argmax(logits, dim=-1)
            correct_train += (preds == labels).sum().item()
            total_train += labels.size(0)

        scheduler.step()
        train_acc = correct_train / total_train
        avg_train_loss = total_loss / len(train_loader)

        # --- Validation Loop ---
        model.eval()
        total_val_loss = 0.0
        correct_val = 0
        total_val = 0

        with torch.no_grad():
            for batch in val_loader:
                input_ids = batch["input_ids"].to(device)
                mask = batch["mask"].to(device)
                labels = batch["labels"].to(device)

                logits = model(input_ids, mask=mask)
                loss = criterion(logits, labels)
                total_val_loss += loss.item()

                preds = torch.argmax(logits, dim=-1)
                correct_val += (preds == labels).sum().item()
                total_val += labels.size(0)

        val_acc = correct_val / total_val
        avg_val_loss = total_val_loss / len(val_loader)

        logger.info(
            f"Epoch {epoch:02d}/{epochs:02d} | Train Loss: {avg_train_loss:.4f} | "
            f"Train Acc: {train_acc * 100:.2f}% | Val Loss: {avg_val_loss:.4f} | "
            f"Val Acc: {val_acc * 100:.2f}%"
        )

        if val_acc > best_val_acc:
            best_val_acc = val_acc
            torch.save(
                {
                    "epoch": epoch,
                    "model_state_dict": model.state_dict(),
                    "val_acc": val_acc,
                    "config": {
                        "vocab_size": len(vocab),
                        "num_classes": len(CATEGORIES),
                        "d_model": 128,
                        "num_heads": 4,
                        "d_ff": 256,
                        "num_layers": 2,
                    },
                },
                model_save_path,
            )
            logger.info("--> Saved best classifier checkpoint to %s (Val Acc: %.2f%%)", model_save_path, val_acc * 100)

    logger.info("Classifier training complete! Peak Validation Accuracy: %.2f%%", best_val_acc * 100)


if __name__ == "__main__":
    train_classifier()
