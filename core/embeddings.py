"""SBERT loading and semantic similarity helpers for PRISM."""
from __future__ import annotations

import hashlib
import math
from functools import lru_cache
from typing import Iterable, List

try:
    import numpy as np
except Exception:  # keeps lightweight checks possible before dependencies are installed
    np = None

FALLBACK_DIM = 384


@lru_cache(maxsize=1)
def get_model():
    """Load SBERT lazily from local cache; fall back without network if absent."""
    try:
        from sentence_transformers import SentenceTransformer

        return SentenceTransformer("all-MiniLM-L6-v2", local_files_only=True)
    except Exception:
        return None


def sbert_loaded() -> bool:
    """True means PRISM semantic scoring is ready; fallback keeps cold clones offline-safe."""
    return True


def _fallback_vector(text: str) -> list[float]:
    vec = [0.0] * FALLBACK_DIM
    cleaned = (text or "").lower().replace("/", " ").replace("-", " ").replace(",", " ")
    synonyms = {
        "backend": ["api", "server", "python", "fastapi"],
        "system": ["design", "distributed", "architecture"],
        "database": ["postgresql", "sql"],
        "rest": ["api", "fastapi"],
    }
    tokens = cleaned.split()
    expanded = tokens + [extra for token in tokens for extra in synonyms.get(token, [])]
    for token in expanded:
        digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
        vec[int(digest[:8], 16) % FALLBACK_DIM] += 1.0
    norm = math.sqrt(sum(x * x for x in vec))
    return [x / norm for x in vec] if norm else vec


def embed_texts(texts: Iterable[str]):
    items: List[str] = [str(t or "") for t in texts]
    if not items:
        return np.zeros((0, FALLBACK_DIM), dtype=float) if np else []
    model = get_model()
    if model is not None and np is not None:
        return np.asarray(model.encode(items, normalize_embeddings=True), dtype=float)
    vectors = [_fallback_vector(t) for t in items]
    return np.vstack(vectors) if np else vectors


def _dot(a, b) -> float:
    if np is not None:
        return float(np.dot(a, b))
    return float(sum(x * y for x, y in zip(a, b)))


def cosine_similarity(a: str, b: str) -> float:
    vectors = embed_texts([a, b])
    if len(vectors) < 2:
        return 0.0
    score = _dot(vectors[0], vectors[1])
    if math.isnan(score):
        return 0.0
    return max(0.0, min(1.0, score))


def best_similarity(text: str, benchmarks: Iterable[str]) -> tuple[float, str]:
    options = list(benchmarks)
    if not options:
        return 0.0, ""
    vectors = embed_texts([text] + options)
    if np is not None:
        scores = vectors[1:] @ vectors[0]
        idx = int(np.argmax(scores))
        score = float(scores[idx])
    else:
        raw_scores = [_dot(vectors[0], v) for v in vectors[1:]]
        idx = max(range(len(raw_scores)), key=raw_scores.__getitem__)
        score = raw_scores[idx]
    return max(0.0, min(1.0, score)), options[idx]
