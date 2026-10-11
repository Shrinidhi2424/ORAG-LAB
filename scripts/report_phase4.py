"""Phase 4 block of FINDINGS.md, generated from results/phase4/<run_id>/ artifacts (used by report.py)."""
from __future__ import annotations

import csv
import json
import xml.etree.ElementTree as ET
from pathlib import Path

from report import latest_run, md_table, rel

NORDER = ["1000", "2000", "5000", "10000", "all"]


def rd(p: Path) -> list[dict]:
    return list(csv.DictReader(p.open(encoding="utf-8")))


def ci(r: dict, m: str) -> str:
    return f"{float(r[m]):.3f} [{float(r[m + '_lo']):.3f}, {float(r[m + '_hi']):.3f}]"


def phase4_block(run: Path) -> tuple[str, list[list]]:
    idx: list[list] = []
    p3 = latest_run("phase3")
    L = [f"Run `{run.name}` - manifest: `{rel(run / 'run_manifest.json')}`. Retrieval-only; inputs: Phase 1 ground truth, Phase 2 baselines, Phase 3 rankings (`{rel(p3)}`). "
         "Quantum-sim = SWAP-test simulation (M=50 shortlist unless stated). Latency of that arm is EMULATED-estimator latency, never quantum latency.", ""]

    mt = run / "main_table.csv"
    if mt.exists():
        main = rd(mt)
        body = []
        for n in NORDER:
            for r in (x for x in main if x["N"] == n):
                arm = r["arm"] + (f" S={r['S']}" if r["S"] else "")
                body.append([n, arm, *(ci(r, m) for m in ("Hit@1", "Hit@3", "Hit@5", "Hit@10", "MRR@10", "nDCG@10", "Overlap@10", "RBO"))])
        L += [f"**T3 main retrieval comparison (4.1)** (`{rel(mt)}`). Values with 95% bootstrap CI over the 300 queries (quantum: per-query mean over 5 seeds). "
              "Overlap@10 and RBO are versus the exact top-10; Flat is the reference (1 by construction).", "",
              md_table(["N", "Arm", "Hit@1", "Hit@3", "Hit@5", "Hit@10", "MRR@10", "nDCG@10", "Overlap@10", "RBO"], body), ""]
        a = next(r for r in main if r["N"] == "all" and r["arm"] == "Flat")
        q = next(r for r in main if r["N"] == "all" and r["arm"] == "Quantum-sim" and r["S"] == "1024")
        idx.append(["P4-1", 4, f"N=all: Hit@3 Flat {float(a['Hit@3']):.3f} vs Quantum-sim S=1024 {float(q['Hit@3']):.3f}", rel(mt)])
        L += ["**F4 quality vs N**: ![F4](results/figures/F4_quality_vs_N.png) (data `results/figures/F4_quality_vs_N.csv`).",
              "**F3 quality vs shots**: ![F3](results/figures/F3_quality_vs_shots.png) (data `results/figures/F3_quality_vs_shots.csv`).",
              "**F6 agreement with classical ranking vs shots**: ![F6](results/figures/F6_overlap_rbo_vs_shots.png) (data `results/figures/F6_overlap_rbo_vs_shots.csv`).", ""]

    ls, sl = run / "latency_summary.csv", run / "latency_slopes.csv"
    if ls.exists() and sl.exists():
        lat, slopes = rd(ls), rd(sl)

        def g(arm, n, m, s):
            return next(r for r in lat if (r["arm"], r["N"], r["M"], r["S"]) == (arm, n, str(m), str(s)))

        specs = [("Flat k=10", "flat", "", ""), ("IVF nprobe 16, k=10", "ivf", "", ""), ("Quantum-sim M=50 S=1024", "qsim", 50, 1024),
                 ("Quantum-sim full scan S=1024", "qsim", "full", 1024)]
        body = [[n, name, f"{float(g(a, n, m, s)['median_ms']):.3f}", f"{float(g(a, n, m, s)['p95_ms']):.3f}",
                 f"{float(g(a, n, m, s)['repeat_median_min_ms']):.3f}-{float(g(a, n, m, s)['repeat_median_max_ms']):.3f}"]
                for n in NORDER for name, a, m, s in specs]
        L += [f"**T4b In-process retrieval latency per query, embedding excluded (4.2)** (`{rel(ls)}`; raw `{rel(run / 'latency_raw.csv')}`). "
              "Protocol: batch-1, 10 warm-up discarded, 100 timed queries, 5 repeats, all conditions shuffled per repeat, 1 thread.", "",
              md_table(["N", "Arm", "Median ms", "p95 ms", "Range of repeat medians (ms)"], body), ""]
        sb = [[r["series"], f"{float(r['slope_b']):.3f} [{float(r['slope_lo']):.3f}, {float(r['slope_hi']):.3f}]", f"{float(r['r2_point_fit']):.3f}"] for r in slopes]
        L += [f"**Latency scaling: log-log exponent b in latency ~ N^b** (`{rel(sl)}`; point estimate on medians, 95% CI by bootstrapping the 5 repeat medians per N)", "",
              md_table(["Series", "b [95% CI]", "R^2 (point fit)"], sb), ""]
        brk = [[n, *(f"{float(g('qsim', n, 50, 1024)[f'median_{s}_ms']):.4f}" for s in ("search", "estimate", "rank")), f"{float(g('qsim', n, 50, 1024)['median_ms']):.3f}"] for n in NORDER]
        L += ["**Stage breakdown, Quantum-sim M=50 S=1024 (median ms)**: Flat shortlist search, binomial estimate, ranking.", "",
              md_table(["N", "Shortlist search", "Estimate (binomial)", "Rank", "Total"], brk), "",
              "**F5 latency vs N**: ![F5](results/figures/F5_latency_vs_N.png) (data `results/figures/F5_latency_vs_N.csv`).", ""]
        # 4.3 shot budget: latency vs S
        sbud = []
        for s in (64, 256, 1024, 4096, 16384):
            sbud.append([s, *(f"{float(g('qsim', 'all', m, s)['median_ms']):.3f}" for m in (20, 50, 100)),
                         f"{float(g('qsim', 'all', 'full', s)['median_ms']):.3f}" if s in (256, 1024, 16384) else "-"])
        L += ["**Shot-budget ablation (4.3): latency vs S at N=all** (median ms; emulator cost grows with candidates, hardly with S). "
              "Quality vs S is in the Phase 3 table and F3.", "", md_table(["S", "M=20", "M=50", "M=100", "full scan"], sbud), ""]
        a, b_ = next(r for r in slopes if r["series"].startswith("Flat")), next(r for r in slopes if r["series"].startswith("Quantum-sim shortlist M=50"))
        idx.append(["P4-2", 4, f"Latency exponent b: Flat {float(a['slope_b']):.2f}, Quantum-sim shortlist M=50 {float(b_['slope_b']):.2f}", rel(sl)])

    mc = run / "modelled_quantum_cost.csv"
    if mc.exists():
        cost = rd(mc)
        sel = [r for r in cost if r["N"] == "all" and r["S"] in ("256", "1024", "4096", "16384") and r["M"] in ("50", "full")]
        L += [f"**MODELLED quantum cost per query at N=all (not measured; Appendix A.3)** (`{rel(mc)}`): circuits = M (or N), shots = circuits x S; 2-qubit-gate executions use the T6 gate "
              "counts of the full circuit with generic state preparation and of the SWAP-test core alone. This is NOT wall-clock quantum speed.", "",
              md_table(["M", "S", "Circuits/query", "Shots/query", "2q-gate executions (full circuit)", "2q-gate executions (SWAP core only)"],
                       [[r["M"], r["S"], r["MODELLED_circuits_per_query"], r["MODELLED_total_shots_per_query"],
                         r["MODELLED_2q_gate_executions_per_query_full_circuit"], r["MODELLED_2q_gate_executions_per_query_swap_core_only"]] for r in sel]), ""]

    mv = run / "memory_vs_N.csv"
    if mv.exists():
        ms = json.loads((run / "memory_slopes.json").read_text(encoding="utf-8"))
        L += [f"**Memory vs N (4.2)** (`{rel(mv)}`; index bytes from Phase 2 `build.csv`): the shortlist arm needs the Flat index only; Tier A circuits would additionally need 512-d padded vectors; "
              "full scan holds the 384-d matrix.", "",
              md_table(["N", "Flat index bytes", "IVF index bytes", "Padded 512-d bytes (Tier A)", "Full-scan matrix bytes"],
                       [[r["N"], r["flat_index_bytes"], r["ivf_index_bytes"], r["padded_512d_vector_bytes_for_tierA"], r["qsim_fullscan_index_bytes"]] for r in rd(mv)]), "",
              f"Log-log slope of index bytes vs N: Flat {ms['loglog_slope_flat_index_bytes']:.3f}, IVF {ms['loglog_slope_ivf_index_bytes']:.3f}.", ""]

    p3m = p3 / "retrieval_metrics.csv" if p3 else None
    if p3m and p3m.exists():
        rm = rd(p3m)
        body = []
        for n in ("5000", "all"):
            for mval in ("20", "50", "100", "full"):
                row = [n, mval]
                for s in ("256", "1024", "4096"):
                    r = next(x for x in rm if (x["N"], x["M"], x["tie"], x["shots"]) == (n, mval, "classical", s))
                    row.append(f"{float(r['Hit@3']):.3f} / {float(r['MRR@10']):.3f} / {float(r['Overlap@10']):.3f}")
                lat_r = next((x for x in rd(ls) if (x["arm"], x["N"], x["M"], x["S"]) == ("qsim", n, mval, "1024")), None) if ls.exists() else None
                row.append(f"{float(lat_r['median_ms']):.3f}" if lat_r else "-")
                body.append(row)
        L += [f"**Shortlist ablation (4.4)**: M in {{20, 50, 100, N (full scan)}}; cells are Hit@3 / MRR@10 / Overlap@10 (mean of 5 seeds; Phase 3 `{rel(p3m)}`); last column: median latency ms at S=1024 (this phase).", "",
              md_table(["N", "M", "S=256", "S=1024", "S=4096", "Latency ms (S=1024)"], body), ""]

    fs, fe = run / "failure_summary.json", run / "failure_examples.csv"
    if fs.exists():
        f = json.loads(fs.read_text(encoding="utf-8"))
        c = f["config"]
        L += [f"**Failure analysis (4.5)** (`{rel(fs)}`, 20 examples with scores in `{rel(fe)}`): N={c['N']}, M={c['M']}, S={c['S']}, seed {c['seed']}, k={c['k']}. "
              f"Replay of the Phase 3 random stream reproduces the saved ranking exactly: {f['replay_matches_phase3_ranking']}. "
              f"Gold in classical top-{c['k']}: {f['gold_in_classical_top_k']}/{f['queries']}; in quantum top-{c['k']}: {f['gold_in_quantum_top_k']}/{f['queries']}. "
              f"Dropped by quantum (gold in classical top-{c['k']} but not quantum): {f['dropped_by_quantum']}; gained: {f['gained_by_quantum']}. "
              f"Median classical gold rank among dropped: {f['dropped_gold_rank_in_shortlist_median']}; mean estimated cos^2 of the dropped gold: {f['dropped_gold_c2_hat_mean']:.3f}.", ""]
        ex = rd(fe)[:5]
        L += ["First 5 of the 20 dumped examples (full text in the CSV):", "",
              md_table(["query_i", "gold classical rank", "gold cos", "gold k/S", "gold c2_hat (true)", "gold quantum rank in shortlist", "quantum top-3 c2_hat"],
                       [[e["query_i"], e["gold_classical_rank"], f"{float(e['gold_cos']):.3f}", f"{e['gold_zero_count_k']}/{c['S']}",
                         f"{float(e['gold_c2_hat']):.3f} ({float(e['gold_c2_true']):.3f})", e["gold_quantum_rank_in_shortlist"], e["quantum_top3_c2_hat"]] for e in ex]), ""]
        idx.append(["P4-3", 4, f"Failure analysis N=all S=256: {f['dropped_by_quantum']} dropped / {f['gained_by_quantum']} gained vs classical top-3", rel(fs)])

    tp = run / "tests.csv"
    if tp.exists():
        t = rd(tp)
        body = [[r["family"], r["metric"], r["N"], r["S"], f"{float(r['classical']):.3f}", f"{float(r['quantum_mean_over_seeds']):.3f}",
                 f"{float(r['diff']):+.3f} [{float(r['diff_lo']):+.3f}, {float(r['diff_hi']):+.3f}]", f"{float(r['p_paired_bootstrap']):.4f}",
                 f"{float(r['p_holm_primary']):.4f}", "yes" if r["significant_at_0.05_holm"] == "True" else "no",
                 f"{float(r['p_wilcoxon_signed_rank']):.4f}", f"{float(r['p_mcnemar_seed0']):.4f}" if r.get("p_mcnemar_seed0") else "-"] for r in t]
        nsig = sum(r["significant_at_0.05_holm"] == "True" for r in t)
        L += [f"**T5a Pre-registered tests (4.6, A.6), classical vs quantum-sim M=50** (`{rel(tp)}`). Primary test: paired bootstrap (10k) of the per-query difference between the seed-averaged quantum "
              "outcome and the classical outcome; Holm correction within each family (T-a Hit@3, T-b MRR@10; 15 tests each). Secondary, uncorrected: Wilcoxon signed-rank on the same differences and exact McNemar on seed 0 "
              f"(Hit@3 only). The bootstrap p floor is about 2e-4. {nsig} of {len(t)} primary tests are significant after Holm.", "",
              md_table(["Fam.", "Metric", "N", "S", "Classical", "Quantum", "Diff [95% CI]", "p (boot)", "p (Holm)", "Sig.", "p Wilcoxon", "p McNemar s0"], body), "",
              "T-c (hallucination rate, McNemar at N=all) belongs to Phase 5."]
        idx.append(["P4-4", 4, f"Pre-registered tests: {nsig}/{len(t)} significant after Holm", rel(tp)])
        L.append("")

    hy = run / "hygiene.json"
    if hy.exists():
        h = json.loads(hy.read_text(encoding="utf-8"))
        fr = json.loads((run / "cpu_freq_per_repeat.json").read_text(encoding="utf-8"))
        mhz = [x for r in fr for x in (r["cpu_mhz_start"], r["cpu_mhz_end"])]
        L += [f"**Measurement hygiene (H7)** (`{rel(hy)}`): plugged in = {h['power_plugged']}, battery {h['battery_percent']}%, power scheme `{h['power_scheme']}`, threads: {h['threads']}, "
              f"CPU temperature: {h['cpu_temperature']}. CPU MHz at repeat boundaries: min {min(mhz):.0f}, max {max(mhz):.0f}. {h['interleaving']}.", ""]
    xml = run / "pytest_junit.xml"
    if xml.exists():
        r = ET.parse(xml).getroot()
        ts = r if r.tag == "testsuite" else r.find("testsuite")
        tot, fail, err, skip = (int(ts.get(x, 0)) for x in ("tests", "failures", "errors", "skipped"))
        L += [f"**pytest** (whole suite at Phase 4 exit): {tot} tests, {fail} failures, {err} errors, {skip} skipped (`{rel(xml)}`).", ""]
        idx.append(["P4-5", 4, f"pytest: {tot - fail - err - skip}/{tot} passed", rel(xml)])
    L += ["**Manuscript hook**: Sections 7 (retrieval quality and scalability) and 9 (latency); Tables T3, T4, T5a; figures F3-F6.", ""]
    return "\n".join(L), idx
