"""Phase 3 tests (plan 3.9): emulator statistics, seeds, ranking rules, RBO, Tier A vs Tier B agreement."""
import numpy as np
import pytest

from qrag import emulator as EM
from qrag.metrics import rbo_ext_matrix
from qrag.quantum_swap import SwapTester, swap_test_circuit


def test_p0_in_unit_interval():
    c = np.linspace(-1, 1, 101)
    p = EM.p0(c)
    assert (p >= 0.5).all() and (p <= 1).all()


def test_emulator_unbiased_and_variance_matches_theory():
    c = np.array([0.0, 0.3, 0.6, 0.9])
    S = 1024
    est = EM.estimate_c2(np.repeat(c[:, None], 20000, 1), S, EM.config_rng(1, S), clip=False)
    assert np.allclose(est.mean(1), c**2, atol=4 * EM.theory_sd(c, S).max() / np.sqrt(20000))
    assert np.allclose(est.std(1), EM.theory_sd(c, S), rtol=0.03)


def test_clip_range_and_counts_dtype():
    k = EM.zero_counts(np.full(1000, 0.05), 64, EM.config_rng(0, 64))
    assert k.dtype == np.int32 and k.min() >= 0 and k.max() <= 64
    c2 = EM.c2_from_counts(k, 64)
    assert c2.min() >= 0 and c2.max() <= 1


def test_seeds_reproducible_and_distinct():
    c = np.random.default_rng(0).random(500)
    a = EM.zero_counts(c, 256, EM.config_rng(3, 256, 50, 1000))
    b = EM.zero_counts(c, 256, EM.config_rng(3, 256, 50, 1000))
    d = EM.zero_counts(c, 256, EM.config_rng(4, 256, 50, 1000))
    assert np.array_equal(a, b) and not np.array_equal(a, d)


def test_tie_break_by_classical_then_position():
    c2 = np.array([[0.5, 0.5, 0.7, 0.5]])
    cos = np.array([[0.1, 0.3, 0.2, 0.3]])
    order = EM.topk_from_keys(EM.rank_keys(c2, cos), 4)
    assert order.tolist() == [[2, 1, 3, 0]]  # 0.7 first; ties by cosine 0.3 (pos 1 before 3), then 0.1


def test_tie_term_never_reorders_distinct_estimates():
    S = 16384
    c2 = np.array([[1 / S * 2, 0.0]])
    cos = np.array([[-1.0, 1.0]])
    assert EM.topk_from_keys(EM.rank_keys(c2, cos), 2).tolist() == [[0, 1]]


def test_infinite_shot_limit_equals_classical_for_positive_cosines():
    rng = np.random.default_rng(0)
    cos = np.sort(rng.random((5, 30)))[:, ::-1]
    order = EM.topk_from_keys(EM.rank_keys(cos**2, cos), 10)
    assert (order == np.arange(10)).all()


def test_rbo_bounds():
    a = np.arange(10)[None, :]
    assert rbo_ext_matrix(a, a)[0] == pytest.approx(1.0)
    assert rbo_ext_matrix(a, a + 100)[0] == pytest.approx(0.0)
    swapped = a.copy()
    swapped[0, [0, 1]] = swapped[0, [1, 0]]
    assert 0.8 < rbo_ext_matrix(swapped, a)[0] < 1.0


def test_swap_circuit_shape():
    v = np.ones(512) / np.sqrt(512)
    qc = swap_test_circuit(v, v)
    assert qc.num_qubits == 19 and qc.count_ops()["cswap"] == 9


def test_tierA_matches_tierB_within_tolerance():
    rng = np.random.default_rng(5)
    a = rng.normal(size=512)
    b = a + rng.normal(size=512)
    a, b = a / np.linalg.norm(a), b / np.linalg.norm(b)
    c = float(a @ b)
    S = 8192
    tA = SwapTester(transpile_each=False).similarity(a, b, S, seed=11)
    tB = EM.estimate_c2(np.array([c]), S, EM.config_rng(11, S), clip=False)[0]
    sd = EM.theory_sd(c, S)
    assert abs(tA - c**2) < 4 * sd and abs(tB - c**2) < 4 * sd and abs(tA - tB) < 6 * sd
