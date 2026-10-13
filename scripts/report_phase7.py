"""Phase 7 block of FINDINGS.md, generated from results/phase7/<run_id>/ artifacts (used by report.py)."""
from __future__ import annotations

import csv
import json
import xml.etree.ElementTree as ET
from pathlib import Path

from report import md_table, rel

NLAB = {"1000": "1000", "2000": "2000", "5000": "5000", "10000": "10000", "all": "all (20958)"}


def rd(p: Path) -> list[dict]:
    return list(csv.DictReader(p.open(encoding="utf-8")))


def f(x, d=3) -> str:
    return "-" if x in ("", None) else f"{float(x):.{d}f}"


def tf(x) -> str:
    return "yes" if x in (True, "True") else "no"


def sv(x) -> str:
    return "not reached" if x in ("", None, "nan") else str(int(float(x)))


def arm_s(r: dict) -> str:
    return r["arm"] + (f" S={int(float(r['S']))}" if r["S"] not in ("", None) else "")


def phase7_block(run: Path) -> tuple[str, list[list]]:
    idx: list[list] = []
    meta = json.loads((run / "synthesis_meta.json").read_text(encoding="utf-8"))
    src = ", ".join(f"{k} `{v}`" for k, v in meta["sources"].items())
    L = [f"Run `{run.name}` - manifest: `{rel(run / 'run_manifest.json')}`. Analysis only: every number below re-aggregates raw artifacts of earlier phases ({src}); nothing was re-measured. "
         "Quantum-sim latency is EMULATED-estimator latency. Shots, circuits and gate executions are MODELLED costs, not wall-clock quantum time; no speedup is claimed.", ""]

    comb = rd(run / "combined_table.csv")
    body = []
    for r in comb:
        h = "-" if not r["hallucination_rate_seed0"] else f"{f(r['hallucination_rate_seed0'])} [{f(r['hall_lo'])}, {f(r['hall_hi'])}]"
        body.append([NLAB[r["N"]], arm_s(r), f"{f(r['Hit@3'])} [{f(r['Hit@3_lo'])}, {f(r['Hit@3_hi'])}]", f(r["MRR@10"]),
                     f(r["retrieval_latency_median_ms"]), f(r["retrieval_latency_p95_ms"]), r["index_bytes"], f(r["http_e2e_median_ms_medium"], 1), h])
    L += [f"**T7a Combined quality / latency / memory / hallucination per arm and N (7.1)** (`{rel(run / 'combined_table.csv')}`). Hit@3 and MRR@10: Phase 4 main table (300 queries; quantum = mean of 5 seeds, M=50). "
          "Retrieval latency: Phase 4 in-process, k=10, embedding excluded. Index bytes: Phase 4 memory table. HTTP E2E: Phase 6 in-network, medium profile, embedding included, measured only for S=1024. "
          "Hallucination rate: Phase 5 seed 0, 200 questions, only at N = 1000 / 5000 / all and S in {64, 256, 1024, 4096}.", "",
          md_table(["N", "Arm", "Hit@3 [95% CI]", "MRR@10", "Retrieval median ms", "p95 ms", "Index bytes", "HTTP E2E median ms (medium)", "Hallucination rate [95% CI]"], body), ""]

    ph = rd(run / "pareto_hallucination.csv")
    body = [[NLAB[r["N"]], arm_s(r), f(r["latency_ms"]), f"{f(r['latency_lo_ms'])}-{f(r['latency_hi_ms'])}",
             f"{f(r['hallucination_rate'])} [{f(r['hall_lo'])}, {f(r['hall_hi'])}]", tf(r["non_dominated"]), tf(r["robustly_dominated"])] for r in ph]
    nd = sum(1 for r in ph if r["non_dominated"] == "True")
    rob = sum(1 for r in ph if r["robustly_dominated"] == "True")
    L += [f"**T7b Pareto set: hallucination rate vs retrieval latency, per N (7.2)** (`{rel(run / 'pareto_hallucination.csv')}`). Both objectives minimised; dominance is evaluated within each N (corpus size is a condition, not an objective). "
          "'Non-dominated' uses point estimates only. 'Robustly dominated' additionally requires, on at least one objective where the dominator is strictly better, disjoint uncertainty intervals "
          "(hallucination: 95% bootstrap CI over the 200 questions; latency: range of the 5 repeat medians). Hallucination is a seed-0 run; latency comes from a separate run (D-4.1), so tiny latency differences between arms are within run-to-run noise.", "",
          md_table(["N", "Arm", "Retrieval median ms", "Range of repeat medians", "Hallucination rate [95% CI]", "Non-dominated", "Robustly dominated"], body), "",
          f"{nd} of {len(ph)} points are non-dominated by point estimate; {rob} are robustly dominated.", ""]
    idx.append(["P7-1", 7, f"Pareto (hallucination vs latency): {nd}/{len(ph)} points non-dominated, {rob} robustly dominated (per-N fronts)", rel(run / "pareto_hallucination.csv")])

    pm = rd(run / "pareto_retrieval_miss.csv")
    body = [[NLAB[r["N"]], arm_s(r), f(r["latency_ms"]), f"{f(r['latency_lo_ms'])}-{f(r['latency_hi_ms'])}",
             f"{f(r['miss_rate'])} [{f(r['miss_lo'])}, {f(r['miss_hi'])}]", tf(r["non_dominated"]), tf(r["robustly_dominated"])] for r in pm]
    ndm = sum(1 for r in pm if r["non_dominated"] == "True")
    robm = sum(1 for r in pm if r["robustly_dominated"] == "True")
    L += [f"**T7c Pareto set: retrieval miss rate (1 - Hit@3) vs retrieval latency, IVF included** (`{rel(run / 'pareto_retrieval_miss.csv')}`), all five rungs, 300 queries, same dominance rules. {ndm} of {len(pm)} points non-dominated; {robm} robustly dominated.", "",
          md_table(["N", "Arm", "Retrieval median ms", "Range of repeat medians", "Miss rate [95% CI]", "Non-dominated", "Robustly dominated"], body), "",
          "**F7 Pareto (hallucination vs latency)**: ![F7](results/figures/F7_pareto_hallucination.png) (data `results/figures/F7_pareto_hallucination.csv`).",
          "**F7b Pareto (retrieval miss vs latency, IVF included)**: ![F7b](results/figures/F7b_pareto_retrieval_miss.png) (data `results/figures/F7b_pareto_retrieval_miss.csv`).", ""]
    idx.append(["P7-2", 7, f"Pareto (retrieval miss vs latency, IVF incl.): {ndm}/{len(pm)} non-dominated, {robm} robustly dominated", rel(run / "pareto_retrieval_miss.csv")])

    bh, br = rd(run / "break_even_hallucination.csv"), rd(run / "break_even_retrieval.csv")
    m = meta["equivalence_margins_abs"]
    body = [[NLAB[r["N"]], r["grid"].replace(";", ", "), sv(r["min_S_McNemar_p_ge_0.05_and_all_larger"])] + [sv(r[f"min_S_CI_within_pm{d}"]) for d in m]
            + [r[f"diff_S{s}"] for s in (256, 1024, 4096)] for r in bh]
    L += [f"**T7d Break-even, outcome level (7.3)** (`{rel(run / 'break_even_hallucination.csv')}`): smallest S in the Phase 5 grid at which the hallucination-rate difference (quantum - classical, seed 0, n=200, paired) is, at that S and every larger S in the grid, "
          f"(i) not significant by exact McNemar (p >= 0.05, uncorrected), or (ii) inside an equivalence band of +-{', +-'.join(str(d) for d in m)} (the whole 95% paired-bootstrap CI inside the band). "
          "(i) is absence of evidence at n=200 and is weak; (ii) is the stronger statement. The margins are analyst choices made after seeing the data (see Deviations); the band widths are shown, not defended.", "",
          md_table(["N", "S grid", "McNemar p>=0.05"] + [f"CI within +-{d}" for d in m] + ["diff at S=256", "diff at S=1024", "diff at S=4096"], body), ""]
    body = [[r["level"].split(" (")[0].replace("retrieval ", ""), NLAB[r["N"]], sv(r["min_S_CI_contains_0_and_all_larger"])] + [sv(r[f"min_S_CI_within_pm{d}"]) for d in m] for r in br]
    L += [f"**T7e Break-even, retrieval level** (`{rel(run / 'break_even_retrieval.csv')}`): same rules on the retrieval metrics (Phase 3, M=50, 5 seeds, 300 queries, grid 64 ... 16384; paired bootstrap CI of quantum - classical). Finer grid and more queries than T7d.", "",
          md_table(["Metric", "N", "CI contains 0 at S and all larger"] + [f"CI within +-{d}" for d in m], body), ""]
    cost = rd(run / "break_even_modelled_cost.csv")
    body = [[c["S"], c["MODELLED_circuits_per_query_shortlist"], f"{float(c['MODELLED_shots_per_query_shortlist']):.3g}", f"{float(c['MODELLED_2q_gate_exec_full_circuit_shortlist']):.3g}",
             f"{float(c['MODELLED_2q_gate_exec_swap_core_shortlist']):.3g}", c["MODELLED_circuits_per_query_full_scan_N_all"], f"{float(c['MODELLED_shots_per_query_full_scan_N_all']):.3g}"] for c in cost]
    L += [f"**T7f MODELLED quantum cost at the break-even shot counts** (`{rel(run / 'break_even_modelled_cost.csv')}`; per-shot gate counts derived from the Phase 4 modelled-cost table, T6 circuit counts). "
          "These are counts of circuit executions and shots a hypothetical device would need per query; they are NOT wall-clock time and imply nothing about speed.", "",
          md_table(["S", "Circuits/query (M=50)", "Shots/query (M=50)", "2q-gate executions, full circuit (M=50)", "2q-gate executions, SWAP core only (M=50)", "Circuits/query, full scan N=all", "Shots/query, full scan N=all"], body), "",
          f"For scale, the measured classical simulation of the real 19-qubit circuit (Tier A, Phase 3, S=1024) cost {meta['tierA_measured_seconds_per_circuit_S1024']:.3f} s per circuit on this laptop (`results/phase3/{meta['sources']['phase3']}/tierA_e2e_summary.json`); "
          "that is classical simulation cost, not quantum time.", ""]

    def bh_row(n):
        return next(r for r in bh if r["N"] == n)

    idx.append(["P7-3", 7, "Break-even S (hallucination, CI within +-0.075 at that and all larger S) at N=1000/5000/all: "
                + "/".join(sv(bh_row(n)["min_S_CI_within_pm0.075"]) for n in ("1000", "5000", "all")), rel(run / "break_even_hallucination.csv")])
    hr = next(r for r in br if r["N"] == "all" and r["level"].startswith("retrieval Hit@3"))
    idx.append(["P7-4", 7, f"Break-even S (Hit@3) at N=all: CI contains 0 from S={sv(hr['min_S_CI_contains_0_and_all_larger'])}; CI within +-0.05 from S={sv(hr['min_S_CI_within_pm0.05'])}", rel(run / "break_even_retrieval.csv")])

    sm, st = rd(run / "sensitivity_shortlist_M.csv"), rd(run / "sensitivity_tie_breaking.csv")
    body = [[NLAB[r["N"]], r["S"]] + [r.get(f"Hit@3_M{k}", "-") for k in ("20", "50", "100", "full")] + [f(r["range_across_M"]), f(r["max_sd_seeds"])] for r in sm]
    L += [f"**T7g Sensitivity to the shortlist size M (7.4)** (`{rel(run / 'sensitivity_shortlist_M.csv')}`): Hit@3 (mean of 5 seeds) for M in {{20, 50, 100, full scan}}; 'range' = max - min over M, to be read against the largest seed-to-seed sd in the row. Hallucination was only generated for M=50.", "",
          md_table(["N", "S", "M=20", "M=50", "M=100", "full", "Range over M", "Max seed sd"], body), ""]
    body = [[NLAB[r["N"]], r["S"], f(r["Hit@3_tie_classical"]), f(r["Hit@3_tie_random"]), f"{float(r['diff_random_minus_classical']):+.3f}", f(r["sd_seeds_classical"]), f(r["sd_seeds_random"])] for r in st]
    big = max(abs(float(r["diff_random_minus_classical"])) for r in st)
    L += [f"**T7h Sensitivity to tie-breaking** (`{rel(run / 'sensitivity_tie_breaking.csv')}`): Hit@3 at M=50 when equal estimates are ordered by classical score (default) vs at random. Largest absolute difference over the table: {big:.3f}.", "",
          md_table(["N", "S", "Hit@3 ties by classical score", "Hit@3 ties random", "Difference", "sd seeds (classical)", "sd seeds (random)"], body), "",
          f"**PCA-to-128-d (7 qubits) embedding-dimension sensitivity**: {meta['pca128_sensitivity']} (plan marks it [P2]; see Deviations).", ""]
    idx.append(["P7-5", 7, f"Tie-breaking sensitivity: max absolute Hit@3 difference = {big:.3f} over all (N, S)", rel(run / "sensitivity_tie_breaking.csv")])

    xml = run / "pytest_junit.xml"
    if xml.exists():
        r = ET.parse(xml).getroot()
        ts = r if r.tag == "testsuite" else r.find("testsuite")
        tot, fail, err, skip = (int(ts.get(x, 0)) for x in ("tests", "failures", "errors", "skipped"))
        L += [f"**pytest** (whole suite at Phase 7 exit): {tot} tests, {fail} failures, {err} errors, {skip} skipped (`{rel(xml)}`).", ""]
        idx.append(["P7-6", 7, f"pytest: {tot - fail - err - skip}/{tot} passed", rel(xml)])
    L += ["**Manuscript hook**: Section 10 (Discussion: tradeoffs / Pareto, break-even, what it means for cloud RAG) and Section 7 (scalability); Tables T7a-T7h; figures F7, F7b.", ""]
    return "\n".join(L), idx
