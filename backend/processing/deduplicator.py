"""
Duplicate detection using embedding-based text similarity.

Uses sentence-transformers with a multilingual model to compare
news articles. If cosine similarity ≥ 0.90, the news is considered
a duplicate and its source is merged into the existing record.

Graceful fallback: if the model cannot be loaded (e.g. incompatible
Python version, missing deps), duplicate detection is skipped and
every article is treated as unique.
"""

import numpy as np
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import SIMILARITY_THRESHOLD
from database.mongo_client import db

# Load model once (lazy)
_model = None
_model_failed = False


def _get_model():
    global _model, _model_failed
    if _model_failed:
        return None
    if _model is None:
        try:
            from sentence_transformers import SentenceTransformer
            print("[Deduplicator] Loading sentence-transformer model...")
            _model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
            print("[Deduplicator] Model loaded.")
        except Exception as e:
            print(f"[Deduplicator] WARNING: Could not load model: {e}")
            print("[Deduplicator] Duplicate detection will be DISABLED.")
            _model_failed = True
            return None
    return _model


def compute_embedding(title: str, content: str) -> list[float]:
    """
    Compute embedding vector for a news article.
    Uses title + first 300 chars of content for efficiency.
    Returns empty list if model is unavailable.
    """
    model = _get_model()
    if model is None:
        return []
    text = f"{title}. {content[:300]}"
    embedding = model.encode(text, convert_to_numpy=True)
    return embedding.tolist()


def find_duplicate(embedding: list[float]) -> dict | None:
    """
    Check if a similar news item already exists in the DB.

    Returns the existing document dict (with _id) if similarity ≥ threshold,
    otherwise None. Returns None if embedding is empty (model unavailable).
    """
    if not embedding:
        return None

    existing = db.get_all_embeddings()
    if not existing:
        return None

    new_vec = np.array(embedding).reshape(1, -1)

    for doc in existing:
        if not doc.get("embedding"):
            continue
        try:
            from sklearn.metrics.pairwise import cosine_similarity
            existing_vec = np.array(doc["embedding"]).reshape(1, -1)
            sim = cosine_similarity(new_vec, existing_vec)[0][0]
            if sim >= SIMILARITY_THRESHOLD:
                return {
                    "_id": str(doc["_id"]),
                    "title": doc.get("title", ""),
                    "similarity": float(sim),
                }
        except Exception:
            continue

    return None
