"""Retrieval metrics for a single gold item per query (Appendix A.4)."""
from __future__ import annotations

import numpy as np


def hit_at_k(ranks: np.ndarray, k: int) -> float:
    return float((ranks <= k).mean())


def precision_at_k(ranks: np.ndarray, k: int) -> float:
    return hit_at_k(ranks, k) / k  # upper-bounded by 1/k with one gold item


def mrr_at_k(ranks: np.ndarray, k: int = 10) -> float:
    return float(np.where(ranks <= k, 1.0 / ranks, 0.0).mean())


def ndcg_at_k(ranks: np.ndarray, k: int = 10) -> float:
    return float(np.where(ranks <= k, 1.0 / np.log2(ranks + 1.0), 0.0).mean())
