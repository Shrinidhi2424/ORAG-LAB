"""Phase 7 tests: Pareto dominance, settled-from rule, modelled-cost scaling, artifact consistency."""
import csv
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import run_phase7 as P7  # noqa: E402


def pt(x, y, ylo=None, yhi=None):
    return {"x": x, "y": y, "xlo": x, "xhi": x, "ylo": y if ylo is None else ylo, "yhi": y if yhi is None else yhi}


IV = dict(xlo="xlo", xhi="xhi", ylo="ylo", yhi="yhi")


def test_dominance_basic():
    a, b, c = pt(1, 1), pt(2, 2), pt(1, 3)
    assert P7.dominates(a, b, "x", "y") and not P7.dominates(b, a, "x", "y")
    assert P7.dominates(a, c, "x", "y")  # equal x, strictly better y
    assert not P7.dominates(a, pt(1, 1), "x", "y")  # identical points do not dominate each other


def test_front_flags_and_robustness():
    pts = [pt(1, 1, 0.9, 1.1), pt(2, 2, 1.9, 2.1)]
    P7.front(pts, "x", "y", **IV)
    assert pts[0]["non_dominated"] and not pts[1]["non_dominated"]
    assert pts[1]["robustly_dominated"]  # y intervals disjoint
    q = [pt(1, 1, 0.5, 1.5), pt(1, 1.2, 0.8, 1.6)]
    P7.front(q, "x", "y", **IV)
    assert q[1]["dominated"] and not q[1]["robustly_dominated"]  # overlapping CIs, equal latency


def test_settled_from():
    assert P7.settled_from([(64, False), (256, True), (1024, False), (4096, True), (16384, True)]) == 4096
    assert P7.settled_from([(64, True), (256, True)]) == 64
    assert P7.settled_from([(64, True), (256, False)]) is None


def phase7_dir() -> Path:
    cur = ROOT / "results" / "phase7" / ".current_run"
    if not cur.exists():
        pytest.skip("phase 7 not run")
    return ROOT / "results" / "phase7" / cur.read_text(encoding="utf-8").strip()


def test_modelled_cost_linear_in_shots():
    rows = list(csv.DictReader((phase7_dir() / "break_even_modelled_cost.csv").open(encoding="utf-8")))
    assert len(rows) >= 2
    r0 = rows[0]
    for r in rows:
        ratio = float(r["S"]) / float(r0["S"])
        assert float(r["MODELLED_shots_per_query_shortlist"]) == pytest.approx(ratio * float(r0["MODELLED_shots_per_query_shortlist"]))
        assert float(r["MODELLED_2q_gate_exec_full_circuit_shortlist"]) == pytest.approx(ratio * float(r0["MODELLED_2q_gate_exec_full_circuit_shortlist"]))


def test_combined_table_matches_sources():
    d = phase7_dir()
    comb = list(csv.DictReader((d / "combined_table.csv").open(encoding="utf-8")))
    assert {r["N"] for r in comb} == set(P7.NORDER)
    main = list(csv.DictReader((P7.cur("phase4") / "main_table.csv").open(encoding="utf-8")))
    flat = next(r for r in comb if r["N"] == "all" and r["arm"] == "Flat")
    assert float(flat["Hit@3"]) == pytest.approx(float(next(r for r in main if r["N"] == "all" and r["arm"] == "Flat")["Hit@3"]))
    assert not any(r["hallucination_rate_seed0"] for r in comb if r["N"] in ("2000", "10000"))  # no generation at those rungs


def test_pareto_has_front_per_n():
    d = phase7_dir()
    for name in ("pareto_hallucination.csv", "pareto_retrieval_miss.csv"):
        rows = list(csv.DictReader((d / name).open(encoding="utf-8")))
        for n in {r["N"] for r in rows}:
            assert any(r["non_dominated"] == "True" for r in rows if r["N"] == n)
