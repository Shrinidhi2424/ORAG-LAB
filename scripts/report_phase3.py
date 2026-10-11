"""Phase 3 block of FINDINGS.md, generated from results/phase3/<run_id>/ artifacts (used by report.py)."""
from __future__ import annotations

import csv
import json
import statistics
import xml.etree.ElementTree as ET
from pathlib import Path

from report import md_table, rel

ROOT = Path(__file__).resolve().parent.parent
MAIN_S = ("64", "256", "1024", "4096", "16384", "inf")


def nkey(n: str) -> float:
    return float("inf") if n == "all" else float(n)


MKEY = {"20": 0, "50": 1, "100": 2, "full": 3}


def rd(p: Path) -> list[dict]:
    return list(csv.DictReader(p.open(encoding="utf-8")))


def f3(x) -> str:
    return "-" if x in ("", None) else f"{float(x):.3f}"


def msd(r: dict, m: str) -> str:
    return f"{float(r[m]):.3f} ± {float(r[m + '_sd_seeds']):.3f}"


def cis(r: dict, m: str) -> str:
    return f"[{float(r[m + '_lo']):.3f}, {float(r[m + '_hi']):.3f}]"


def phase3_block(run: Path) -> tuple[str, list[list]]:
    idx: list[list] = []
    L = [f"Run `{run.name}` - manifest: `{rel(run / 'run_manifest.json')}`. Quantum-inspired arm = classical SIMULATION of the "
         "SWAP test (Appendix A.1); no speedup is claimed. Tier B latency is emulated-estimator latency, not quantum latency.", ""]

    tt = run / "tierA_timing.json"
    if tt.exists():
        t = json.loads(tt.read_text(encoding="utf-8"))
        L += [f"**Tier A circuit cost on this laptop (3.3, first step)** (`{rel(tt)}`): 19 qubits, S=4096, median per pair "
              f"{t['with_transpile']['per_pair_s_median_excl_first']:.3f} s with transpile, {t['without_transpile']['per_pair_s_median_excl_first']:.3f} s without; "
              f"identical estimates in both modes: {t['identical_estimates_both_modes']}. Tier B chunk (20 queries x {t['tierB_chunk_full_scan']['candidates']} "
              f"candidates, S=1024, incl. ranking): {t['tierB_chunk_full_scan']['seconds']:.3f} s. Decision: {t['decision']}.", ""]

    vj = run / "validation.json"
    if vj.exists():
        v = json.loads(vj.read_text(encoding="utf-8"))
        a, b = v["tierA"], v["tierB"]
        L += [f"**Validation (3.3a/b)** (`{rel(vj)}`, per-pair `{rel(run / 'validation_pairs.csv')}`): {v['n_pairs']} pairs "
              f"({v['pair_types']['random_corpus_pair']} random corpus pairs + {v['pair_types']['query_top50_pair']} query-to-exact-top-50 pairs; "
              f"cos range {v['cos_range'][0]:.3f} to {v['cos_range'][1]:.3f}), S = {v['shots']}, unclipped estimates. "
              f"Theory RMSE = {v['theory_rmse']:.4f}.", "",
              md_table(["Tier", "Bias", "MAE", "RMSE", "z sd (theory 1)", "|z|<=2", "|z|<=3", "KS vs N(0,1) p"],
                       [[n, f"{s['bias']:+.5f}", f"{s['mae']:.4f}", f"{s['rmse']:.4f}", f"{s['z_sd']:.3f}", f"{s['frac_abs_z_le_2']:.3f}",
                         f"{s['frac_abs_z_le_3']:.3f}", f"{s['ks_vs_normal_p']:.3f}"] for n, s in (("A (Aer circuit)", a), ("B (emulator)", b))]), "",
              f"Two-sample KS on standardised errors, Tier A vs Tier B: D = {v['ks_two_sample_z_tierA_vs_tierB']['stat']:.3f}, p = {v['ks_two_sample_z_tierA_vs_tierB']['p']:.3f}.", ""]
        r = v["repeated"]
        L += [f"Repeated estimates ({r['pairs']} pairs x {r['repeats']} repeats per tier, S={r['shots']}; `{rel(run / 'validation_repeated.npz')}`): "
              f"mean |difference of pair means| = {r['mean_abs_diff_of_pair_means']:.4f} (expected under equivalence ~{r['mean_abs_diff_of_pair_means_expected_sd']:.4f} sd); "
              f"variance ratio A/B median {r['var_ratio_A_over_B_median']:.3f} (IQR {r['var_ratio_A_over_B_iqr'][0]:.3f}-{r['var_ratio_A_over_B_iqr'][1]:.3f}); "
              f"variance / theory: A {r['tierA_var_over_theory_mean']:.3f}, B {r['tierB_var_over_theory_mean']:.3f}; "
              f"pooled two-sample KS D = {r['ks_two_sample_pooled_z']['stat']:.3f}, p = {r['ks_two_sample_pooled_z']['p']:.3f}.", ""]
        sa, sb = v["loglog_slope_tierA"], v["loglog_slope_tierB"]
        L += [f"**F2 error vs shots (3.3c)**: ![F2](results/figures/F2_error_vs_shots.png) (data `results/figures/F2_error_vs_shots.csv`, source `{rel(run / 'f2_error_vs_shots.csv')}`). "
              f"Log-log slope of RMSE vs S: Tier B {sb['slope']:.3f} (95% CI {sb['ci95'][0]:.3f} to {sb['ci95'][1]:.3f}); "
              f"Tier A {sa['slope']:.3f} (95% CI {sa['ci95'][0]:.3f} to {sa['ci95'][1]:.3f}); theory -0.5.", ""]
        idx.append(["P3-1", 3, f"Tier A vs Tier B KS p = {v['ks_two_sample_z_tierA_vs_tierB']['p']:.3f}; RMSE slope B {sb['slope']:.3f}, A {sa['slope']:.3f} (theory -0.5)", rel(vj)])

    na = run / "negative_cosine_audit.json"
    if na.exists():
        n = json.loads(na.read_text(encoding="utf-8"))
        L += [f"**Negative-cosine audit (3.3d)** (`{rel(na)}`)", "", md_table(
            ["N", "cos<0 in exact top-10", "cos<0 in exact top-100", "Queries whose noise-free cos² full-scan top-10 differs from cos top-10", "Min cos in corpus"],
            [[k, x["negative_cos_in_exact_top10"], x["negative_cos_in_exact_top100"],
              x["queries_where_noisefree_cos2_full_scan_top10_differs_from_cos_top10"], f"{x['min_cos_in_full_corpus']:.3f}"] for k, x in n.items()]), "",
              "The last-but-one column measures the sign loss of cos² (D1) in the full-scan protocol: strongly negative items square above weakly "
              "positive top-10 items. Shortlist protocols (M <= 100) contain no negative cosines, so they are unaffected.", ""]

    rm = run / "retrieval_metrics.csv"
    if rm.exists():
        rows = rd(rm)

        def get(n, m, tie, s):
            return next((r for r in rows if (r["N"], r["M"], r["tie"], r["shots"]) == (n, m, tie, s)), None)

        ns = sorted(dict.fromkeys(r["N"] for r in rows), key=nkey)
        L += [f"**Quantum-sim retrieval, two-stage (M=50 shortlist from Flat, Tier B re-score, ties by classical score), 300 queries, 5 seeds** "
              f"(`{rel(rm)}`; rankings `{rel(run / 'rankings')}/`). Values: mean ± sd across seeds; [95% bootstrap CI over queries, seed-averaged]; "
              "diff = quantum - classical Hit@3 (paired bootstrap CI).", ""]
        body = []
        for n_ in ns:
            cl = get(n_, "50", "classical", "classical")
            body.append([n_, "classical", f"{float(cl['Hit@3']):.3f}", cis(cl, "Hit@3"), f"{float(cl['MRR@10']):.3f}", "1", "1", "0", "1", "-"])
            for s in MAIN_S:
                r = get(n_, "50", "classical", s)
                if r:
                    body.append([n_, s, msd(r, "Hit@3"), cis(r, "Hit@3"), msd(r, "MRR@10"), f3(r["Overlap@10"]), f3(r["RBO"]),
                                 f3(r["Top1Changed"]), f3(r.get("KendallTau", "")), f"{float(r['diff_Hit@3']):+.3f} [{float(r['diff_Hit@3_lo']):+.3f}, {float(r['diff_Hit@3_hi']):+.3f}]"])
        L += [md_table(["N", "Shots S", "Hit@3", "Hit@3 CI", "MRR@10", "Overlap@10", "RBO", "Top-1 changed", "Kendall tau (M items)", "diff Hit@3 [CI]"], body), ""]
        fs = []
        for n_ in ns:
            for s in MAIN_S:
                r = get(n_, "full", "classical", s)
                if r:
                    fs.append([n_, s, msd(r, "Hit@3"), msd(r, "MRR@10"), f3(r["Overlap@10"]), f3(r["Top1Changed"]),
                               f"{float(r['diff_Hit@3']):+.3f} [{float(r['diff_Hit@3_lo']):+.3f}, {float(r['diff_Hit@3_hi']):+.3f}]"])
        L += ["**Full-scan ablation (all N candidates estimated, Tier B)**", "",
              md_table(["N", "Shots S", "Hit@3", "MRR@10", "Overlap@10", "Top-1 changed", "diff Hit@3 [CI]"], fs), ""]
        tb = []
        for n_ in ns:
            for s in ("64", "128", "256", "1024"):
                c, rr = get(n_, "50", "classical", s), get(n_, "50", "random", s)
                if c and rr:
                    tb.append([n_, s, msd(c, "Hit@3"), msd(rr, "Hit@3"), msd(c, "Hit@1"), msd(rr, "Hit@1")])
        L += ["**Tie-breaking effect at low S (M=50) [P1]**: default breaks equal estimates by the classical score (a design choice that "
              "injects exact information into ties); 'random' breaks them uniformly at random.", "",
              md_table(["N", "Shots S", "Hit@3 ties=classical", "Hit@3 ties=random", "Hit@1 ties=classical", "Hit@1 ties=random"], tb), ""]
        cl_all, q_all = get(ns[-1], "50", "classical", "classical"), get(ns[-1], "50", "classical", "64")
        idx.append(["P3-2", 3, f"N={ns[-1]}, M=50: Hit@3 classical {float(cl_all['Hit@3']):.3f} vs quantum-sim S=64 {float(q_all['Hit@3']):.3f}", rel(rm)])

    th = run / "shot_thresholds.csv"
    if th.exists():
        t = rd(th)
        L += [f"**Shot threshold (exit gate)** (`{rel(th)}`): smallest S such that for that S and every larger S in the grid the paired 95% CI "
              "of (quantum - classical) contains 0 ('indistinguishable'), and the plainer rule 'quantum mean inside the classical 95% CI'.", "",
              md_table(["N", "M", "Ties", "Hit@3: indistinguishable", "Hit@3: within classical CI", "MRR@10: indistinguishable", "MRR@10: within CI", "Hit@1: indistinguishable"],
                       [[r["N"], r["M"], r["tie"], r["min_shots_Hit@3_indistinguishable"], r["min_shots_Hit@3_within_classical_CI"],
                         r["min_shots_MRR@10_indistinguishable"], r["min_shots_MRR@10_within_classical_CI"], r["min_shots_Hit@1_indistinguishable"]]
                        for r in sorted(t, key=lambda r: (nkey(r["N"]), MKEY.get(r["M"], 9), r["tie"]))]), ""]
        m50 = sorted((r for r in t if r["M"] == "50" and r["tie"] == "classical"), key=lambda r: nkey(r["N"]))
        idx.append(["P3-3", 3, "Hit@3 shot threshold (M=50) per N: " + ", ".join(f"{r['N']}: {r['min_shots_Hit@3_indistinguishable']}" for r in m50), rel(th)])

    tm = run / "tierB_run_timing.csv"
    if tm.exists():
        t = rd(tm)
        agg = {}
        for r in t:
            if r["tie"] == "classical" and r["shots"] != "0" and r["mode"] in ("50", "full"):
                agg.setdefault((r["N"], r["mode"]), []).append(float(r["seconds"]))
        L += [f"Tier B run cost (H8; `{rel(tm)}`): median seconds per (N, M, S, seed) run over all 300 queries, incl. ranking and metrics - " +
              ", ".join(f"N={n_} M={m}: {statistics.median(v):.3f} s" for (n_, m), v in agg.items()) + ". (Proper latency per query is Phase 4.)", ""]

    te = run / "tierA_e2e_summary.json"
    if te.exists():
        e = json.loads(te.read_text(encoding="utf-8"))
        L += [f"**Tier A end-to-end subset (3.5) [P1]** (`{rel(te)}`, `{rel(run / 'tierA_e2e.csv')}`): {e['queries']} queries x M={e['M']} "
              f"(exact top-{e['M']} at N={e['N']}) x S={e['shots']}: {e['circuits']} real Aer circuits in {e['total_seconds']:.1f} s "
              f"({e['seconds_per_circuit']:.3f} s per circuit; classical simulation cost grows as 2^qubits).", "",
              md_table(["Ranking", "Hit@1", "Hit@3", "Top-1 changed vs classical", "Overlap@3 vs classical"],
                       [[k, f"{e[k]['Hit@1']:.3f}", f"{e[k]['Hit@3']:.3f}", f"{e[k]['top1_changed_frac']:.3f}", f"{e[k]['overlap@3_mean']:.3f}"]
                        for k in ("A", "B", "classical")]), "", "With 20 queries these rates are illustrative only (no CI claimed).", ""]
        idx.append(["P3-4", 3, f"Tier A end-to-end: {e['circuits']} circuits, {e['seconds_per_circuit']:.3f} s/circuit", rel(te)])

    t6 = run / "t6_resource_counts.json"
    if t6.exists():
        r = json.loads(t6.read_text(encoding="utf-8"))
        L += [f"**T6 resource counts (MODELLED, not executed)** (`{rel(t6)}`; basis {r['basis']}, optimisation level {r['optimization_level']}, "
              f"transpile took {r['transpile_seconds']:.1f} s)", "",
              md_table(["Circuit", "Qubits", "Depth", "2-qubit gates", "1-qubit gates"],
                       [[k, r[k]["qubits"], r[k]["depth"], r[k]["two_qubit_gates"], r[k]["one_qubit_gates"]] for k in ("swap_test_core", "full_with_state_prep")]), "",
              f"Statevector memory for the 19-qubit simulation: {r['statevector_bytes_complex128']} bytes (complex128). State preparation dominates the "
              "gate count; without QRAM-like loading there is no asymptotic advantage (Appendix A.3).", ""]
        idx.append(["P3-5", 3, f"T6: full circuit depth {r['full_with_state_prep']['depth']}, {r['full_with_state_prep']['two_qubit_gates']} two-qubit gates", rel(t6)])

    L += ["**Not done in Phase 3**: 3.6 Zardini-style estimator [P1] deferred until all P0 phases are complete (plan Section 0 priority rule); see Deviations.", ""]
    xml = run / "pytest_junit.xml"
    if xml.exists():
        r = ET.parse(xml).getroot()
        ts = r if r.tag == "testsuite" else r.find("testsuite")
        tot, fail, err, skip = (int(ts.get(x, 0)) for x in ("tests", "failures", "errors", "skipped"))
        L += [f"**pytest** (whole suite at Phase 3 exit): {tot} tests, {fail} failures, {err} errors, {skip} skipped (`{rel(xml)}`).", ""]
        idx.append(["P3-6", 3, f"pytest: {tot - fail - err - skip}/{tot} passed", rel(xml)])
    L += ["**Manuscript hook**: Section 6 (estimator validation, F2, shot budget), Table T6; Section 2 (SWAP test).", ""]
    return "\n".join(L), idx
