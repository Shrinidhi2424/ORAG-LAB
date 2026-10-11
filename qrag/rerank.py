"""Two-stage 'shortlist then estimate' retrieval with the quantum-inspired (SWAP-test) estimator (plan D3).

Stage 1: exact FAISS Flat search returns the top-M shortlist (cosine scores).
Stage 2: Tier B emulator draws k ~ Binomial(S, (1 + cos^2) / 2) per shortlisted item and ranks by the clipped
estimate 2k/S - 1; ties by classical cosine, then position. M = None scans the whole corpus (full-scan ablation).
Latency of this class is EMULATED-estimator latency, not quantum latency.
"""
from __future__ import annotations

import time

import numpy as np

from qrag import emulator as EM
from qrag.index_classical import build_flat


class QuantumSimRetriever:
    def __init__(self, corpus: np.ndarray, M: int | None = 50, shots: int = 1024, seed: int = 0, flat_index=None):
        self.corpus = np.ascontiguousarray(corpus, dtype=np.float32)
        self.M, self.shots = M, shots
        self.index = flat_index if flat_index is not None else (build_flat(self.corpus) if M is not None else None)
        self.rng = np.random.default_rng(seed)

    def retrieve(self, q: np.ndarray, k: int = 10, stages: dict | None = None) -> tuple[np.ndarray, np.ndarray]:
        """q: (1, d) float32. Returns (positions, estimated cos^2) of the top-k. Fills `stages` with seconds."""
        t0 = time.perf_counter()
        if self.M is None:
            cos = (self.corpus @ q[0]).astype(np.float64)
            cand = None
        else:
            scores, cand = self.index.search(q, self.M)
            cos, cand = scores[0].astype(np.float64), cand[0]
        t1 = time.perf_counter()
        c2 = EM.c2_from_counts(EM.zero_counts(cos, self.shots, self.rng), self.shots, clip=True)
        keys = EM.rank_keys(c2, cos)
        t2 = time.perf_counter()
        if self.M is None:  # partial selection first: O(N) instead of a full sort
            part = np.argpartition(-keys, k - 1)[:k]
            order = part[np.argsort(-keys[part], kind="stable")]
        else:
            order = np.argsort(-keys, kind="stable")[:k]
        t3 = time.perf_counter()
        if stages is not None:
            stages.update(search_s=t1 - t0, estimate_s=t2 - t1, rank_s=t3 - t2)
        return (order if cand is None else cand[order]), c2[order]
