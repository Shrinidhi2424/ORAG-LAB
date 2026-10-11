"""Classical exact (brute-force) cosine retrieval on L2-normalised vectors."""
from __future__ import annotations

import numpy as np


def exact_topk(queries: np.ndarray, corpus: np.ndarray, k: int = 50, chunk: int = 50) -> tuple[np.ndarray, np.ndarray]:
    """Brute-force inner-product top-k. Returns (positions into `corpus`, scores), best first.
    Ties are broken by lower position (stable). Queries are processed in chunks to bound memory (H8)."""
    ids = np.empty((len(queries), k), dtype=np.int32)
    scores = np.empty((len(queries), k), dtype=np.float32)
    for s in range(0, len(queries), chunk):
        sim = queries[s : s + chunk] @ corpus.T
        # stable sort on negated scores: descending score, ties by ascending position
        order = np.argsort(-sim, axis=1, kind="stable")[:, :k]
        ids[s : s + chunk] = order
        scores[s : s + chunk] = np.take_along_axis(sim, order, axis=1)
    return ids, scores


def gold_ranks(queries: np.ndarray, corpus: np.ndarray, gold_pos: np.ndarray, chunk: int = 50) -> np.ndarray:
    """1-based rank of each query's gold item under exact cosine (ties counted pessimistically-free:
    rank = 1 + number of items with strictly higher score, plus lower-position ties, matching exact_topk)."""
    ranks = np.empty(len(queries), dtype=np.int64)
    for s in range(0, len(queries), chunk):
        sim = queries[s : s + chunk] @ corpus.T
        for j in range(sim.shape[0]):
            g = sim[j, gold_pos[s + j]]
            ranks[s + j] = 1 + int((sim[j] > g).sum()) + int((sim[j, : gold_pos[s + j]] == g).sum())
    return ranks
