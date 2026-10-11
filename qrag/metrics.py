"""Retrieval metrics for a single gold item per query (Appendix A.4)."""
from __future__ import annotations

import numpy as np


def hit_at_k(ranks: np.ndarray, k: int) -> float:
    return float((ranks <= k).mean())


def precision_at_k(ranks: np.ndarray, k: int) -> float:
    return hit_at_k(ranks, k) / k  # upper-bounded by 1/k with one gold item


def mrr_at_k(ranks: np.ndarray, k: int = 10) -> float:
    return float(np.where(ranks <= k, 1.0 / ranks, 0.0).mean())


def rbo_ext_matrix(a: np.ndarray, b: np.ndarray, p: float = 0.9) -> np.ndarray:
    """Extrapolated Rank-Biased Overlap (Webber et al. 2010, eq. 32) for equal-depth lists, row-wise.
    a, b: (Q, k) ranked id lists without duplicates. Identical lists give 1."""
    k = a.shape[1]
    eq = a[:, :, None] == b[:, None, :]
    x = np.stack([eq[:, :d, :d].sum(axis=(1, 2)) for d in range(1, k + 1)], axis=1).astype(np.float64)  # X_d
    d = np.arange(1, k + 1)
    return x[:, -1] / k * p**k + (1 - p) / p * (x / d * p**d).sum(axis=1)


def ndcg_at_k(ranks: np.ndarray, k: int = 10) -> float:
    return float(np.where(ranks <= k, 1.0 / np.log2(ranks + 1.0), 0.0).mean())
