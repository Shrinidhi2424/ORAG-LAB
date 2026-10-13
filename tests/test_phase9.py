"""Phase 9 tests (9.3): determinism of the quantum-sim arm, expected seed-to-seed variance, stored-ranking determinism,
and the acceptance artifacts (clean room, numbers audit) when they exist."""
import json
from pathlib import Path

import numpy as np
import pytest

from qrag import emulator as EM
from qrag.rerank import QuantumSimRetriever

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def corpus():
    rng = np.random.default_rng(9)
    c = rng.normal(size=(800, 32)).astype(np.float32)
    c /= np.linalg.norm(c, axis=1, keepdims=True)
    q = (c[:20] + 0.6 * rng.normal(size=(20, 32))).astype(np.float32)
    return c, q / np.linalg.norm(q, axis=1, keepdims=True)


def run(c, q, seed, shots=256, M=50):
    r = QuantumSimRetriever(c, M=M, shots=shots, seed=seed)
    return np.stack([r.retrieve(q[i : i + 1], k=10)[0] for i in range(len(q))])


def test_same_seed_identical_rankings(corpus):
    c, q = corpus
    assert np.array_equal(run(c, q, 7), run(c, q, 7))
    assert np.array_equal(run(c, q, 7, M=None), run(c, q, 7, M=None))


def test_different_seeds_vary_at_low_shots_and_converge_at_high(corpus):
    c, q = corpus
    lo = [run(c, q, s, shots=64) for s in range(4)]
    assert any(not np.array_equal(lo[0], x) for x in lo[1:])  # shot noise reorders candidates
    exact = np.argsort(-(q @ c.T), axis=1, kind="stable")[:, :3]
    hi = run(c, q, 1, shots=10**7)
    assert (np.sort(hi[:, :3], 1) == np.sort(exact, 1)).mean() > 0.95  # vanishing noise -> classical order


def test_seed_variance_matches_theory():
    cos = np.full(20000, 0.6)
    for s in (64, 1024):
        est = np.stack([EM.estimate_c2(cos, s, EM.config_rng(seed, s), clip=False) for seed in range(5)])
        assert est.mean() == pytest.approx(0.36, abs=0.01)
        assert est.std() == pytest.approx(float(EM.theory_sd(np.array([0.6]), s)[0]), rel=0.05)


def rankings():
    cur = ROOT / "results" / "phase3" / ".current_run"
    d = ROOT / "results" / "phase3" / cur.read_text(encoding="utf-8").strip() / "rankings" / "N1000_M50_tieclassical.npz"
    if not d.exists():
        pytest.skip("Phase 3 rankings not present (git-ignored)")
    return np.load(d)


def test_stored_rankings_seed_structure():
    z = rankings()
    shots = list(z["shots"])
    top = z["top"]
    assert top.shape[1] == 5  # R = 5 seeds
    s64 = top[shots.index(64)]
    assert any(not np.array_equal(s64[0], s64[i]) for i in range(1, 5))  # seeds differ at low shots
    sinf = top[shots.index(0)]  # 0 encodes S = infinity (noise-free limit)
    assert all(np.array_equal(sinf[0], sinf[i]) for i in range(1, 5))
    assert np.array_equal(sinf[0], z["classical_top10"])


def phase9_dir():
    cur = ROOT / "results" / "phase9" / ".current_run"
    if not cur.exists():
        pytest.skip("phase 9 not run")
    return ROOT / "results" / "phase9" / cur.read_text(encoding="utf-8").strip()


def test_clean_room_reproduced_everything():
    p = phase9_dir() / "clean_room_summary.json"
    if not p.exists():
        pytest.skip("clean room not run")
    s = json.loads(p.read_text(encoding="utf-8"))
    assert s["different"] == 0 and s["missing"] == 0 and s["comparisons"] > 50


def test_numbers_audit_passes():
    p = phase9_dir() / "number_audit.json"
    if not p.exists():
        pytest.skip("numbers audit not run")
    s = json.loads(p.read_text(encoding="utf-8"))
    assert not s["missing_paths"] and not s["unflagged_hand_numbers"]
