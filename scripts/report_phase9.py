"""Phase 9 blocks of FINDINGS.md (used by report.py): Headline Findings (section 3, task 9.5), the Phase 9 report with the
clean-room reproduction, determinism, numbers audit and the Acceptance Checklist (9.1-9.4, 9.6), and the reproduction
commands (section 6).

Every number is read from an artifact. Every qualitative sentence in the headline findings is guarded by a claim check
evaluated on the same artifacts; a failed check is printed in the block instead of being silently kept.
"""
from __future__ import annotations

import csv
import json
import re
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

from report import ROOT, latest_run, md_table, rel

NLAB = {"1000": "1k", "2000": "2k", "5000": "5k", "10000": "10k", "all": "all (20,958)"}
NS = ["1000", "2000", "5000", "10000", "all"]
DEFINITION = ("**Terminology (defined once).** In this work, *quantum-inspired retrieval* means a retrieval stage whose similarity scores are obtained by "
              "classically simulating a quantum similarity-estimation procedure (the SWAP test), including its finite-shot measurement statistics. "
              "No quantum hardware is used and no speedup is claimed. This is distinct from strictly 'dequantised' algorithms such as Tang's.")


OK_STATUS = ("identical", "equal_ignoring_timing", "equal_ignoring_line_endings")


def reproduced(c: dict) -> int:
    return c["identical"] + c["equal_ignoring_timing"] + c.get("equal_ignoring_line_endings", 0)


def rd(p: Path) -> list[dict]:
    return list(csv.DictReader(p.open(encoding="utf-8")))


