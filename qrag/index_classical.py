"""Classical retrieval: numpy brute force (reference) and FAISS Flat / IVF wrappers (Phase 2)."""
from __future__ import annotations

import time

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
    """1-based rank of each query's gold item under exact cosine: 1 + number of items with a strictly
    higher score + lower-position ties, matching the tie-breaking of exact_topk."""
    ranks = np.empty(len(queries), dtype=np.int64)
    for s in range(0, len(queries), chunk):
        sim = queries[s : s + chunk] @ corpus.T
        for j in range(sim.shape[0]):
            g = sim[j, gold_pos[s + j]]
            ranks[s + j] = 1 + int((sim[j] > g).sum()) + int((sim[j, : gold_pos[s + j]] == g).sum())
    return ranks


def ranks_from_ids(ids: np.ndarray, gold_pos: np.ndarray, missing: int = 10**6) -> np.ndarray:
    """Gold rank within returned top-k id lists; `missing` if the gold item is not in the list."""
    hit = ids == gold_pos[:, None]
    return np.where(hit.any(axis=1), hit.argmax(axis=1) + 1, missing).astype(np.int64)


def overlap_at_k(ids_a: np.ndarray, ids_b: np.ndarray, k: int) -> np.ndarray:
    """Per-query |top-k(a) ∩ top-k(b)| / k."""
    return np.array([len(set(a[:k].tolist()) & set(b[:k].tolist())) / k for a, b in zip(ids_a, ids_b)])


# ---- FAISS wrappers --------------------------------------------------------------------------------

def build_flat(vecs: np.ndarray):
    import faiss

    index = faiss.IndexFlatIP(vecs.shape[1])
    index.add(vecs)
    return index


def default_nlist(n: int) -> int:
    return max(1, round(n**0.5))


def build_ivf(vecs: np.ndarray, nlist: int | None = None, seed: int = 42, train_per_list: int = 50):
    """IndexIVFFlat (inner product). k-means trained on a fixed seeded sample of the same vectors."""
    import faiss

    n, d = vecs.shape
    nlist = nlist or default_nlist(n)
    quantizer = faiss.IndexFlatIP(d)
    index = faiss.IndexIVFFlat(quantizer, d, nlist, faiss.METRIC_INNER_PRODUCT)
    index.cp.seed = seed
    sample_n = min(n, train_per_list * nlist)
    sample = vecs[np.random.default_rng(seed).choice(n, size=sample_n, replace=False)]
    index.train(sample)
    index.add(vecs)
    return index


def search(index, queries: np.ndarray, k: int) -> tuple[np.ndarray, np.ndarray, float]:
    """FAISS search wrapper: returns (ids, scores, elapsed seconds). Missing results are -1."""
    t0 = time.perf_counter()
    scores, ids = index.search(queries, k)
    return ids, scores, time.perf_counter() - t0


def index_bytes(index) -> int:
    import faiss

    return int(len(faiss.serialize_index(index)))
