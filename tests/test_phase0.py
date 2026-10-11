"""Phase 0 smoke tests: utilities, manifest, and the Qiskit/Aer SWAP-test circuit from plan D2."""
import json

import numpy as np
import pytest

from qrag.manifest import build_manifest, write_run_manifest
from qrag.seed import set_global_seed
from qrag.timing import Stopwatch, summarize, time_calls


def test_seed_reproducible():
    a = set_global_seed(7).random(5)
    b = set_global_seed(7).random(5)
    assert np.array_equal(a, b)
    assert not np.array_equal(a, set_global_seed(8).random(5))


def test_timing_discards_warmup():
    calls = []
    samples, stats = time_calls(lambda x: calls.append(x), list(range(15)), warmup=10)
    assert len(calls) == 15 and len(samples) == 5 and stats.n == 5
    assert stats.median_ms <= stats.p95_ms <= stats.max_ms


def test_summarize_percentiles():
    s = summarize([0.001] * 99 + [0.1])
    assert s.median_ms == pytest.approx(1.0)
    assert s.p95_ms == pytest.approx(1.0, abs=1e-6)


def test_stopwatch():
    with Stopwatch() as sw:
        pass
    assert sw.elapsed >= 0


def test_manifest_contents(tmp_path):
    m = build_manifest("phase0", "t", seeds={"global": 42})
    assert m["seeds"] == {"global": 42}
    assert m["packages"]["qiskit"] and m["packages"]["faiss-cpu"]
    p = write_run_manifest(tmp_path, "phase0", "t")
    assert json.loads(p.read_text(encoding="utf-8"))["run_id"] == "t"


def test_core_imports():
    import faiss
    import qiskit
    import qiskit_aer
    import sentence_transformers  # noqa: F401
    import torch

    assert not torch.cuda.is_available() or True  # GPU deliberately unused (H3)
    assert faiss.IndexFlatIP(4).d == 4
    assert qiskit.__version__ and qiskit_aer.__version__


def test_swap_test_circuit_matches_cos2():
    """D2 recipe on 3+3 qubits: set_statevector + SWAP test; estimate ~ cos^2 within shot noise."""
    from qiskit import QuantumCircuit, transpile
    from qiskit_aer import AerSimulator

    rng = np.random.default_rng(0)
    n = 3
    a = rng.normal(size=2**n)
    b = a + 0.8 * rng.normal(size=2**n)
    a, b = a / np.linalg.norm(a), b / np.linalg.norm(b)
    psi = np.kron(b, np.kron(a, [1.0, 0.0])).astype(complex)
    qc = QuantumCircuit(1 + 2 * n, 1)
    qc.set_statevector(psi)
    qc.h(0)
    for i in range(n):
        qc.cswap(0, 1 + i, 1 + n + i)
    qc.h(0)
    qc.measure(0, 0)
    shots = 8192
    sim = AerSimulator(seed_simulator=1)
    counts = sim.run(transpile(qc, sim), shots=shots).result().get_counts()
    est = 2 * counts.get("0", 0) / shots - 1
    true = float(a @ b) ** 2
    assert abs(est - true) < 5 * 2 * np.sqrt(0.25 / shots)
