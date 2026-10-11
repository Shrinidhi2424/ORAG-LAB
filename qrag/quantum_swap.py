"""Tier A: SWAP-test similarity on real Qiskit circuits, simulated by Aer (plan D2, task 3.2).

State loading uses Aer's set_statevector with the classically built joint state (plan D2): the SWAP test
itself (H, controlled-SWAPs, H, measure) is executed by the simulator; only state preparation is
shortcut. Qubit 0 = ancilla, qubits 1..n = register A, n+1..2n = register B (Qiskit is little-endian,
hence kron(b, kron(a, |0>))).
"""
from __future__ import annotations

import numpy as np

N_QUBITS_REG = 9  # 512 = 2^9 amplitudes per register


def _unit(v: np.ndarray) -> np.ndarray:
    v = np.asarray(v, dtype=np.float64)
    return v / np.linalg.norm(v)


def swap_test_circuit(a: np.ndarray, b: np.ndarray, measure: bool = True):
    """SWAP-test circuit for unit vectors a, b of length 2^n, loaded via set_statevector."""
    import qiskit_aer  # noqa: F401 - importing Aer registers QuantumCircuit.set_statevector
    from qiskit import QuantumCircuit

    a, b = _unit(a), _unit(b)
    n = int(np.log2(len(a)))
    assert len(a) == len(b) == 2**n, "vectors must have length 2^n"
    psi = np.kron(b, np.kron(a, [1.0, 0.0])).astype(complex)
    qc = QuantumCircuit(1 + 2 * n, 1 if measure else 0)
    qc.set_statevector(psi)
    qc.h(0)
    for i in range(n):
        qc.cswap(0, 1 + i, 1 + n + i)
    qc.h(0)
    if measure:
        qc.measure(0, 0)
    return qc


class SwapTester:
    """Runs SWAP tests on AerSimulator (ideal, noise-free statevector method)."""

    def __init__(self, transpile_each: bool = True):
        from qiskit_aer import AerSimulator

        self.sim = AerSimulator(method="statevector")
        self.transpile_each = transpile_each

    def zero_counts(self, a: np.ndarray, b: np.ndarray, shots: int, seed: int) -> int:
        """Number of ancilla-0 outcomes in `shots` shots."""
        from qiskit import transpile

        qc = swap_test_circuit(a, b)
        if self.transpile_each:
            qc = transpile(qc, self.sim)
        counts = self.sim.run(qc, shots=shots, seed_simulator=int(seed)).result().get_counts()
        return int(counts.get("0", 0))

    def similarity(self, q: np.ndarray, d: np.ndarray, shots: int, seed: int, clip: bool = False) -> float:
        """Estimate of cos^2(q, d): c2_hat = 2k/S - 1 (unbiased when clip=False)."""
        c2 = 2.0 * self.zero_counts(q, d, shots, seed) / shots - 1.0
        return float(min(max(c2, 0.0), 1.0)) if clip else c2


def resource_counts(a: np.ndarray, b: np.ndarray, basis=("cx", "u"), optimization_level: int = 1) -> dict:
    """Gate/depth counts of the FULL circuit with generic StatePreparation decomposition (for T6 only;
    never executed). Also counts the SWAP-test core alone."""
    from qiskit import QuantumCircuit, transpile
    from qiskit.circuit.library import StatePreparation

    a, b = _unit(a), _unit(b)
    n = int(np.log2(len(a)))
    full = QuantumCircuit(1 + 2 * n, 1)
    full.append(StatePreparation(a), list(range(1, 1 + n)))
    full.append(StatePreparation(b), list(range(1 + n, 1 + 2 * n)))
    core = QuantumCircuit(1 + 2 * n, 1)
    for qc in (full, core):
        qc.h(0)
        for i in range(n):
            qc.cswap(0, 1 + i, 1 + n + i)
        qc.h(0)
        qc.measure(0, 0)
    out = {}
    for name, qc in (("full_with_state_prep", full), ("swap_test_core", core)):
        t = transpile(qc, basis_gates=list(basis), optimization_level=optimization_level, seed_transpiler=42)
        ops = dict(t.count_ops())
        out[name] = {"qubits": t.num_qubits, "depth": t.depth(), "ops": {k: int(v) for k, v in ops.items()},
                     "two_qubit_gates": int(sum(v for k, v in ops.items() if k in ("cx", "cz", "ecr"))),
                     "one_qubit_gates": int(sum(v for k, v in ops.items() if k in ("u", "u3", "rz", "sx", "x", "h")))}
    out["basis"] = list(basis)
    out["optimization_level"] = optimization_level
    out["statevector_bytes_complex128"] = int(16 * 2 ** (1 + 2 * n))
    return out
