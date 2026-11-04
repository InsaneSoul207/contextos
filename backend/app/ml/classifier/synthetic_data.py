"""
Training and validation dataset generator for the Document Classifier.
"""

from __future__ import annotations

import random
from typing import Any

from app.ml.classifier.dataset import CAT2IDX, simple_tokenize

RAW_SAMPLES: dict[str, list[str]] = {
    "Code & Technical Docs": [
        "FastAPI endpoint defined with async def route returning JSON response and Pydantic validation models.",
        "Docker container build failed during cargo build in release mode due to missing libssl development headers.",
        "Refactored SQLite connection pool to enable WAL journal mode and asynchronous connection locks.",
        "Created TypeScript interfaces for the desktop frontend state management with Zustand and Tauri invoke API.",
        "The migration script adds indices on documents table column created_at and full text search virtual table.",
        "Function calculate_embedding takes input string, normalizes whitespace, and generates 384 dimensional dense vector.",
        "Git merge conflict resolved in backend/app/core/database.py. Updated tests and verified CI workflow.",
        "Kubernetes deployment spec configured with rolling update strategy and CPU resource limits.",
        "Implemented Redis cache layer to store session tokens and decrease latency on search requests.",
        "Bug fix: Null pointer exception when parsing malformed JSON payloads from the Chrome extension webhook.",
    ],
    "Research & Academic": [
        "In this work, we propose a novel self-attention mechanism that achieves state of the art results on benchmark datasets.",
        "Empirical evaluation shows an improvement of 4.2 percent in Mean Reciprocal Rank over baseline BM25 retrieval.",
        "We conduct an ablation study analyzing the impact of layer normalization and attention head dimensionality.",
        "The proposed architecture minimizes contrastive triplet loss across multi-modal image and text embedding spaces.",
        "Related work in dense passage retrieval has predominantly explored dual-encoder bi-directional representations.",
        "Figure 3 illustrates the convergence curves under AdamW optimizer with cosine learning rate scheduling.",
        "Our experiments demonstrate that bidirectional representations capture long range syntactic dependencies.",
        "The theoretical formulation proves asymptotic bounds under mild smoothness assumptions for convex optimization.",
        "We evaluate precision and recall across five benchmark corpora including MS-MARCO and SQuAD v2.",
        "The qualitative results highlight that our model eliminates hallucinations through grounded citation generation.",
    ],
    "Meeting & Sync Notes": [
        "Weekly engineering sync: Discussed Q4 roadmap, backend migration blockers, and mobile companion app progress.",
        "Sprint 14 Retrospective: What went well - quick turnaround on bug fixes. What could be improved - test coverage.",
        "Action items from Monday standup: Sarah to review pull request 88, Eshaan to optimize retrieval pipeline.",
        "Meeting with product lead regarding user onboarding feedback and search latency metrics.",
        "Notes from design review: Simplified navigation bar layout and improved contrast for dark mode theme.",
        "Quarterly business review: Outlined key performance indicators, active user growth, and infrastructure costs.",
        "Discussion on database schema changes: Agreed to postpone deprecating legacy fields until next release.",
        "All hands meeting minutes: CEO shared vision for upcoming AI initiatives and annual performance review cycle.",
        "Sync with security team: Completed penetration testing audit and scheduled dependency updates.",
        "Client sync summary: Confirmed delivery deadline for beta milestone on December 15th.",
    ],
    "Coursework & Study": [
        "Midterm examination review: Study chapters 4 through 7 covering gradient descent and backpropagation.",
        "Homework 3 Problem 2: Derive the update rule for multi-class logistic regression using cross entropy loss.",
        "Computer Science Lab 4: Implement a binary search tree in C++ with recursive traversal algorithms.",
        "Syllabus for Information Retrieval: Lectures on inverted indices, vector space models, and evaluation metrics.",
        "Assignment submission deadline is Friday at 11:59 PM. Late submissions will receive a 10% penalty per day.",
        "Read pages 140 to 185 before next Tuesday's lecture on Convolutional Neural Networks and pooling layers.",
        "Study notes for final exam: Definitions of eigenvalues, eigenvectors, and singular value decomposition.",
        "Professor office hours: Mondays and Wednesdays from 2 PM to 4 PM in Engineering Building room 302.",
        "Group project milestone: Submit the literature review and proposal document in PDF format on Canvas.",
        "Quiz preparation: Review the difference between supervised, unsupervised, and reinforcement learning paradigms.",
    ],
    "Financial & Receipts": [
        "Invoice INV-2026-094: Total amount due $450.00. Payment terms: Net 30 days from invoice date.",
        "Amazon Web Services monthly billing statement: EC2 instance charges $34.20, S3 storage $12.50, Total $46.70.",
        "Receipt for software subscription: GitHub Copilot annual license renewal $100.00 charged to Visa ending in 4021.",
        "Payment confirmation: Your payment of $1,250.00 for office rent has been successfully processed.",
        "Tax statement for financial year 2025: Form 1099 miscellaneous income summary and deductions itemized.",
        "Expense report submission: Travel expenses for developer conference including flight and hotel accommodations.",
        "Bank transaction notification: Direct deposit received from payroll in the amount of $3,800.00.",
        "Order receipt from Apple Store: MacBook Pro M3 repair and battery replacement, total paid with tax $249.00.",
        "Utility bill for electricity and high speed fiber internet: Due date November 28, balance $89.45.",
        "Vendor invoice for cloud GPU compute hours: 150 hours of A100 training cluster at $2.20 per hour.",
    ],
    "Personal & Notes": [
        "Weekend to-do list: Buy groceries, clean bicycle chain, call parents, and finish reading chapter 5 of Sci-Fi book.",
        "Workout routine: 5 km morning run, 3 sets of pull-ups, core strengthening exercises, and 15 minute stretching.",
        "Packing checklist for upcoming mountain trip: Warm jacket, hiking boots, camera batteries, water bottle.",
        "Personal book recommendations for this year: Project Hail Mary, Atomic Habits, and Clean Architecture.",
        "Ideas for side project: A browser extension that automatically organizes open tabs by task context.",
        "Recipe for homemade vegetarian pasta: Olive oil, minced garlic, cherry tomatoes, fresh basil, and parmesan.",
        "Journal entry: Great productive day today, managed to finish all assigned coding tasks before evening.",
        "Car maintenance notes: Scheduled oil change and tire rotation at local service center next Saturday.",
        "Gift ideas for sister's birthday: Noise cancelling headphones or watercolor painting set.",
        "Home organization: Declutter desk drawer, organize USB cables, and label storage boxes.",
    ],
}


