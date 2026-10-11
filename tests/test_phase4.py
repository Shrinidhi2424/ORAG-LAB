"""Phase 4 tests: Holm, paired tests, power-law fit, QuantumSimRetriever behaviour."""
import numpy as np
import pytest

from qrag import emulator as EM
from qrag.index_classical import build_flat, exact_topk
from qrag.rerank import QuantumSimRetriever
from qrag.stats import holm, loglog_slope_ci, mcnemar_exact, paired_bootstrap_p


def test_holm_matches_reference():
    adj = holm([0.01, 0.04, 0.03, 0.005])
    assert np.allclose(adj, [0.03, 0.06, 0.06, 0.02])


def test_holm_monotone_and_capped():
    adj = holm(np.random.default_rng(0).random(20))
    assert adj.max() <= 1 and (adj >= 0).all()


def test_paired_bootstrap_p_null_and_effect():
    rng = np.random.default_rng(1)
    assert paired_bootstrap_p(rng.normal(0, 1, 300)) > 0.05
    assert paired_bootstrap_p(rng.normal(0.5, 1, 300)) < 0.01


def test_mcnemar_exact():
    a = np.array([1] * 10 + [0] * 2 + [1] * 8, bool)
    b = np.array([0] * 10 + [1] * 2 + [1] * 8, bool)
    n10, n01, p = mcnemar_exact(a, b)
    assert (n10, n01) == (10, 2) and p == pytest.approx(0.03857421875)
    assert mcnemar_exact(a, a)[2] == 1.0


def test_loglog_slope_recovers_exponent():
    xs = np.array([1e3, 2e3, 5e3, 1e4, 2e4])
    rng = np.random.default_rng(0)
    ys = [3e-6 * x**1.0 * (1 + 0.02 * rng.normal(size=5)) for x in xs]
    b, lo, hi, r2 = loglog_slope_ci(xs, ys, n_boot=500)
    assert lo <= b <= hi and abs(b - 1.0) < 0.05 and r2 > 0.99


@pytest.fixture(scope="module")
def corpus():
    rng = np.random.default_rng(2)
    c = rng.normal(size=(600, 24)).astype(np.float32)
    return c / np.linalg.norm(c, axis=1, keepdims=True)


def test_retriever_high_shots_matches_exact(corpus):
    q = corpus[5:6] + 0.05
    q = (q / np.linalg.norm(q)).astype(np.float32)
    ret = QuantumSimRetriever(corpus, M=50, shots=2**20, seed=0)
    ids, _ = ret.retrieve(q, 5)
    assert set(ids.tolist()) == set(exact_topk(q, corpus, 5)[0][0].tolist())
    assert ids[0] == exact_topk(q, corpus, 1)[0][0, 0]


def test_retriever_seeded_and_stage_timings(corpus):
    q = np.ascontiguousarray(corpus[:1])
    st = {}
    a = QuantumSimRetriever(corpus, 20, 64, seed=3).retrieve(q, 5, st)[0]
    b = QuantumSimRetriever(corpus, 20, 64, seed=3).retrieve(q, 5)[0]
    assert np.array_equal(a, b) and set(st) == {"search_s", "estimate_s", "rank_s"}


def test_full_scan_returns_valid_positions(corpus):
    q = np.ascontiguousarray(corpus[7:8])
    ids, c2 = QuantumSimRetriever(corpus, None, 4096, seed=0).retrieve(q, 10)
    assert len(set(ids.tolist())) == 10 and ids.max() < len(corpus) and (c2 >= 0).all() and (c2 <= 1).all()
    assert 7 in ids.tolist()