def js(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def f(x, d=3) -> str:
    return "-" if x in ("", None) else f"{float(x):.{d}f}"


def pp(x, d=3) -> str:
    return f"{float(x):+.{d}f}"


class Claims:
    def __init__(self):
        self.results: list[tuple[str, bool]] = []

    def __call__(self, text: str, ok: bool) -> str:
        self.results.append((text, bool(ok)))
        return text if ok else f"**CLAIM CHECK FAILED - do not use:** {text}"

    def line(self) -> str:
        bad = [t for t, ok in self.results if not ok]
        return f"Claim checks on the artifacts: {len(self.results) - len(bad)}/{len(self.results)} passed" + ("." if not bad else f"; FAILED: {bad}")


# ---------------------------------------------------------------------------------------------------------------------
def headline_block() -> tuple[str, list[list]]:
    p3, p4, p5, p6, p7, p8 = (latest_run(f"phase{i}") for i in (3, 4, 5, 6, 7, 8))
    C = Claims()
    idx: list[list] = []
    L = [DEFINITION, "",
         "Each answer below cites the table / figure that supports it; every number is generated from the artifacts by `scripts/report_phase9.py`. "
         "'Quantum-sim' = the SWAP-test simulation arm (two-stage: Flat shortlist M=50, then the shot-limited estimator), 'classical' = FAISS Flat (exact cosine).", ""]

    # ---------------- RQ1 hallucination
    pt = rd(p5 / "paired_tests.csv")
    tc = sorted((r for r in pt if r["family"] == "T-c"), key=lambda r: int(r["S"]))
    h4096 = next(r for r in pt if r["metric"] == "hallucinated_or_misread" and r["N"] == "all" and r["S"] == "4096" and r["seed"] == "0")
    out = {r["arm"]: r for r in rd(p5 / "outcomes_by_arm.csv")}
    cl_all, q64 = out["classical_Nall_k3"], out["quantum_Nall_M50_S64_seed0_k3"]
    med = rd(p5 / "mediation_by_gold_in_context.csv")
    rag = [r for r in med if r["arm"].startswith(("classical", "quantum"))]
    rate = {g: [float(r["hallucinated_or_misread_rate"]) for r in rag if r["gold_in_context"] == g] for g in ("True", "False")}
    within = max(max(v) - min(v) for v in rate.values())
    gap = min(rate["False"]) - max(rate["True"])
    abst_max = max(float(r["abstention_rate"]) for r in rag if r["gold_in_context"] == "False")
    so = {r["N"]: r for r in rd(p8 / "seed_robustness_outcomes.csv")}
    seed_pos = all(r["diff_vs_classical_seed" + s].startswith("+") for r in so.values() for s in "012")
    sig = [r for r in tc if float(r["p_holm_T-c"]) < 0.05]
    L += ["### RQ1 - Hallucination: does swapping the retrieval stage change the rate / type of hallucinated answers?", "",
          "- " + C(f"Yes at low shot budgets, no detectable change at high ones. Pre-registered T-c (N=all, seed 0, 200 questions, exact McNemar, Holm): "
                   + "; ".join(f"S={r['S']}: {pp(r['diff'])} [{pp(r['diff_lo'])}, {pp(r['diff_hi'])}], p_Holm={float(r['p_holm_T-c']):.3f}" for r in tc)
                   + f" (hallucination rate quantum - classical; classical = {f(cl_all['hallucination_rate'])}).",
                   len(sig) >= 1 and float(tc[-1]["p_holm_T-c"]) >= 0.05 and float(tc[0]["diff"]) > 0),
          "- " + C(f"Only S=64 survives Holm correction; S=256 is nominally significant uncorrected and seeds 1-2 at S=256 also show more hallucination than classical "
                   f"(all three seeds positive: {seed_pos}). At S=4096 (exploratory) the difference is {pp(h4096['diff'])} [{pp(h4096['diff_lo'])}, {pp(h4096['diff_hi'])}].",
                   len(sig) == 1 and sig[0]["S"] == "64" and seed_pos),
          "- " + C(f"Mechanism: the effect runs through retrieval. Whether the gold paragraph reached the top-3 dominates the outcome: across all classical and quantum-sim RAG arms, "
                   f"the hallucinated-or-misread rate is {f(min(rate['True']))}-{f(max(rate['True']))} when gold is in context and {f(min(rate['False']))}-{f(max(rate['False']))} when it is not; "
                   f"the spread within either stratum ({f(within)}) is smaller than the gap between strata ({f(gap)}). Low shot counts lower the gold-in-context rate "
                   f"(N=all: classical {f(cl_all['gold_in_context_rate'])} vs S=64 {f(q64['gold_in_context_rate'])}), and the small generator rarely abstains when gold is missing "
                   f"(abstention at most {f(abst_max)} in that stratum).",
                   within < gap and abst_max < 0.25),
          f"- Evidence: Table T5c (`{rel(p5 / 'paired_tests.csv')}`), mediation table and F9 (`{rel(p5 / 'mediation_by_gold_in_context.csv')}`), F8, seed table T8a (`{rel(p8 / 'seed_robustness_outcomes.csv')}`).",
          "- Strength of evidence: **moderate**. One generator (1.5B), one dataset, 200 questions, T-c on seed 0 only; the outcome definition does not depend on the HHEM threshold, "
          "but the faithfulness judge is unvalidated by humans (audit pending) and agrees only weakly with an NLI cross-check (T8d).", ""]
    idx.append(["H-1", 9, "RQ1: hallucination rises at S=64 (Holm-significant), no detectable change at S>=1024; mediated by gold-in-context", rel(p5 / "paired_tests.csv")])

    # ---------------- RQ2 latency
    lat = rd(p4 / "latency_summary.csv")
    fl = next(r for r in lat if r["arm"] == "flat" and r["N"] == "all")
    qs = next(r for r in lat if r["arm"] == "qsim" and r["N"] == "all" and r["M"] == "50" and float(r["S"]) == 1024)
    full = next(r for r in lat if r["arm"] == "qsim" and r["N"] == "all" and r["M"] == "full" and float(r["S"]) == 1024)
    h6 = {(r["profile"], r["arm"], r["N"]): r for r in rd(p6 / "latency_summary.csv")}
    hc, hq = h6[("medium", "classical", "all")], h6[("medium", "quantum", "all")]
    cost = {int(r["S"]): r for r in rd(p7 / "break_even_modelled_cost.csv")}
    tA = js(p3 / "tierA_e2e_summary.json")
    fl_rng = (float(fl["repeat_median_min_ms"]), float(fl["repeat_median_max_ms"]))
    L += ["### RQ2 - Latency: cost / benefit of the quantum-inspired stage, shot dependence, end-to-end vs retrieval-only", "",
          "- " + C(f"Retrieval-only, in-process (emulated estimator, N=all): Flat {f(fl['median_ms'])} ms vs quantum-sim M=50 S=1024 {f(qs['median_ms'])} ms median; "
                   f"the quantum-sim median lies inside Flat's run-to-run range of repeat medians ({f(fl_rng[0])}-{f(fl_rng[1])} ms), i.e. no measurable difference. "
                   f"The estimator stage itself costs {f(qs['median_estimate_ms'])} ms of it; the shortlist arm runs the exact Flat search first, so it cannot be faster than Flat. "
                   f"Full-scan estimation costs {f(full['median_ms'])} ms.",
                   fl_rng[0] <= float(qs["median_ms"]) <= fl_rng[1] and float(full["median_ms"]) > float(fl["median_ms"])),
          "- " + C(f"Shot budget barely moves emulated latency (it draws one binomial per candidate), but it sets the MODELLED quantum cost: at S=1024, "
                   f"{int(cost[1024]['MODELLED_circuits_per_query_shortlist'])} circuits and {int(cost[1024]['MODELLED_shots_per_query_shortlist']):,} shots per query (shortlist), "
                   f"{int(cost[1024]['MODELLED_shots_per_query_full_scan_N_all']):,} shots for a full scan. Simulating the real 19-qubit circuit classically (Tier A) took "
                   f"{f(tA['seconds_per_circuit'])} s per circuit on this laptop. None of these is wall-clock quantum time.", 1024 in cost),
          "- " + C(f"End-to-end over HTTP (containers, medium profile, N=all): classical {f(hc['e2e_median_ms'], 1)} ms vs quantum-sim {f(hq['e2e_median_ms'], 1)} ms median; "
                   f"query embedding ({f(hc['embed_compute_median_ms'], 1)} ms compute) and service hops dominate, and retrieval compute is {f(hc['retrieve_compute_median_ms'], 1)} / "
                   f"{f(hq['retrieve_compute_median_ms'], 1)} ms. Generation dwarfs all of it (median {f(cl_all['median_gen_wall_s'], 1)} s per uncached answer on this CPU, classical N=all).",
                   float(hc["embed_compute_median_ms"]) > float(hc["retrieve_compute_median_ms"]) and float(hq["embed_compute_median_ms"]) > float(hq["retrieve_compute_median_ms"])
                   and float(cl_all["median_gen_wall_s"]) * 1000 > 10 * float(hc["e2e_median_ms"])),
          f"- Evidence: T4b and stage breakdown (`{rel(p4 / 'latency_summary.csv')}`), F5, T4c / F5b (`{rel(p6 / 'latency_summary.csv')}`), T7f (`{rel(p7 / 'break_even_modelled_cost.csv')}`).",
          "- Strength of evidence: **strong for 'no latency benefit from the emulated estimator'**; no evidence at all about quantum hardware latency (not measured, by design). "
          "Absolute numbers are specific to a shared, CPU-only laptop (Balanced power plan, temperature not monitored).", ""]
    idx.append(["H-2", 9, f"RQ2: N=all retrieval median Flat {f(fl['median_ms'])} ms vs quantum-sim {f(qs['median_ms'])} ms (emulated; within noise)", rel(p4 / "latency_summary.csv")])

    # ---------------- RQ3 scalability
    tests = rd(p4 / "tests.csv")
    gap_n = {n: next(r for r in tests if r["metric"] == "Hit@3" and r["N"] == n and r["S"] == "1024") for n in NS}
    thr = {r["N"]: r for r in rd(p3 / "shot_thresholds.csv") if r["M"] == "50" and r["tie"] == "classical"}
    tvals = [thr[n]["min_shots_Hit@3_indistinguishable"] for n in NS]
    tnum = [float(x) if x not in ("", None) else float("inf") for x in tvals]
    sl = {r["series"]: r for r in rd(p4 / "latency_slopes.csv")}
    s_flat = next(v for k, v in sl.items() if k.startswith("Flat"))
    s_q = next(v for k, v in sl.items() if k.startswith("Quantum-sim shortlist M=50"))
    overlap = float(s_flat["slope_lo"]) <= float(s_q["slope_hi"]) and float(s_q["slope_lo"]) <= float(s_flat["slope_hi"])
    mem = rd(p4 / "memory_vs_N.csv")
    m_all = next(r for r in mem if r["N"] == "all")
    L += ["### RQ3 - Scalability: quality, latency and memory as the corpus grows", "",
          "- " + C("At a fixed shot budget the quantum-sim quality gap is larger at N=all than at N=1k (not monotone at every rung): Hit@3 difference (quantum - classical, M=50, S=1024, mean of 5 seeds) "
                   + ", ".join(f"N={NLAB[n]} {pp(gap_n[n]['diff'])}" for n in NS) + ".",
                   float(gap_n["all"]["diff"]) < float(gap_n["1000"]["diff"])),
          "- " + C("Equivalently, the shot budget needed before the Hit@3 difference is statistically indistinguishable from zero (paired CI, at that S and all larger S) grows with N: "
                   + ", ".join(f"N={NLAB[n]}: {int(t) if t != float('inf') else 'not reached'}" for n, t in zip(NS, tnum))
                   + ". Mechanism (observation, not a tested model): shot noise ~1/sqrt(S) against a shrinking score margin between the gold paragraph and more distractors.",
                   all(a <= b for a, b in zip(tnum, tnum[1:])) and tnum[-1] > tnum[0]),
          "- " + C(f"Latency scaling exponents (latency ~ N^b, in-process): Flat {f(s_flat['slope_b'], 2)} [{f(s_flat['slope_lo'], 2)}, {f(s_flat['slope_hi'], 2)}], "
                   f"quantum-sim shortlist {f(s_q['slope_b'], 2)} [{f(s_q['slope_lo'], 2)}, {f(s_q['slope_hi'], 2)}]; the intervals overlap, so neither arm can be said to scale worse in latency.",
                   overlap),
          f"- Memory grows linearly with N for both arms (they share the Flat index: {int(m_all['flat_index_bytes']):,} bytes at N=all); running Tier A circuits would additionally need "
          f"the 512-d padded vectors ({int(m_all['padded_512d_vector_bytes_for_tierA']):,} bytes).",
          f"- Evidence: T3 / F4 (`{rel(p4 / 'main_table.csv')}`), T5a (`{rel(p4 / 'tests.csv')}`), shot thresholds (`{rel(p3 / 'shot_thresholds.csv')}`), latency slopes / F5 (`{rel(p4 / 'latency_slopes.csv')}`), memory (`{rel(p4 / 'memory_vs_N.csv')}`).",
          "- Strength of evidence: **moderate for the quality trend** (300 queries, 5 seeds, consistent across rungs); **weak for latency scaling** (wide exponent CIs, N <= 20,958; no extrapolation to production scale).", ""]
    idx.append(["H-3", 9, f"RQ3: Hit@3 gap at S=1024 widens from {pp(gap_n['1000']['diff'])} (N=1k) to {pp(gap_n['all']['diff'])} (N=all); shots needed grow with N", rel(p4 / "tests.csv")])

    # ---------------- RQ4 tradeoff
    ph = rd(p7 / "pareto_hallucination.csv")
    pm = rd(p7 / "pareto_retrieval_miss.csv")
    flat_nd = all(r["non_dominated"] == "True" for r in ph if r["arm"] == "Flat")
    q_nd = [r for r in ph if r["arm"] != "Flat" and r["non_dominated"] == "True"]
    q_nd_noise = all(float(next(x for x in ph if x["arm"] == "Flat" and x["N"] == r["N"])["latency_lo_ms"]) <= float(r["latency_ms"]) for r in q_nd)
    q_rob = sum(r["robustly_dominated"] == "True" for r in ph if r["arm"] != "Flat")
    ivf_nd = all(r["non_dominated"] == "True" for r in pm if r["arm"] == "IVF")
    for n in NS:
        iv = next(r for r in pm if r["arm"] == "IVF" and r["N"] == n)
        fr = next(r for r in pm if r["arm"] == "Flat" and r["N"] == n)
        ivf_nd = ivf_nd and float(iv["latency_ms"]) < float(fr["latency_ms"]) and float(fr["miss_lo"]) <= float(iv["miss_rate"]) <= float(fr["miss_hi"])
    be = {r["N"]: r for r in rd(p7 / "break_even_hallucination.csv")}
    ber = {r["N"]: r for r in rd(p7 / "break_even_retrieval.csv") if r["level"].startswith("retrieval Hit@3")}
    be_s = [be[n]["min_S_CI_within_pm0.075"] for n in ("1000", "5000", "all")]
    L += ["### RQ4 - Tradeoff: is there a Pareto frontier (hallucination vs latency vs corpus size), and where does each arm sit?", "",
          "- " + C("Exact Flat retrieval is on the Pareto front at every corpus size. "
                   + (f"{len(q_nd)} quantum-sim point(s) are also nominally non-dominated, but only through median latency differences inside Flat's run-to-run range; "
                      if q_nd else "No quantum-sim point is non-dominated; ")
                   + f"{q_rob} quantum-sim point(s) are robustly dominated (low S). The quantum-sim arm therefore buys nothing on this frontier: it can at best match Flat.",
                   flat_nd and q_nd_noise),
          "- " + C("Break-even (smallest S whose hallucination difference vs classical has its whole 95% CI within +-0.075, at that and every larger S): "
                   + ", ".join(f"N={NLAB[n]}: {s}" for n, s in zip(("1000", "5000", "all"), be_s))
                   + f"; at retrieval level, Hit@3 needs S={ber['all']['min_S_CI_contains_0_and_all_larger']} at N=all for its CI to contain 0. "
                   f"At S=1024 that is {int(cost[1024]['MODELLED_shots_per_query_shortlist']):,} modelled shots per query.",
                   all(s not in ("", None) for s in be_s)),
          "- " + C("For a practical cloud deployment the relevant frontier is retrieval-only: IVF (nprobe 16) is non-dominated at every N, at lower latency than Flat with a miss rate inside Flat's CI band (T7c, F7b).",
                   ivf_nd),
          f"- Evidence: T7b / F7 (`{rel(p7 / 'pareto_hallucination.csv')}`), T7c / F7b (`{rel(p7 / 'pareto_retrieval_miss.csv')}`), T7d-T7f (`{rel(p7 / 'break_even_hallucination.csv')}`).",
          "- Strength of evidence: **moderate**. Hallucination and latency come from different runs (D-7.1); equivalence margins are post hoc (D-7.2); "
          "the conclusion 'no tradeoff advantage in simulation' is robust to those choices because the quantum-sim arm executes the Flat search as its first stage.", ""]
    idx.append(["H-4", 9, f"RQ4: Flat on the Pareto front at every N; hallucination break-even (+-0.075) at S={'/'.join(be_s)}", rel(p7 / "pareto_hallucination.csv")])

    L += ["**Overall**: the expected result of plan section 1 holds and is documented with its mechanism: at high shot counts the simulated quantum-inspired arm retrieves "
          "almost like exact cosine (near-null differences), at low shot counts it degrades retrieval and, through missing gold paragraphs, increases hallucination. "
          "No speedup is claimed or observed; the emulated estimator adds work on top of the exact search.", "", C.line(), ""]
    return "\n".join(L), idx, C


# ---------------------------------------------------------------------------------------------------------------------
def git_phase_commits() -> list[tuple[str, str, str]]:
    r = subprocess.run(["git", "log", "--reverse", "--format=%h|%an|%s"], cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
    out = []
    for line in r.stdout.splitlines():
        h, a, s = line.split("|", 2)
        m = re.match(r"(?:fix\()?phase-(\d+)", s)
        if m:
            out.append((h, a, s))
    return out


def checklist() -> list[list]:
    P = {i: latest_run(f"phase{i}") for i in range(10)}
    rows = []

    def add(item, ok, ev):
        rows.append(["[x]" if ok is True else "[ ]", item, ev])

    gb = js(P[0] / "generator_bench_summary.json")
    passing = [m["model"] for m in gb["models"] if m["passes_gate"]]
    add("Generator benchmark table recorded; model chosen by the H2 rule", bool(gb["chosen"]) and gb["chosen"] in passing, f"chosen {gb['chosen']}; passing {passing} (`{rel(P[0] / 'generator_bench_summary.json')}`)")
    man = [d for i in range(9) if P[i] for d in [P[i]] if (d / "run_manifest.json").exists() or (d / "manifests").exists()]
    add("Environment recorded; versions pinned; seeds fixed; manifests written", (P[0] / "env.json").exists() and (ROOT / "requirements.lock").exists() and len(man) == 9,
        f"env.json, requirements.lock; run manifests for {len(man)}/9 phase runs 0-8")
    cs = js(P[1] / "corpus_stats.json")
    add("Corpus ladder nested, gold always included; 300 questions fixed", cs["ladder_nested"] and cs["gold_in_every_rung"] and cs["n_eval"] == 300, f"`{rel(P[1] / 'corpus_stats.json')}`")
    q2 = rd(P[2] / "quality.csv")
    l4 = rd(P[4] / "latency_summary.csv")
    ok2 = all(any(r["arm"] == a and r["N"] == n for r in q2) for a in ("flat", "ivf") for n in NS) and all(any(r["arm"] == a and r["N"] == n for r in l4) for a in ("flat", "ivf") for n in NS)
    add("Classical Flat (and IVF) metrics + latency for all N", ok2, f"`{rel(P[2] / 'quality.csv')}`, `{rel(P[4] / 'latency_summary.csv')}`")
    v = js(P[3] / "validation.json")
    slope = v["loglog_slope_tierB"]["slope"]
    add("Tier B emulator validated vs theory and vs Tier A (F2)", abs(slope + 0.5) < 0.05 and (ROOT / "results/figures/F2_error_vs_shots.png").exists(),
        f"RMSE slope {slope:.3f} (theory -0.5); KS A vs B p={v['ks_two_sample_z_tierA_vs_tierB']['p']:.3f}; repeated-estimate KS caveat in Failures")
    rm = rd(P[3] / "retrieval_metrics.csv")
    combos = {(r["N"], r["M"], r["shots"]) for r in rm if r["tie"] == "classical"}
    need = {(n, m, s) for n in NS for m in ("20", "50", "100", "full") for s in ("64", "128", "256", "512", "1024", "2048", "4096", "8192", "16384")}
    add("Quantum arm results: all S, M, N, R=5 seeds", need <= combos and all(r.get("Hit@3_sd_seeds") not in ("", None) for r in rm if r["shots"] not in ("classical", "inf")),
        f"{len(need & combos)}/{len(need)} (N, M, S) configurations with 5-seed sd (`{rel(P[3] / 'retrieval_metrics.csv')}`)")
    cc = js(P[5] / "controls_check.json")
    add("Controls run (closed-book, oracle, random) and sane", cc["oracle_correct_gt_closed_book"] and cc["random_correct_le_closed_book"], f"`{rel(P[5] / 'controls_check.json')}`")
    ts = {r["threshold"] for r in rd(P[5] / "threshold_sweep.csv")}
    add("Hallucination taxonomy + HHEM + threshold sensitivity", ts == {"0.3", "0.5", "0.7"} and (P[5] / "judged.csv").exists(), f"thresholds {sorted(ts)}; NLI cross-check in Phase 8")
    t4 = rd(P[4] / "tests.csv")
    t5 = rd(P[5] / "paired_tests.csv")
    add("McNemar/bootstrap tests with Holm correction", all(r["p_holm_primary"] for r in t4) and any(r.get("p_holm_T-c") for r in t5), "T-a/T-b (Phase 4, 30 tests), T-c (Phase 5, 3 tests)")
    sm = js(P[6] / "smoke_test.json") if (P[6] / "smoke_test.json").exists() else js(next(ROOT.glob("results/phase6/*/smoke_test.json")))
    add("Cloud-native stack runs (Docker or logged fallback); HTTP latency measured", sm["all_ok"] and (P[6] / "latency_summary.csv").exists(), "Docker compose stack; T4c")
    add("Concurrency test (P1) or logged skip", (P[6] / "concurrency.csv").exists(), f"`{rel(P[6] / 'concurrency.csv')}`")
    cr = P[9] / "clean_room_summary.json"
    xml = P[9] / "pytest_junit.xml"
    if cr.exists() and xml.exists():
        c = js(cr)
        r_ = ET.parse(xml).getroot()
        t_ = r_ if r_.tag == "testsuite" else r_.find("testsuite")
        tot, bad = int(t_.get("tests", 0)), int(t_.get("failures", 0)) + int(t_.get("errors", 0))
        add("Clean-room reproduction passes; pytest passes", c["different"] == 0 and c["missing"] == 0 and bad == 0,
            f"{reproduced(c)}/{c['comparisons']} artifacts reproduced; pytest {tot - bad}/{tot}")
    else:
        add("Clean-room reproduction passes; pytest passes", False, "not run yet")
    findings = (ROOT / "FINDINGS.md").read_text(encoding="utf-8")
    sheet = re.search(r"## 8\. Manuscript Numbers Sheet\n(.*)", findings, re.S)
    add("FINDINGS.md complete incl. Deviations, Limitations, Numbers Sheet", bool(sheet and "BEGIN:numbers" in sheet.group(1)),
        "Deviations and Limitations present; Numbers Sheet is a Phase 10 deliverable" if not (sheet and "BEGIN:numbers" in sheet.group(1)) else "all sections present")
    figs = [n for n in ("F1_architecture", "F2_error_vs_shots", "F3_quality_vs_shots", "F4_quality_vs_N", "F5_latency_vs_N", "F6_overlap_rbo_vs_shots",
                        "F7_pareto_hallucination", "F8_outcome_taxonomy", "F9_hallucination_by_gold_in_context", "F10_concurrency")
            if (ROOT / f"results/figures/{n}.png").exists() and (ROOT / f"results/figures/{n}.csv").exists()]
    readme = (ROOT / "README.md").exists()
    add("README complete; figures F1-F10 with CSVs", readme and len(figs) == 10, f"figures with CSV {len(figs)}/10; README.md {'present' if readme else 'missing (Phase 10 deliverable)'}")
    com = git_phase_commits()
    done = sorted({int(re.match(r"(?:fix\()?phase-(\d+)", s).group(1)) for _, _, s in com})
    order_ok = done == list(range(len(done)))
    add("Every phase 0-10 was committed (by the human) before the next began", order_ok and done == list(range(11)),
        f"phase commits found for {done} in order={order_ok}, authors {sorted({a for _, a, _ in com})}; phases {[i for i in range(11) if i not in done]} pending")
    spd = [ln.strip() for ln in findings.splitlines() if re.search(r"speed-?up", ln, re.I)]
    neg = [ln for ln in spd if not re.search(r"\b(no|not|never|nothing|cannot|without)\b", ln, re.I)]
    defs = findings.count("means a retrieval stage whose similarity scores are obtained by classically simulating")
    add("No claim of quantum speedup anywhere; terminology defined once", not neg and defs == 1, f"{len(spd)} lines mention speedup, all negated: {not neg}; definition occurs {defs}x")
    return rows


def phase9_block(run: Path) -> tuple[str, list[list]]:
    idx: list[list] = []
    L = [f"Run `{run.name}` - manifest: `{rel(run / 'run_manifest.json')}`.", ""]
    cr = run / "clean_room_summary.json"
    if cr.exists():
        c = js(cr)
        rows = rd(run / "clean_room.csv")
        env = c["environment"]
        L += [f"**9.1 Clean-room reproduction** (`{rel(cr)}`, per-artifact rows `{rel(run / 'clean_room.csv')}`, logs in `{rel(run)}/logs/`): fresh `git clone` of commit `{c['clone_of_commit'][:10]}`, "
              f"run with the pinned interpreter ({env['locked_packages']} locked packages, {len(env['mismatches'])} version mismatches vs `requirements.lock`). "
              f"{c['comparisons']} comparisons: {c['identical']} byte-identical, {c['equal_ignoring_timing']} equal after ignoring timing / run-id fields, "
              f"{c.get('equal_ignoring_line_endings', 0)} equal after normalising CRLF line endings (git checkout on Windows), {c['different']} different, {c['missing']} missing. "
              f"Small config: {c['small_config']}. Excluded: {'; '.join(c['excluded'])}. Wall time {c['total_seconds'] / 60:.1f} min.", ""]
        by = {}
        for r in rows:
            s = by.setdefault(r["stage"], {"n": 0, "ok": 0, "bad": []})
            s["n"] += 1
            s["ok"] += r["status"] in OK_STATUS
            if r["status"] not in OK_STATUS:
                s["bad"].append(r["artifact"])
        L += [md_table(["Stage", "Artifacts compared", "Reproduced", "Not reproduced"], [[k, v["n"], v["ok"], ", ".join(v["bad"]) or "-"] for k, v in by.items()]), ""]
        idx.append(["P9-1", 9, f"Clean room: {reproduced(c)}/{c['comparisons']} artifacts reproduced, {c['different']} different", rel(cr)])
    na = run / "number_audit.json"
    if na.exists():
        n = js(na)
        L += [f"**9.4 Numbers audit** (`{rel(na)}`, `scripts/check_numbers.py`): {n['generated_blocks_checked']} generated blocks re-rendered from the artifacts, not reproducible: {n['generated_blocks_not_reproducible'] or 'none'}; "
              f"{n['artifact_paths_checked']} quoted artifact paths, missing: {n['missing_paths'] or 'none'}; hand-authored text: {n['hand_numbers_allowed_design_constants']} design-constant numbers, "
              f"{len(n['unflagged_hand_numbers'])} unlabelled hand-typed numbers. Passed: **{n['passed']}**. (The Manuscript Numbers Sheet itself is a Phase 10 deliverable and will be added to this audit.)", ""]
        idx.append(["P9-2", 9, f"Numbers audit passed: {n['passed']}", rel(na)])
    xml = run / "pytest_junit.xml"
    if xml.exists():
        r = ET.parse(xml).getroot()
        ts = r if r.tag == "testsuite" else r.find("testsuite")
        tot, fail, err, skip = (int(ts.get(x, 0)) for x in ("tests", "failures", "errors", "skipped"))
        L += [f"**9.2 / 9.3 pytest** (whole suite, incl. determinism tests in `tests/test_phase9.py`: same seed -> identical quantum-sim rankings for shortlist and full scan; "
              f"different seeds -> different rankings at low S and convergence to the classical order at very high S; seed-to-seed variance of the estimator matches sqrt((1 - c^4)/S); "
              f"stored rankings: seeds differ at S=64 and coincide with the classical list at S=inf): {tot} tests, {fail} failures, {err} errors, {skip} skipped (`{rel(xml)}`).", ""]
        idx.append(["P9-3", 9, f"pytest: {tot - fail - err - skip}/{tot} passed", rel(xml)])
    cl = checklist()
    L += ["**9.6 Acceptance checklist (plan section 9)**, each item evaluated by `scripts/report_phase9.py` on the artifacts; unticked items are pending or failed, as stated.", "",
          md_table(["", "Item", "Evidence"], cl), ""]
    idx.append(["P9-4", 9, f"Acceptance checklist: {sum(r[0] == '[x]' for r in cl)}/{len(cl)} ticked", rel(run)])
    L += ["**Manuscript hook**: Section 3 of FINDINGS (Headline Findings) feeds chapter sections 7-10 and 12; the checklist and clean-room result support the reproducibility statement (Section 5).", ""]
    return "\n".join(L), idx


REPRO = """```
python tasks.py setup                 # venv + pinned requirements.lock
python tasks.py env data bench        # Phase 0: environment, SQuAD download + checksums, generator gate (needs Ollama)
python tasks.py phase1                # corpus, ladder, eval set, embeddings (~15 min CPU), ground truth
python tasks.py phase2 phase3 phase4  # FAISS baseline, SWAP-test arm + validation, retrieval-only experiments
python tasks.py phase5                # RAG generation (resumable, hours on CPU; cached), HHEM judging, analysis
python tasks.py phase6                # Docker Desktop running, Ollama idle: containers, HTTP latency, concurrency
python tasks.py phase7 phase8         # tradeoff synthesis; robustness / NLI judge (stop Ollama first)
python tasks.py phase9                # clean-room reproduction, numbers audit, tests, headline findings
python tasks.py figures report        # figures (PNG + CSV) and FINDINGS.md blocks
```"""