def generate_classification_dataset(
    num_train: int = 1500, num_val: int = 300, seed: int = 42
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Generate balanced text classification samples with data augmentation."""
    random.seed(seed)
    categories = list(RAW_SAMPLES.keys())

    def augment_text(text: str) -> str:
        words = text.split()
        if len(words) > 8 and random.random() < 0.3:
            # Drop 1 random word
            drop_idx = random.randint(0, len(words) - 1)
            words.pop(drop_idx)
        return " ".join(words)

    def create_split(count_per_cat: int) -> list[dict[str, Any]]:
        samples = []
        for cat in categories:
            templates = RAW_SAMPLES[cat]
            label_id = CAT2IDX[cat]
            for _ in range(count_per_cat):
                base_text = random.choice(templates)
                # Combine two sentences occasionally for longer document context
                if random.random() < 0.4:
                    second_text = random.choice(templates)
                    full_text = f"{base_text} {second_text}"
                else:
                    full_text = base_text

                full_text = augment_text(full_text)
                tokens = simple_tokenize(full_text)
                samples.append({
                    "text": full_text,
                    "tokens": tokens,
                    "category": cat,
                    "label": label_id,
                })
        random.shuffle(samples)
        return samples

    train_samples = create_split(num_train // len(categories))
    val_samples = create_split(num_val // len(categories))
    return train_samples, val_samples
