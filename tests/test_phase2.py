"""Phase 2 tests (plan 2.5): FAISS Flat == numpy brute force; IVF recall -> 1 as nprobe -> nlist; stats helpers."""
import numpy as np
import pytest

from qrag.index_classical import (build_flat, build_ivf, default_nlist, exact_topk, index_bytes, overlap_at_k,
                                  ranks_from_ids, search)
from qrag.stats import bootstrap_ci


@pytest.fixture(scope="module")
def data():
    rng = np.random.default_rng(3)
    c = rng.normal(size=(2000, 32)).astype(np.float32)
    c /= np.linalg.norm(c, axis=1, keepdims=True)
    q = c[rng.choice(2000, 40, replace=False)] + 0.3 * rng.normal(size=(40, 32)).astype(np.float32)
    q /= np.linalg.norm(q, axis=1, keepdims=True)
    return c, q


def test_flat_equals_numpy_bruteforce(data):
    c, q = data
    ids, sc, dt = search(build_flat(c), q, 20)
    ref_ids, ref_sc = exact_topk(q, c, 20)
    assert dt >= 0
    assert np.allclose(sc, ref_sc, atol=1e-5)
    assert np.mean([set(a) == set(b) for a, b in zip(ids, ref_ids)]) == 1.0


def test_ivf_recall_reaches_one_at_full_nprobe(data):
    c, q = data
    nlist = default_nlist(len(c))
    ivf = build_ivf(c, nlist)
    ref, _ = exact_topk(q, c, 10)
    rec = {}
    for npr in (1, 4, nlist):
        ivf.nprobe = npr
        ids, _, _ = search(ivf, q, 10)
        rec[npr] = overlap_at_k(ids, ref, 10).mean()
    assert rec[1] <= rec[4] <= rec[nlist]
    assert rec[nlist] == pytest.approx(1.0)


def test_ivf_is_deterministic(data):
    c, q = data
    a, b = build_ivf(c, 20, seed=42), build_ivf(c, 20, seed=42)
    a.nprobe = b.nprobe = 3
    assert np.array_equal(search(a, q, 5)[0], search(b, q, 5)[0])


def test_ranks_from_ids_and_index_bytes(data):
    c, _ = data
    ids = np.array([[5, 7, 9], [1, 2, 3]])
    assert ranks_from_ids(ids, np.array([9, 4])).tolist() == [3, 10**6]
    assert index_bytes(build_flat(c)) >= c.nbytes


def test_bootstrap_ci_covers_mean():
    v = (np.random.default_rng(0).random(300) < 0.6).astype(float)
    est, lo, hi = bootstrap_ci(v, n_boot=2000)
    assert lo <= est <= hi and hi - lo < 0.2
