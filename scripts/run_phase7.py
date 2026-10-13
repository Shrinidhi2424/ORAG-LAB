"""Phase 7: scalability and tradeoff synthesis (Pareto, break-even, sensitivity). Analysis only, no new measurements.

Usage: python scripts/run_phase7.py --run-id <id>
Outputs: results/phase7/<run_id>/ (R3). Consumes Phase 2-6 artifacts. Nothing is re-measured: every number is a
re-aggregation of a raw artifact from an earlier phase. Latency of the quantum-sim arm is EMULATED-estimator latency;
shots / circuits / gate executions are MODELLED costs, not wall-clock quantum time (Appendix A.3).
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from qrag.manifest import write_run_manifest  # noqa: E402

NORDER = ["1000", "2000", "5000", "10000", "all"]
HALL_N = ["1000", "5000", "all"]  # rungs with generation runs (Phase 5)
HALL_S = [64, 256, 1024, 4096]
MISS_S = [256, 1024, 4096, 16384]  # shots with both a Phase 4 main-table row and a Phase 4 latency row
M_MAIN = "50"
MARGINS = (0.05, 0.075, 0.10)  # equivalence margins (absolute, in rate units) for the break-even analysis
BASE_KEY = "classical"


def cur(phase: str) -> Path:
    return ROOT / "results" / phase / (ROOT / "results" / phase / ".current_run").read_text(encoding="utf-8").strip()


def rd(p: Path) -> list[dict]:
    return list(csv.DictReader(p.open(encoding="utf-8")))


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(dict.fromkeys(k for r in rows for k in r)))
        w.writeheader()
        w.writerows(rows)


def jdump(path: Path, obj) -> None:
    path.write_text(json.dumps(obj, indent=2), encoding="utf-8")


def fl(x, default=None):
    return default if x in ("", None) else float(x)


# ---------------------------------------------------------------------------------------------------------------------
# Pareto helpers (both objectives minimised)
# ---------------------------------------------------------------------------------------------------------------------
def dominates(a: dict, b: dict, xk: str, yk: str) -> bool:
    return a[xk] <= b[xk] and a[yk] <= b[yk] and (a[xk] < b[xk] or a[yk] < b[yk])


def robustly_dominates(a: dict, b: dict, xk: str, yk: str, xlo: str, xhi: str, ylo: str, yhi: str) -> bool:
    """Conservative: a dominates b by point estimate AND on at least one objective where a is strictly better the
    uncertainty intervals (hallucination / miss: 95% bootstrap CI; latency: range of the 5 repeat medians) are disjoint."""
    if not dominates(a, b, xk, yk):
        return False
    return any(a[k] < b[k] and a[hi] < b[lo] for k, lo, hi in ((xk, xlo, xhi), (yk, ylo, yhi)))


def front(points: list[dict], xk: str, yk: str, **iv) -> None:
    for p in points:
        p["dominated"] = any(dominates(q, p, xk, yk) for q in points if q is not p)
        p["robustly_dominated"] = any(robustly_dominates(q, p, xk, yk, **iv) for q in points if q is not p)
        p["non_dominated"] = not p["dominated"]


def pareto_hallucination(p4: Path, p5: Path) -> list[dict]:
    """(hallucination rate, retrieval latency) per (arm, S, N). Latency: Phase 4 in-process, k=10, embedding excluded."""
    lat = rd(p4 / "latency_summary.csv")
    out = rd(p5 / "outcomes_by_arm.csv")
    pts = []
    for n in HALL_N:
        fl_ = next(r for r in lat if r["arm"] == "flat" and r["N"] == n)
        cl = next(r for r in out if r["kind"] == "classical" and r["N"] == n)
        pts.append(point("classical", "Flat", n, "", cl, fl_))
        for s in HALL_S:
            q = next((r for r in out if r["kind"] == "quantum" and r["N"] == n and r["S"] == str(s) and r["seed"] == "0"), None)
            ql = next(r for r in lat if r["arm"] == "qsim" and r["N"] == n and r["M"] == M_MAIN and float(r["S"]) == s)
            pts.append(point("quantum", "Quantum-sim", n, s, q, ql))
    for n in HALL_N:
        front([p for p in pts if p["N"] == n], "latency_ms", "hallucination_rate",
              xlo="latency_lo_ms", xhi="latency_hi_ms", ylo="hall_lo", yhi="hall_hi")
    return pts


def point(kind: str, arm: str, n: str, s, o: dict, lat: dict) -> dict:
    return {"kind": kind, "arm": arm, "N": n, "S": s, "latency_ms": float(lat["median_ms"]), "latency_p95_ms": float(lat["p95_ms"]),
            "latency_lo_ms": float(lat["repeat_median_min_ms"]), "latency_hi_ms": float(lat["repeat_median_max_ms"]),
            "hallucination_rate": float(o["hallucination_rate"]), "hall_lo": float(o["hall_lo"]), "hall_hi": float(o["hall_hi"]),
            "correct_rate": float(o["correct_rate"]), "abstention_rate": float(o["abstention_rate"]),
            "gold_in_context_rate": float(o["gold_in_context_rate"]), "n_questions": int(o["n"])}


def pareto_miss(p2: Path, p4: Path) -> list[dict]:
    """(retrieval miss rate = 1 - Hit@3, retrieval latency) per (arm, S, N), IVF included. Hit@3 from the Phase 4 main table (300 queries)."""
    main, lat = rd(p4 / "main_table.csv"), rd(p4 / "latency_summary.csv")
    pts = []
    for n in NORDER:
        for arm, want in (("Flat", "flat"), ("IVF", "ivf")):
            m = next(r for r in main if r["N"] == n and r["arm"].startswith(arm))
            pts.append(miss_point(arm, "classical", n, "", m, next(r for r in lat if r["arm"] == want and r["N"] == n)))
        for s in MISS_S:
            m = next(r for r in main if r["N"] == n and r["arm"] == "Quantum-sim" and r["S"] == str(s))
            pts.append(miss_point("Quantum-sim", "quantum", n, s, m, next(r for r in lat if r["arm"] == "qsim" and r["N"] == n and r["M"] == M_MAIN and float(r["S"]) == s)))
    for n in NORDER:
        front([p for p in pts if p["N"] == n], "latency_ms", "miss_rate", xlo="latency_lo_ms", xhi="latency_hi_ms", ylo="miss_lo", yhi="miss_hi")
    return pts


def miss_point(arm: str, kind: str, n: str, s, m: dict, lat: dict) -> dict:
    return {"kind": kind, "arm": arm, "N": n, "S": s, "latency_ms": float(lat["median_ms"]), "latency_p95_ms": float(lat["p95_ms"]),
            "latency_lo_ms": float(lat["repeat_median_min_ms"]), "latency_hi_ms": float(lat["repeat_median_max_ms"]),
            "hit3": float(m["Hit@3"]), "miss_rate": 1 - float(m["Hit@3"]), "miss_lo": 1 - float(m["Hit@3_hi"]), "miss_hi": 1 - float(m["Hit@3_lo"]),
            "mrr10": float(m["MRR@10"])}


# ---------------------------------------------------------------------------------------------------------------------
# Combined table (7.1)
# ---------------------------------------------------------------------------------------------------------------------
def combined(p2: Path, p3: Path, p4: Path, p5: Path, p6: Path) -> list[dict]:
    main, lat = rd(p4 / "main_table.csv"), rd(p4 / "latency_summary.csv")
    mem = {r["N"]: r for r in rd(p4 / "memory_vs_N.csv")}
    out5 = rd(p5 / "outcomes_by_arm.csv")
    http = {(r["profile"], r["arm"], r["N"]): r for r in rd(p6 / "latency_summary.csv")}
    rows = []
    for n in NORDER:
        for m in (r for r in main if r["N"] == n):
            arm = m["arm"]
            s = m["S"]
            if arm == "Flat":
                lr, kind, mem_b, http_arm = next(r for r in lat if r["arm"] == "flat" and r["N"] == n), "classical", mem[n]["flat_index_bytes"], "classical"
                o = next((r for r in out5 if r["kind"] == "classical" and r["N"] == n), None)
            elif arm.startswith("IVF"):
                lr, kind, mem_b, http_arm, o = next(r for r in lat if r["arm"] == "ivf" and r["N"] == n), "classical", mem[n]["ivf_index_bytes"], None, None
            else:
                lr = next(r for r in lat if r["arm"] == "qsim" and r["N"] == n and r["M"] == M_MAIN and float(r["S"]) == float(s))
                kind, mem_b, http_arm = "quantum", mem[n]["qsim_shortlist_index_bytes"], ("quantum" if float(s) == 1024 else None)
                o = next((r for r in out5 if r["kind"] == "quantum" and r["N"] == n and r["S"] == s and r["seed"] == "0"), None)
            h = http.get(("medium", http_arm, n)) if http_arm else None
            rows.append({"N": n, "arm": arm, "S": s, "M": M_MAIN if kind == "quantum" else "",
                         "Hit@3": m["Hit@3"], "Hit@3_lo": m["Hit@3_lo"], "Hit@3_hi": m["Hit@3_hi"], "MRR@10": m["MRR@10"], "Overlap@10": m["Overlap@10"],
                         "retrieval_latency_median_ms": lr["median_ms"], "retrieval_latency_p95_ms": lr["p95_ms"],
                         "index_bytes": mem_b,
                         "http_e2e_median_ms_medium": h["e2e_median_ms"] if h else "",
                         "hallucination_rate_seed0": o["hallucination_rate"] if o else "", "hall_lo": o["hall_lo"] if o else "", "hall_hi": o["hall_hi"] if o else "",
                         "correct_rate_seed0": o["correct_rate"] if o else ""})
    return rows


# ---------------------------------------------------------------------------------------------------------------------
# Break-even (7.3)
# ---------------------------------------------------------------------------------------------------------------------
def settled_from(items: list[tuple[float, bool]]) -> float | None:
    """Smallest S such that the predicate holds at S and at every larger S in the grid; None if it fails at the largest."""
    items = sorted(items)
    best = None
    for s, ok in reversed(items):
        if ok:
            best = s
        else:
            break
    return best


def break_even(p3: Path, p4: Path, p5: Path) -> tuple[list[dict], list[dict]]:
    # (a) outcome level: hallucination (Phase 5, exact McNemar, seed 0, n=200); N where generation was run
    pt = [r for r in rd(p5 / "paired_tests.csv") if r["metric"] == "hallucinated_or_misread" and r["seed"] == "0"]
    rows_h = []
    for n in HALL_N:
        sel = [r for r in pt if r["N"] == n]
        grid = sorted(float(r["S"]) for r in sel)
        row = {"level": "hallucination (Phase 5, n=200)", "N": n, "grid": ";".join(str(int(s)) for s in grid)}
        ns = settled_from([(float(r["S"]), float(r["p_mcnemar"]) >= 0.05) for r in sel])
        row["min_S_McNemar_p_ge_0.05_and_all_larger"] = "" if ns is None else int(ns)
        for d in MARGINS:
            eq = settled_from([(float(r["S"]), float(r["diff_lo"]) > -d and float(r["diff_hi"]) < d) for r in sel])
            row[f"min_S_CI_within_pm{d}"] = "" if eq is None else int(eq)
        for r in sel:
            row[f"diff_S{int(float(r['S']))}"] = f"{float(r['diff']):+.3f} [{float(r['diff_lo']):+.3f}, {float(r['diff_hi']):+.3f}] p={float(r['p_mcnemar']):.3f}"
        rows_h.append(row)
    # (b) retrieval level: Hit@3 and MRR@10 vs classical (Phase 3: M=50, tie=classical, 300 queries, S grid 64..16384)
    rm = [r for r in rd(p3 / "retrieval_metrics.csv") if r["M"] == M_MAIN and r["tie"] == "classical" and r["shots"] not in ("classical", "inf")]
    rows_r = []
    for metric in ("Hit@3", "MRR@10"):
        for n in NORDER:
            sel = [r for r in rm if r["N"] == n]
            row = {"level": f"retrieval {metric} (Phase 3, n=300)", "N": n, "grid": ";".join(str(int(s)) for s in sorted(float(r["shots"]) for r in sel))}
            ci_zero = settled_from([(float(r["shots"]), float(r[f"diff_{metric}_lo"]) <= 0 <= float(r[f"diff_{metric}_hi"])) for r in sel])
            row["min_S_CI_contains_0_and_all_larger"] = "" if ci_zero is None else int(ci_zero)
            for d in MARGINS:
                eq = settled_from([(float(r["shots"]), float(r[f"diff_{metric}_lo"]) > -d and float(r[f"diff_{metric}_hi"]) < d) for r in sel])
                row[f"min_S_CI_within_pm{d}"] = "" if eq is None else int(eq)
            rows_r.append(row)
    return rows_h, rows_r


def modelled_cost_at(p3: Path, p4: Path, s: int, n_all: int) -> dict:
    """MODELLED cost at shots s. Per-shot 2q-gate executions are read from the Phase 4 modelled-cost artifact (constant per shot)."""
    mc = rd(p4 / "modelled_quantum_cost.csv")
    ref = next(r for r in mc if r["M"] == M_MAIN and r["S"] == "1024")
    shots_ref = float(ref["MODELLED_total_shots_per_query"])
    per_shot_full = float(ref["MODELLED_2q_gate_executions_per_query_full_circuit"]) / shots_ref
    per_shot_core = float(ref["MODELLED_2q_gate_executions_per_query_swap_core_only"]) / shots_ref
    m = int(M_MAIN)
    return {"S": s, "MODELLED_circuits_per_query_shortlist": m, "MODELLED_shots_per_query_shortlist": m * s,
            "MODELLED_2q_gate_exec_full_circuit_shortlist": per_shot_full * m * s, "MODELLED_2q_gate_exec_swap_core_shortlist": per_shot_core * m * s,
            "MODELLED_circuits_per_query_full_scan_N_all": n_all, "MODELLED_shots_per_query_full_scan_N_all": n_all * s,
            "MODELLED_2q_gate_exec_full_circuit_full_scan_N_all": per_shot_full * n_all * s}


# ---------------------------------------------------------------------------------------------------------------------
# Sensitivity (7.4): shortlist M and tie-breaking; PCA-128 is [P2] and not run
# ---------------------------------------------------------------------------------------------------------------------
def sensitivity(p3: Path) -> tuple[list[dict], list[dict]]:
    rm = rd(p3 / "retrieval_metrics.csv")
    sel_s = ("256", "1024", "4096")
    m_rows = []
    for n in NORDER:
        for s in sel_s:
            vals = {}
            for mm in ("20", "50", "100", "full"):
                r = next((x for x in rm if x["M"] == mm and x["N"] == n and x["shots"] == s and x["tie"] == "classical"), None)
                if r:
                    vals[mm] = (float(r["Hit@3"]), float(r["Hit@3_sd_seeds"]), float(r["MRR@10"]))
            hs = [v[0] for v in vals.values()]
            m_rows.append({"N": n, "S": int(s), **{f"Hit@3_M{k}": f"{v[0]:.3f}" for k, v in vals.items()},
                           **{f"sd_seeds_M{k}": f"{v[1]:.3f}" for k, v in vals.items()},
                           "range_across_M": max(hs) - min(hs), "max_sd_seeds": max(v[1] for v in vals.values())})
    t_rows = []
    for n in NORDER:
        for s in ("64", "256", "1024", "4096", "16384"):
            c = next((x for x in rm if x["M"] == M_MAIN and x["N"] == n and x["shots"] == s and x["tie"] == "classical"), None)
            r = next((x for x in rm if x["M"] == M_MAIN and x["N"] == n and x["shots"] == s and x["tie"] == "random"), None)
            if c and r:
                t_rows.append({"N": n, "S": int(s), "Hit@3_tie_classical": float(c["Hit@3"]), "Hit@3_tie_random": float(r["Hit@3"]),
                               "diff_random_minus_classical": float(r["Hit@3"]) - float(c["Hit@3"]),
                               "sd_seeds_classical": float(c["Hit@3_sd_seeds"]), "sd_seeds_random": float(r["Hit@3_sd_seeds"]),
                               "MRR@10_tie_classical": float(c["MRR@10"]), "MRR@10_tie_random": float(r["MRR@10"])})
    return m_rows, t_rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", required=True)
    a = ap.parse_args()
    out = ROOT / "results" / "phase7" / a.run_id
    out.mkdir(parents=True, exist_ok=True)
    p2, p3, p4, p5, p6 = (cur(f"phase{i}") for i in (2, 3, 4, 5, 6))
    sources = {f"phase{i}": d.name for i, d in zip((2, 3, 4, 5, 6), (p2, p3, p4, p5, p6))}

    comb = combined(p2, p3, p4, p5, p6)
    write_csv(out / "combined_table.csv", comb)

    ph = pareto_hallucination(p4, p5)
    write_csv(out / "pareto_hallucination.csv", ph)
    pm = pareto_miss(p2, p4)
    write_csv(out / "pareto_retrieval_miss.csv", pm)

    be_h, be_r = break_even(p3, p4, p5)
    write_csv(out / "break_even_hallucination.csv", be_h)
    write_csv(out / "break_even_retrieval.csv", be_r)

    n_all = int(json.loads(next((cur("phase1")).glob("corpus_stats.json")).read_text(encoding="utf-8"))["unique_paragraphs"])
    sset = sorted({int(r[f"min_S_CI_within_pm{d}"]) for r in be_h + be_r for d in MARGINS if r.get(f"min_S_CI_within_pm{d}") not in ("", None)}
                  | {int(r["min_S_McNemar_p_ge_0.05_and_all_larger"]) for r in be_h if r["min_S_McNemar_p_ge_0.05_and_all_larger"] != ""}
                  | {int(r["min_S_CI_contains_0_and_all_larger"]) for r in be_r if r["min_S_CI_contains_0_and_all_larger"] != ""})
    cost = [modelled_cost_at(p3, p4, s, n_all) for s in sset]
    write_csv(out / "break_even_modelled_cost.csv", cost)
    tA = json.loads((p3 / "tierA_e2e_summary.json").read_text(encoding="utf-8"))

    m_rows, t_rows = sensitivity(p3)
    write_csv(out / "sensitivity_shortlist_M.csv", m_rows)
    write_csv(out / "sensitivity_tie_breaking.csv", t_rows)

    jdump(out / "synthesis_meta.json", {
        "sources": sources, "equivalence_margins_abs": list(MARGINS), "m_main": int(M_MAIN), "n_all": n_all,
        "pareto_objectives": {"hallucination": ["retrieval latency median ms (Phase 4, in-process, k=10, embedding excluded)", "hallucination rate (Phase 5, seed 0, n=200)"],
                              "retrieval_miss": ["retrieval latency median ms (Phase 4)", "1 - Hit@3 (Phase 4 main table, 300 queries)"]},
        "tierA_measured_seconds_per_circuit_S1024": tA["seconds_per_circuit"], "tierA_note": "measured classical simulation of the 19-qubit circuit (Aer), not quantum time",
        "pca128_sensitivity": "not run ([P2])"})
    write_run_manifest(out, "phase7", a.run_id, seeds={"analysis": "deterministic re-aggregation; no randomness"},
                       config={"sources": sources, "margins": list(MARGINS), "m_main": int(M_MAIN), "n_all": n_all})
    print("phase7 artifacts in", out)


if __name__ == "__main__":
    main()
