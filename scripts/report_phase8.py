"""Phase 8 block of FINDINGS.md, generated from results/phase8/<run_id>/ artifacts (used by report.py)."""
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


def cell(s: str, n: int = 90) -> str:
    s = s.replace("|", "/").replace("\n", " ")
    return s if len(s) <= n else s[: n - 1] + "..."


def phase8_block(run: Path) -> tuple[str, list[list]]:
    idx: list[list] = []
    L = [f"Run `{run.name}` - manifest: `{rel(run / 'run_manifest.json')}`. Re-aggregates Phase 1-6 artifacts; the only new model run is the alternative faithfulness judge (NLI cross-encoder, 8.2). "
         "Quantum-sim = classical simulation of the SWAP test; latency/shots remarks follow the Phase 3-7 labelling.", ""]

    so = rd(run / "seed_robustness_outcomes.csv")
    body = [[NLAB[r["N"]], r["S"], f(r["classical_hall_rate"]), f(r["hall_rate_seed0"]), f(r["hall_rate_seed1"]), f(r["hall_rate_seed2"]), f(r["hall_rate_sd_seeds"]), f(r["hall_rate_range"]),
             f(r["flip_rate_hall_indicator"]), f(r["flip_rate_gold_in_context"]), f"{r['hall_flips_with_gold_in_context_flip']} / {r['hall_flips_with_gold_in_context_constant']}",
             f(r["always_hall_all_seeds"]), f(r["never_hall_any_seed"]), r["diff_vs_classical_seed0"], r["diff_vs_classical_seed1"], r["diff_vs_classical_seed2"]] for r in so]
    L += [f"**T8a Seed robustness of the hallucination outcome (8.1)** (`{rel(run / 'seed_robustness_outcomes.csv')}`): quantum-sim M=50, S=256, seeds 0/1/2, 200 questions. "
          "Flip rate = share of questions whose hallucinated-or-misread indicator is not the same in all three seeds. 'Flips with / without gold-in-context change' splits the flipped questions by whether "
          "the gold paragraph entered or left the top-3 between seeds. Differences vs classical: paired bootstrap CI and exact McNemar p (uncorrected).", "",
          md_table(["N", "S", "Classical rate", "Seed 0", "Seed 1", "Seed 2", "sd over seeds", "Range", "Flip rate (hall.)", "Flip rate (gold in ctx)", "Hall. flips with / without gold change",
                    "Hall. in all seeds", "Hall. in no seed", "Diff vs classical seed 0", "seed 1", "seed 2"], body), ""]
    for r in so:
        idx.append([f"P8-1{'a' if r['N'] == '5000' else 'b'}", 8, f"S=256 N={r['N']}: hallucination rate sd across 3 seeds {f(r['hall_rate_sd_seeds'])}, {f(r['flip_rate_hall_indicator'])} of questions flip outcome", rel(run / "seed_robustness_outcomes.csv")])

    rp = run / "seed_robustness_retrieval.csv"
    if rp.exists():
        rr = rd(rp)
        body = [[NLAB[r["N"]], r["S"], f(r["Hit@3_mean"]), f(r["Hit@3_sd_seeds"]), f(r["frac_queries_Hit@3_unstable"]), f(r["frac_queries_top1_unstable"]), f(r["frac_queries_top3_set_unstable"])] for r in rr]
        L += [f"**T8b Seed stability of retrieval, per query (8.1)** (`{rel(rp)}`): Phase 3 rankings, M=50, 5 seeds, 300 queries. 'Unstable' = not identical across the 5 seeds.", "",
              md_table(["N", "S", "Hit@3 (mean of seeds)", "sd over seeds", "Queries with unstable Hit@3", "Queries with unstable top-1", "Queries with unstable top-3 set"], body), ""]
        x = next(r for r in rr if r["N"] == "all" and r["S"] == "1024")
        idx.append(["P8-2", 8, f"N=all S=1024: {f(x['frac_queries_top1_unstable'])} of queries change top-1 across seeds, {f(x['frac_queries_Hit@3_unstable'])} change Hit@3", rel(rp)])
    else:
        L += ["**T8b**: skipped, Phase 3 rankings not present locally (see `seed_robustness_retrieval_SKIPPED.json`).", ""]

    ti = json.loads((run / "threshold_invariance.json").read_text(encoding="utf-8"))
    tt = rd(run / "threshold_sensitivity_tests.csv")
    sel = [r for r in tt if r["seed"] == "0"]
    body = []
    for key in dict.fromkeys((r["N"], r["S"]) for r in sel):
        cells = [next(r for r in sel if (r["N"], r["S"]) == key and r["threshold"] == t) for t in ("0.3", "0.5", "0.7")]
        body.append([NLAB[key[0]], key[1]] + [f"{float(c['diff']):+.3f} (p={float(c['p_mcnemar']):.3f})" for c in cells])
    cons = 0
    tot = 0
    for key in dict.fromkeys((r["N"], r["S"], r["seed"]) for r in tt):
        sig = [float(r["p_mcnemar"]) < 0.05 for r in tt if (r["N"], r["S"], r["seed"]) == key]
        tot += 1
        cons += len(set(sig)) == 1
    L += [f"**T8c HHEM threshold sensitivity of the conclusions (8.2)** (`{rel(run / 'threshold_sensitivity_tests.csv')}`). The headline hallucination rate (hallucinated + misread) uses only correctness, abstention and gold-in-context: "
          f"identical across thresholds for every arm = {ti['hallucination_rate_identical_across_thresholds_for_all_arms']} (Phase 5 `threshold_sweep.csv`). The ungrounded-answer rate does depend on the threshold; the table gives the "
          "quantum - classical difference (same N, seed 0) at thresholds 0.3 / 0.5 / 0.7 with exact McNemar p (uncorrected, exploratory).", "",
          md_table(["N", "S", "diff @0.3", "diff @0.5", "diff @0.7"], body), "",
          f"Significance at 0.05 is the same at all three thresholds in {cons} of {tot} (N, S, seed) comparisons; the sign of the difference is reported in the table.", ""]
    idx.append(["P8-3", 8, f"HHEM threshold: significance verdict identical across 0.3/0.5/0.7 in {cons}/{tot} comparisons; hallucination rate threshold-invariant: {ti['hallucination_rate_identical_across_thresholds_for_all_arms']}", rel(run / "threshold_sensitivity_tests.csv")])

    ns = run / "nli_summary.json"
    if ns.exists():
        s = json.loads(ns.read_text(encoding="utf-8"))
        body = [[t, f(v["agreement"]), f(v["kappa"]), f(v["faithful_rate_hhem"]), f(v["faithful_rate_nli"])] for t, v in s["by_threshold"].items()]
        a = s["quantum_vs_classical_ungrounded_direction_agrees_across_judges"]
        L += [f"**T8d Alternative judge: NLI cross-encoder (8.2)** (`{rel(ns)}`; scores `{rel(run / 'nli_scores.csv')}`). `{s['model']}` @ `{s['revision']}`; {s['premise_handling']}. "
              f"{s['answers_scored']} non-abstained RAG answers of all P0 arms ({s['paragraph_pairs']} paragraph pairs). Spearman correlation HHEM vs NLI score: {f(s['spearman_hhem_vs_nli'])}. "
              "Faithful = score >= threshold; the same threshold is applied to both judges (they are not calibrated to each other).", "",
              md_table(["Threshold", "Agreement on faithful / not", "Cohen kappa", "Faithful rate (HHEM)", "Faithful rate (NLI)"], body), "",
              f"Direction of 'quantum-sim ungrounded rate above/below classical at the same N' at threshold 0.5 agrees between the two judges in {a['agree']} of {a['total']} arms.", ""]
        by = rd(run / "nli_by_arm.csv")
        body = [[r["arm"], r["n_scored"], f(r["ungrounded_hhem_0.5"]), f(r["ungrounded_nli_0.5"])] for r in by]
        L += [f"Ungrounded-answer rate by arm under each judge (threshold 0.5; `{rel(run / 'nli_by_arm.csv')}`):", "", md_table(["Arm", "Answers scored", "HHEM", "NLI"], body), ""]
        idx.append(["P8-4", 8, f"NLI vs HHEM faithfulness @0.5: agreement {f(s['by_threshold']['0.5']['agreement'])}, kappa {f(s['by_threshold']['0.5']['kappa'])}, Spearman {f(s['spearman_hhem_vs_nli'])}", rel(ns)])
    else:
        L += ["**T8d**: alternative judge not run (see Failures).", ""]

    ex = rd(run / "qualitative_examples.csv")
    cc = json.loads((run / "qualitative_category_counts.json").read_text(encoding="utf-8"))
    body = [[r["category"].split(",")[0].split(" (")[0], r["qi"], cell(r["question"], 70), cell(r["gold_answers"], 25), r["classical_gold_rank_Nall"], r["classical_cosines"], cell(r["classical_answer"], 45),
             r["classical_outcome"], r["quantum_S256_cosines"], cell(r["quantum_S256_answer"], 45), r["quantum_S256_outcome"]] for r in ex]
    L += [f"**T8e Qualitative error analysis, 20 curated examples (8.3)** (`{rel(run / 'qualitative_examples.csv')}`, full text, retrieved ids and HHEM scores in the CSV). Classical Flat vs quantum-sim S=256 seed 0, N=all, first 200 questions. "
          f"Pool sizes in these categories: {json.dumps(cc['pool_sizes_n200_N_all_S256_seed0'])}; examples drawn at random within category (seed 8). Cosines = exact query-paragraph cosine of the retrieved top-3 in rank order. "
          "'Gold rank' = rank of the gold paragraph under exact cosine at N=all (blank = outside the stored top-50).", "",
          md_table(["Category", "q", "Question", "Gold", "Gold rank", "Classical cos (top-3)", "Classical answer", "Outcome", "Quantum cos (top-3)", "Quantum answer", "Outcome"], body), ""]
    idx.append(["P8-5", 8, f"20 curated classical-vs-quantum examples written; pools: {sum(cc['pool_sizes_n200_N_all_S256_seed0'].values())} questions in 4 categories", rel(run / "qualitative_examples.csv")])

    au = json.loads((run / "audit_agreement.json").read_text(encoding="utf-8"))
    L += [f"**Hand audit (8.4)** (`{rel(run / 'audit_agreement.json')}`): {au['rows_labelled']} of {au['rows']} rows of `results/audit_template.csv` carry human labels; status: {au['status']}."]
    if au["status"] == "computed":
        L.append("Agreement: " + json.dumps({k: v for k, v in au.items() if k in ("correctness", "faithfulness_hhem_0.5", "outcome_taxonomy")}))
    L.append("")
    idx.append(["P8-6", 8, f"Hand audit: {au['rows_labelled']}/{au['rows']} rows labelled; {au['status']}", rel(run / "audit_agreement.json")])

    th = rd(run / "threats_matrix.csv")
    L += [f"**T8f Threats-to-validity matrix (plan table T7; 8.5)** (`{rel(run / 'threats_matrix.csv')}`): each threat with its evidence read from the artifacts, the direction of the possible bias, and the artifact.", "",
          md_table(["Threat", "Evidence", "Direction / consequence", "Artifact"], [[t["threat"], cell(t["evidence"], 400), cell(t["direction"], 300), f"`{t['artifact']}`"] for t in th]), ""]
    idx.append(["P8-7", 8, f"Threats-to-validity matrix: {len(th)} threats with artifact evidence", rel(run / "threats_matrix.csv")])

    xml = run / "pytest_junit.xml"
    if xml.exists():
        r = ET.parse(xml).getroot()
        ts = r if r.tag == "testsuite" else r.find("testsuite")
        tot_, fail, err, skip = (int(ts.get(x, 0)) for x in ("tests", "failures", "errors", "skipped"))
        L += [f"**pytest** (whole suite at Phase 8 exit): {tot_} tests, {fail} failures, {err} errors, {skip} skipped (`{rel(xml)}`).", ""]
        idx.append(["P8-8", 8, f"pytest: {tot_ - fail - err - skip}/{tot_} passed", rel(xml)])
    L += ["**Manuscript hook**: Section 8 (hallucination analysis: robustness, error analysis) and Section 11 (limitations and threats to validity); Tables T8a-T8f.", ""]
    return "\n".join(L), idx
