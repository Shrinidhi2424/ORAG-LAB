"""Phase 10: documentation and manuscript handoff. Reads artifacts only; nothing is measured.

Usage: python scripts/run_phase10.py --run-id <id>
Outputs (results/phase10/<run_id>/, immutable): numbers_sheet.csv (every number quoted in the chapter, one artifact path each),
methods_facts.csv (every parameter of the method), claims.csv (claims the data supports / does not support), figure_inventory.csv.
Also writes docs/manuscript_source_notes.md, docs/seminar_summary.md and docs/seminar/ (6-8 key figures and tables), and
dist/qrag-lab-results.zip (archive of results/, git-ignored). All numbers come from the artifacts through the extractors below.
"""
from __future__ import annotations

import argparse
import csv
import json
import shutil
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from qrag.manifest import write_run_manifest  # noqa: E402

NS = ["1000", "2000", "5000", "10000", "all"]
NLAB = {"1000": "1000", "2000": "2000", "5000": "5000", "10000": "10000", "all": "all (20958)"}


def cur(phase: str) -> Path:
    return ROOT / "results" / phase / (ROOT / "results" / phase / ".current_run").read_text(encoding="utf-8").strip()


def rd(p: Path) -> list[dict]:
    return list(csv.DictReader(p.open(encoding="utf-8")))


def js(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def rel(p: Path) -> str:
    return p.relative_to(ROOT).as_posix()


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(dict.fromkeys(k for r in rows for k in r)))
        w.writeheader()
        w.writerows(rows)


def f(x, d=3) -> str:
    return f"{float(x):.{d}f}"


_CI_COLS = {"hallucination_rate": ("hall_lo", "hall_hi"), "ungrounded_answer_rate": ("ungr_lo", "ungr_hi")}


def ci(r: dict, m: str, d=3) -> str:
    lo, hi = _CI_COLS.get(m, (m + "_lo", m + "_hi"))
    return f"{f(r[m], d)} [{f(r[lo], d)}, {f(r[hi], d)}]"


class Sheet:
    def __init__(self, prefix: str):
        self.prefix, self.rows = prefix, []

    def add(self, section: str, quantity: str, value, artifact: Path, note: str = "") -> str:
        i = f"{self.prefix}{len(self.rows) + 1:03d}"
        self.rows.append({"id": i, "chapter_section": section, "quantity": quantity, "value": str(value), "artifact": rel(artifact), "note": note})
        return i

    def get(self, i: str) -> str:
        return next(r["value"] for r in self.rows if r["id"] == i)


def numbers_sheet() -> Sheet:
    S = Sheet("N")
    p0, p1, p2, p3, p4, p5, p6, p7, p8, p9 = (cur(f"phase{i}") for i in range(10))
    env, man = js(p0 / "env.json"), js(p0 / "run_manifest.json")
    # ------------------------------------------------------------------ 5 experimental setup
    cs, emb = js(p1 / "corpus_stats.json"), js(p1 / "embed_info.json")
    S.add("5", "Unique paragraphs after de-duplication", cs["unique_paragraphs"], p1 / "corpus_stats.json")
    S.add("5", "Raw paragraphs train / dev", f"{cs['raw']['train']} / {cs['raw']['dev']}", p1 / "corpus_stats.json")
    S.add("5", "Exact duplicate paragraphs dropped", cs["duplicates_dropped"], p1 / "corpus_stats.json")
    S.add("5", "Evaluation questions (seed 42) / distinct gold paragraphs", f"{cs['n_eval']} / {cs['distinct_gold_paragraphs']}", p1 / "corpus_stats.json")
    S.add("5", "Corpus ladder sizes", ", ".join(str(v) for v in cs["ladder_sizes"].values()), p1 / "corpus_stats.json", "nested; gold paragraphs in every rung")
    S.add("5", "Words per paragraph mean / median / p95 / max", " / ".join(f"{cs['words_per_paragraph'][k]:.1f}" for k in ("mean", "median", "p95", "max")), p1 / "corpus_stats.json")
    S.add("5", "Embedding model and revision", f"{emb['model']} @ {emb['revision']}", p1 / "embed_info.json")
    S.add("5", "Embedding dimension / padded dimension / max sequence length", f"{emb['dim']} / {emb['padded_dim']} / {emb['max_seq_length']}", p1 / "embed_info.json")
    S.add("5", "Paragraphs truncated by the embedder (count, share)", f"{emb['paragraphs_truncated']} ({f(emb['paragraphs_truncated_frac'])})", p1 / "embed_info.json")
    S.add("5", "Paragraph embedding time (s) and rate (paragraphs/s)", f"{emb['paragraph_embed_s']:.1f} s, {emb['paragraphs_per_s']:.1f}/s", p1 / "embed_info.json")
    gb = js(p0 / "generator_bench_summary.json")
    g = next(m for m in gb["models"] if m["model"] == gb["chosen"])
    S.add("5", "Chosen generator, quantisation, digest", f"{g['model']}, {g['ollama_details'].split('quantization_level=')[1].strip(chr(39))}, {g['digest'][:12]}", p0 / "generator_bench_summary.json")
    S.add("5", "Generator gate: median s/query, p95 s, tokens/s, prompt tokens", f"{g['median_wall_s']} / {g['p95_wall_s']} / {g['median_tokens_per_s']} / {g['median_prompt_tokens']}", p0 / "generator_bench_summary.json")
    S.add("5", "Generation options", json.dumps(gb["options"]), p0 / "generator_bench_summary.json")
    S.add("5", "HHEM judge model and revision", f"{js(p5 / 'judge_info.json')['model']} @ {js(p5 / 'judge_info.json')['revision'][:12]}", p5 / "judge_info.json")
    S.add("5", "Host CPU / RAM / OS", f"{env['cpu_model']} / {env['host']['ram_total_bytes'] / 1e9:.2f} GB / {env['host']['os']}", p0 / "env.json")
    S.add("5", "Key package versions (numpy, faiss-cpu, torch, qiskit, qiskit-aer)", ", ".join(f"{k} {env['packages'][k]}" for k in ("numpy", "faiss-cpu", "torch", "qiskit", "qiskit-aer")), p0 / "env.json")
    # ------------------------------------------------------------------ 6 estimator validation
    val, t6 = js(p3 / "validation.json"), js(p3 / "t6_resource_counts.json")
    for tier in ("A", "B"):
        t = val[f"tier{tier}"]
        S.add("6", f"Tier {tier} error at S=4096: bias / MAE / RMSE / theory RMSE",
              f"{t['bias']:+.5f} / {t['mae']:.4f} / {t['rmse']:.4f} / {val['theory_rmse']:.4f}", p3 / "validation.json")
    S.add("6", "Two-sample KS Tier A vs Tier B (statistic, p)", f"{val['ks_two_sample_z_tierA_vs_tierB']['stat']:.3f}, {val['ks_two_sample_z_tierA_vs_tierB']['p']:.3f}", p3 / "validation.json")
    for tier in ("A", "B"):
        s = val[f"loglog_slope_tier{tier}"]
        S.add("6", f"Log-log slope of RMSE vs shots, Tier {tier} (theory -0.5)", f"{s['slope']:.3f}", p3 / "validation.json")
    S.add("6", "SWAP circuit with generic state preparation: qubits / depth / 2q gates / 1q gates", f"{t6['full_with_state_prep']['qubits']} / {t6['full_with_state_prep']['depth']} / {t6['full_with_state_prep']['two_qubit_gates']} / {t6['full_with_state_prep']['one_qubit_gates']}", p3 / "t6_resource_counts.json")
    S.add("6", "SWAP-test core alone: depth / 2q gates", f"{t6['swap_test_core']['depth']} / {t6['swap_test_core']['two_qubit_gates']}", p3 / "t6_resource_counts.json")
    tA, te = js(p3 / "tierA_timing.json"), js(p3 / "tierA_e2e_summary.json")
    S.add("6", "Tier A simulation cost per circuit (s), end-to-end subset", f"{te['seconds_per_circuit']:.3f}", p3 / "tierA_e2e_summary.json", "classical simulation cost, not quantum time")
    neg = js(p3 / "negative_cosine_audit.json")
    S.add("6", "Negative cosines in exact top-10 at every rung", sum(v["negative_cos_in_exact_top10"] for v in neg.values()), p3 / "negative_cosine_audit.json")
    thr = {r["N"]: r for r in rd(p3 / "shot_thresholds.csv") if r["M"] == "50" and r["tie"] == "classical"}
    S.add("6", "Smallest S with Hit@3 indistinguishable from classical (paired CI), N = 1000/2000/5000/10000/all", " / ".join(thr[n]["min_shots_Hit@3_indistinguishable"] for n in NS), p3 / "shot_thresholds.csv")
    # ------------------------------------------------------------------ 7 retrieval
    main = rd(p4 / "main_table.csv")
    for n in NS:
        for arm, flt in (("Flat", lambda r: r["arm"] == "Flat"), ("IVF nprobe 16", lambda r: r["arm"].startswith("IVF"))):
            r = next(x for x in main if x["N"] == n and flt(x))
            S.add("7", f"{arm}, N={NLAB[n]}: Hit@1 / Hit@3 [CI] / MRR@10", f"{f(r['Hit@1'])} / {ci(r, 'Hit@3')} / {f(r['MRR@10'])}", p4 / "main_table.csv")
        for s in ("256", "1024", "4096", "16384"):
            r = next(x for x in main if x["N"] == n and x["arm"] == "Quantum-sim" and x["S"] == s)
            S.add("7", f"Quantum-sim M=50 S={s}, N={NLAB[n]}: Hit@3 [CI] / MRR@10 / Overlap@10 / RBO", f"{ci(r, 'Hit@3')} / {f(r['MRR@10'])} / {f(r['Overlap@10'])} / {f(r['RBO'])}", p4 / "main_table.csv")
    lat = rd(p4 / "latency_summary.csv")
    for n in NS:
        a = next(r for r in lat if r["arm"] == "flat" and r["N"] == n)
        b = next(r for r in lat if r["arm"] == "ivf" and r["N"] == n)
        c = next(r for r in lat if r["arm"] == "qsim" and r["N"] == n and r["M"] == "50" and float(r["S"]) == 1024)
        d = next(r for r in lat if r["arm"] == "qsim" and r["N"] == n and r["M"] == "full" and float(r["S"]) == 1024)
        S.add("7/9", f"Retrieval latency median / p95 ms, N={NLAB[n]}: Flat | IVF | quantum-sim M=50 S=1024 | full scan S=1024",
              " | ".join(f"{f(x['median_ms'])} / {f(x['p95_ms'])}" for x in (a, b, c, d)), p4 / "latency_summary.csv", "in-process, k=10, embedding excluded; quantum-sim = emulated-estimator latency")
    for r in rd(p4 / "latency_slopes.csv"):
        if r["series"].startswith(("Flat", "IVF", "Quantum-sim shortlist M=50", "Quantum-sim full scan, S=1024")):
            S.add("9", f"Latency exponent b: {r['series']}", f"{f(r['slope_b'], 2)} [{f(r['slope_lo'], 2)}, {f(r['slope_hi'], 2)}]", p4 / "latency_slopes.csv")
    fs = js(p4 / "failure_summary.json")
    S.add("7", "Failure analysis N=all S=256: gold in classical / quantum top-3; dropped / gained", f"{fs['gold_in_classical_top_k']} / {fs['gold_in_quantum_top_k']}; {fs['dropped_by_quantum']} / {fs['gained_by_quantum']} of {fs['queries']}", p4 / "failure_summary.json")
    tests = rd(p4 / "tests.csv")
    S.add("7", "Pre-registered retrieval tests significant after Holm", f"{sum(r['significant_at_0.05_holm'] == 'True' for r in tests)} of {len(tests)}", p4 / "tests.csv")
    q2 = next(r for r in rd(p2 / "latency_summary.csv") if r["N"] == "all") if (p2 / "latency_summary.csv").exists() else None
    S.add("9", "Query embedding latency, batch 1: median / p95 ms", f"{f(js(p2 / 'query_embed_summary.json')['median_ms'], 1)} / {f(js(p2 / 'query_embed_summary.json')['p95_ms'], 1)}", p2 / "query_embed_summary.json")
    for r in rd(p2 / "build.csv"):
        if r["N"] == "all":
            S.add("9", f"Index size at N=all, {r['arm']} (bytes)", r["index_bytes"], p2 / "build.csv")
    # ------------------------------------------------------------------ 8 hallucination
    out = rd(p5 / "outcomes_by_arm.csv")
    for r in out:
        ungr = ci(r, "ungrounded_answer_rate") if r["ungrounded_answer_rate"] not in ("", None) else "-"
        S.add("8", f"{r['arm']}: correct / hallucination rate / abstention / ungrounded [CI]", f"{ci(r, 'correct_rate')} / {ci(r, 'hallucination_rate')} / {ci(r, 'abstention_rate')} / {ungr}", p5 / "outcomes_by_arm.csv", f"n={r['n']}, threshold {r['threshold']}")
    cc = js(p5 / "controls_check.json")
    S.add("8", "Controls: oracle / closed-book / random correct rate", f"{cc['oracle_correct']:.3f} / {cc['closed_book_correct']:.3f} / {cc['random_correct']:.3f}", p5 / "controls_check.json")
    for r in rd(p5 / "paired_tests.csv"):
        if r["family"] == "T-c":
            S.add("8", f"T-c hallucination, N=all S={r['S']} seed 0: diff [CI], McNemar p, Holm p", f"{float(r['diff']):+.3f} [{float(r['diff_lo']):+.3f}, {float(r['diff_hi']):+.3f}], {float(r['p_mcnemar']):.4f}, {float(r['p_holm_T-c']):.4f}", p5 / "paired_tests.csv")
    reg = js(p5 / "regeneration_check.json")
    S.add("11", "Regeneration check: identical text / same correct label / same abstain label", f"{reg['identical_text']} / {reg['same_correct_label']} / {reg['same_abstain_label']} of {reg['n_sampled']}", p5 / "regeneration_check.json")
    S.add("11", "Answers truncated by the 48-token limit", sum(r["done_reason"] == "length" for r in rd(p5 / "judged.csv")), p5 / "judged.csv", "of all stored answers")
    so = rd(p8 / "seed_robustness_outcomes.csv")
    for r in so:
        S.add("8", f"Seed robustness S=256 N={NLAB[r['N']]}: rates seeds 0/1/2, sd, flip rate", f"{f(r['hall_rate_seed0'])} / {f(r['hall_rate_seed1'])} / {f(r['hall_rate_seed2'])}, sd {f(r['hall_rate_sd_seeds'])}, flip {f(r['flip_rate_hall_indicator'])}", p8 / "seed_robustness_outcomes.csv")
    nli = js(p8 / "nli_summary.json")
    S.add("8", "NLI cross-check vs HHEM at 0.5: agreement / kappa / Spearman", f"{f(nli['by_threshold']['0.5']['agreement'])} / {f(nli['by_threshold']['0.5']['kappa'])} / {f(nli['spearman_hhem_vs_nli'])}", p8 / "nli_summary.json", f"{nli['answers_scored']} answers")
    au = js(p8 / "audit_agreement.json")
    S.add("11", "Hand audit: rows labelled", f"{au['rows_labelled']} of {au['rows']}", p8 / "audit_agreement.json", au["status"])
    # ------------------------------------------------------------------ 9 cloud
    h = {(r["profile"], r["arm"], r["N"]): r for r in rd(p6 / "latency_summary.csv")}
    for prof in ("small", "medium", "large"):
        for arm in ("classical", "quantum"):
            S.add("9", f"HTTP E2E median / p95 ms, {prof} profile, {arm}, N=1000 | 5000 | all", " | ".join(f"{f(h[(prof, arm, n)]['e2e_median_ms'], 1)} / {f(h[(prof, arm, n)]['e2e_p95_ms'], 1)}" for n in ("1000", "5000", "all")), p6 / "latency_summary.csv", "in-network client; embedding included")
    r = h[("medium", "classical", "all")]
    S.add("9", "Medium profile, classical, N=all: embed compute / embed overhead / retrieve compute / client-orchestrator overhead (ms)", f"{f(r['embed_compute_median_ms'], 1)} / {f(r['embed_service_overhead_median_ms'], 1)} / {f(r['retrieve_compute_median_ms'], 1)} / {f(r['client_to_orchestrator_overhead_median_ms'], 1)}", p6 / "latency_summary.csv")
    conc = rd(p6 / "concurrency.csv")
    for key in dict.fromkeys((r["profile"], r["arm"]) for r in conc):
        sel = [r for r in conc if (r["profile"], r["arm"]) == key]
        peak = {c: sorted(float(r["throughput_rps"]) for r in sel if r["clients"] == c) for c in ("1", "4", "16")}
        S.add("9", f"Throughput req/s (median of 3 runs), {key[0]} {key[1]}, 1 / 4 / 16 clients", " / ".join(f"{peak[c][len(peak[c]) // 2]:.1f}" for c in ("1", "4", "16")), p6 / "concurrency.csv", f"errors {sum(float(r['errors']) for r in sel):.0f} of {sum(float(r['requests']) for r in sel):.0f}")
    mem = rd(p6 / "memory.csv")
    for svc in ("embedder", "retriever-classical", "retriever-quantum-sim"):
        r = next(x for x in mem if x["profile"] == "medium" and x["service"] == svc)
        S.add("9", f"Container memory, medium profile, {svc}: idle / peak / limit MB", f"{f(r['idle_mb'], 1)} / {f(r['peak_during_load_mb'], 1)} / {f(r['limit_mb'], 0)}", p6 / "memory.csv")
    for r in rd(p6 / "startup.csv"):
        S.add("9", f"Stack start-up, {r['profile']} profile: compose up s / until all healthy s", f"{f(r['compose_up_s'], 1)} / {f(r['extra_wait_until_all_ready_s'], 1)}", p6 / "startup.csv")
    # ------------------------------------------------------------------ 10 tradeoff
    ph, pm = rd(p7 / "pareto_hallucination.csv"), rd(p7 / "pareto_retrieval_miss.csv")
    S.add("10", "Pareto (hallucination vs latency): non-dominated / robustly dominated / points", f"{sum(r['non_dominated'] == 'True' for r in ph)} / {sum(r['robustly_dominated'] == 'True' for r in ph)} / {len(ph)}", p7 / "pareto_hallucination.csv")
    S.add("10", "Pareto (retrieval miss vs latency, IVF incl.): non-dominated / robustly dominated / points", f"{sum(r['non_dominated'] == 'True' for r in pm)} / {sum(r['robustly_dominated'] == 'True' for r in pm)} / {len(pm)}", p7 / "pareto_retrieval_miss.csv")
    for r in rd(p7 / "break_even_hallucination.csv"):
        S.add("10", f"Break-even S (hallucination), N={NLAB[r['N']]}: McNemar p>=0.05 / CI within +-0.05 / +-0.075 / +-0.10", " / ".join(r[k] or "not reached" for k in ("min_S_McNemar_p_ge_0.05_and_all_larger", "min_S_CI_within_pm0.05", "min_S_CI_within_pm0.075", "min_S_CI_within_pm0.1")), p7 / "break_even_hallucination.csv")
    for r in rd(p7 / "break_even_retrieval.csv"):
        if r["level"].startswith("retrieval Hit@3"):
            S.add("10", f"Break-even S (Hit@3), N={NLAB[r['N']]}: CI contains 0 / within +-0.05 / +-0.075 / +-0.10", " / ".join(r[k] or "not reached" for k in ("min_S_CI_contains_0_and_all_larger", "min_S_CI_within_pm0.05", "min_S_CI_within_pm0.075", "min_S_CI_within_pm0.1")), p7 / "break_even_retrieval.csv")
    for r in rd(p7 / "break_even_modelled_cost.csv"):
        if r["S"] in ("1024", "4096"):
            S.add("10", f"MODELLED cost S={r['S']}: circuits / shots (M=50); 2q-gate executions (full circuit); shots full scan N=all", f"{r['MODELLED_circuits_per_query_shortlist']} / {int(float(r['MODELLED_shots_per_query_shortlist'])):,}; {float(r['MODELLED_2q_gate_exec_full_circuit_shortlist']):.3g}; {int(float(r['MODELLED_shots_per_query_full_scan_N_all'])):,}", p7 / "break_even_modelled_cost.csv", "MODELLED, not wall-clock quantum time")
    # ------------------------------------------------------------------ reproducibility
    c9 = js(p9 / "clean_room_summary.json")
    S.add("5/11", "Clean-room reproduction: artifacts compared / reproduced / different", f"{c9['comparisons']} / {c9['identical'] + c9['equal_ignoring_timing'] + c9.get('equal_ignoring_line_endings', 0)} / {c9['different']}", p9 / "clean_room_summary.json")
    return S


def methods_facts() -> Sheet:
    M = Sheet("M")
    p0, p1, p3, p4, p5, p6, p7 = (cur(f"phase{i}") for i in (0, 1, 3, 4, 5, 6, 7))
    man = {i: js(cur(f"phase{i}") / "run_manifest.json") for i in (0, 1, 2, 3, 4, 6, 7, 8)}
    run = cur("phase3") / "run_manifest.json"
    cfg = lambda i: man[i]["config"]  # noqa: E731
    M.add("5", "Corpus / eval set / ladder seeds", json.dumps(man[1]["seeds"]), p1 / "run_manifest.json")
    M.add("5", "Ladder rungs", "1000, 2000, 5000, 10000, all (20958); nested; all 275 gold paragraphs in every rung", p1 / "corpus_stats.json")
    M.add("5", "Retrieval metrics", "Hit@{1,3,5,10}, P@k, MRR@10, nDCG@10, Overlap@k, RBO p=0.9 (A.4)", p1 / "run_manifest.json")
    M.add("5", "Statistics", "bootstrap 95% CIs 10,000 resamples; exact McNemar; paired bootstrap; Holm within family (A.6)", p4 / "tests.csv")
    M.add("6", "Quantum-inspired estimator", "SWAP test, c2_hat = 2k/S - 1, k ~ Binomial(S, (1+c^2)/2), clipped to [0,1]; ties by classical score", p3 / "run_manifest.json")
    M.add("6", "Shot grid / seeds / shortlist sizes", "S in {64,128,256,512,1024,2048,4096,8192,16384}; 5 seeds; M in {20, 50, 100, full}", p3 / "run_manifest.json")
    M.add("6", "Tier A circuit", "19 qubits (1 ancilla + 2 x 9), 384-d padded to 512, set_statevector + H, 9 CSWAP, H, measure; Aer statevector", p3 / "t6_resource_counts.json")
    M.add("5", "Retrieval baseline", "FAISS IndexFlatIP on L2-normalised vectors; IVFFlat nlist=round(sqrt N), nprobe 16 (>=0.95 Overlap@10), k-means seed 42", p0 / "run_manifest.json")
    M.add("5", "Prompt", "Appendix A.5 system + context template; k=3 paragraphs; closed-book prompt differs (D-5.1)", p5 / "build_info.json")
    bi = js(p5 / "build_info.json")
    M.add("5", "Decoding", json.dumps(bi["options"]), p5 / "build_info.json")
    M.add("5", "Generation questions / run matrix", f"{bi['questions']} questions (first 200 of 300); {bi['records']} records; {bi['unique_prompts_P0']} unique P0 prompts + {bi['unique_prompts_P1_extra']} P1", p5 / "build_info.json")
    M.add("5", "Hallucination definitions", "hallucination rate = (hallucinated + misread) / all; ungrounded-answer rate = non-abstained with HHEM < threshold; thresholds 0.3/0.5/0.7, default 0.5", p5 / "judge_info.json")
    M.add("5", "Hardware", "HP 15s-dr3xxx, i5-1135G7 (4C/8T), 8 GB RAM, CPU only, Windows 11", p0 / "env.json")
    M.add("5", "Latency protocol", "batch 1, 10 warm-up discarded, 100 timed queries, 5 repeats, conditions shuffled per repeat, 1 thread, Balanced power plan, CPU temperature not monitored", p4 / "hygiene.json")
    M.add("4", "Cloud-native stack", "FastAPI services: embedder, retriever-classical, retriever-quantum-sim, generator-gateway, orchestrator; docker compose; profiles 1 CPU/1.5 GB, 2/2, 4/3; WSL2 cap 3 GB / 4 CPUs", p6 / "run_manifest.json")
    M.add("9", "HTTP protocol", "in-network load generator, 10 warm-up, 100 timed, 5 repeats; concurrency 1/4/16 clients x 300 requests x 3 repeats", p6 / "latency_summary.csv")
    M.add("10", "Pareto / break-even rules", "dominance within each N; robust dominance needs disjoint CI / repeat ranges; equivalence margins 0.05, 0.075, 0.10 (post hoc)", p7 / "synthesis_meta.json")
    M.add("5", "Pinned environment", "requirements.lock; git commit hash in every run_manifest.json", p0 / "run_manifest.json")
    return M


CLAIMS = [
    ("supported", "RQ1", "At low shot budgets (S=64) the simulated quantum-inspired retrieval increases hallucination relative to exact cosine, with the generator fixed (Holm-significant at N=all).", "N-T-c rows; Table T5c", "moderate"),
    ("supported", "RQ1", "The hallucination effect is mediated by retrieval: outcomes split almost entirely by whether the gold paragraph reached the context.", "mediation table / F9", "moderate"),
    ("supported", "RQ1", "At S >= 1024 no difference in hallucination is detectable with 200 questions.", "T-c, T7d", "weak-moderate (absence of evidence at this n)"),
    ("supported", "RQ2", "The emulated estimator gives no retrieval-latency benefit: the shortlist arm executes the exact search first, and full-scan estimation is slower than Flat.", "T4b", "strong"),
    ("supported", "RQ2", "Over HTTP the query embedding and service hops dominate retrieval time for both arms; generation dominates the whole request.", "T4c", "strong"),
    ("supported", "RQ3", "At a fixed shot budget the Hit@3 gap is larger at the full corpus than at 1k paragraphs, and the shots needed for indistinguishable Hit@3 grow with N.", "T3, shot thresholds", "moderate"),
    ("supported", "RQ3", "The Tier B emulator reproduces the Tier A circuit statistics (mean, variance, 1/sqrt(S) error scaling).", "T6, F2", "strong on mean / variance; weaker on distribution shape"),
    ("supported", "RQ4", "Exact Flat retrieval is on the Pareto front at every corpus size; the quantum-sim arm can at best match it; IVF is the practical latency option.", "T7b, T7c, F7, F7b", "moderate"),
    ("supported", "Method", "The SWAP-test top-3 differs from the exact top-3 mainly for queries whose gold paragraph has a small score margin; a measurable share of top-1 results changes across seeds even at 1024 shots.", "T8b, failure analysis", "moderate"),
    ("not_supported", "Speed", "Any quantum speedup, advantage, or lower latency. The arm is a classical simulation; modelled shots and gates are counts, not time.", "-", "-"),
    ("not_supported", "Hardware", "Anything about real quantum hardware, noise, QRAM or state-preparation cost.", "-", "-"),
    ("not_supported", "Generality", "Results for other corpora (multi-hop, domain-specific), other embedders, or larger / better-calibrated generators (single dataset, embedder, 1.5B model).", "-", "-"),
    ("not_supported", "Scale", "Latency or memory scaling beyond about 21k paragraphs; the exponent CIs overlap between arms.", "-", "-"),
    ("not_supported", "Cloud", "Performance of a real cloud deployment (containers emulated on one shared laptop; free-tier cloud rerun not done).", "-", "-"),
    ("not_supported", "Faithfulness", "Validated faithfulness: the HHEM judge was not checked by humans (audit pending) and agrees only weakly with the NLI cross-check.", "-", "-"),
    ("not_supported", "Equivalence", "That the quantum-sim arm is equivalent to classical at S >= 1024; margins are post hoc and n=200.", "-", "-"),
    ("not_supported", "Zardini", "Any result for the Zardini-style quantum k-NN estimator (not implemented, D-3.3); Q-L2S and other extensions (E1-E5) were not run.", "-", "-"),
]

SEMINAR = [("F1_architecture", "System architecture"), ("F2_error_vs_shots", "Estimator validation"), ("F4_quality_vs_N", "Retrieval quality vs N"),
           ("F5_latency_vs_N", "Retrieval latency vs N"), ("F8_outcome_taxonomy", "Outcome taxonomy"), ("F9_hallucination_by_gold_in_context", "Mediation by gold-in-context"),
           ("F7_pareto_hallucination", "Pareto: hallucination vs latency"), ("F10_concurrency", "Concurrency")]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", required=True)
    a = ap.parse_args()
    out = ROOT / "results" / "phase10" / a.run_id
    out.mkdir(parents=True, exist_ok=True)
    N = numbers_sheet()
    M = methods_facts()
    write_csv(out / "numbers_sheet.csv", N.rows)
    write_csv(out / "methods_facts.csv", M.rows)
    write_csv(out / "claims.csv", [{"status": s, "area": ar, "claim": c, "evidence": e, "strength": st} for s, ar, c, e, st in CLAIMS])
    figs = []
    for i in list(range(1, 11)) + ["5b", "7b"]:
        stem = next((p.stem for p in (ROOT / "results" / "figures").glob(f"F{i}_*.png")), None)
        if stem:
            figs.append({"figure": f"F{i}", "png": f"results/figures/{stem}.png", "data_csv": f"results/figures/{stem}.csv", "dpi": 300,
                         "png_exists": (ROOT / f"results/figures/{stem}.png").exists(), "csv_exists": (ROOT / f"results/figures/{stem}.csv").exists()})
    write_csv(out / "figure_inventory.csv", figs)

    # ---- docs: source notes + seminar
    docs = ROOT / "docs"
    (docs / "seminar").mkdir(parents=True, exist_ok=True)
    nid = {r["quantity"]: r for r in N.rows}
    src = ["# Manuscript source notes", "",
           "Generated by `scripts/run_phase10.py` from the artifacts; not prose. Chapter sections follow the plan (section 7). All numbers are in `FINDINGS.md` section 8 (Manuscript Numbers Sheet); ids below refer to it.", ""]
    by_sec = {}
    for r in N.rows:
        for sec in r["chapter_section"].split("/"):
            by_sec.setdefault(sec, []).append(r)
    titles = {"4": "System design", "5": "Experimental setup", "6": "Results I: estimator validation and shot budget", "7": "Results II: retrieval quality and scalability",
              "8": "Results III: hallucination analysis", "9": "Results IV: latency, cloud overheads, concurrency", "10": "Discussion: tradeoffs", "11": "Limitations and threats to validity"}
    for sec in ("4", "5", "6", "7", "8", "9", "10", "11"):
        src += [f"## Section {sec} - {titles[sec]}", ""]
        src += [f"- {r['id']}: {r['quantity']} -> `{r['artifact']}`" for r in by_sec.get(sec, [])[:400]] or ["- (system design: see README architecture diagram and figure F1)"]
        src.append("")
    src += ["## Claims the data supports", ""] + [f"- [{ar}] {c} (evidence: {e}; strength: {st})" for s, ar, c, e, st in CLAIMS if s == "supported"]
    src += ["", "## Claims the data does NOT support (do not write these)", ""] + [f"- [{ar}] {c}" for s, ar, c, e, st in CLAIMS if s == "not_supported"]
    src += ["", "## Terminology", "", "Define once (FINDINGS section 3): quantum-inspired retrieval = a retrieval stage whose similarity scores come from classically simulating the SWAP test, including finite-shot statistics. No quantum hardware, no speedup.", ""]
    (docs / "manuscript_source_notes.md").write_text("\n".join(src), encoding="utf-8", newline="\n")

    def v(q_start: str) -> str:
        return next(r["value"] for r in N.rows if r["quantity"].startswith(q_start))

    summ = ["# QRAG-Lab: one-page results summary", "",
            "Quantum-inspired (SWAP-test, simulated) retrieval vs exact FAISS cosine in a containerised RAG pipeline on SQuAD v1.1. All numbers: `FINDINGS.md` section 8; run on a CPU-only 8 GB laptop.", "",
            "## What was done", "",
            f"- Corpus ladder 1k to {v('Unique paragraphs')} paragraphs; {v('Evaluation questions').split(' / ')[0]} evaluation questions on {v('Evaluation questions').split(' / ')[1]} gold paragraphs (200 for generation); embedder MiniLM-L6; generator qwen2.5:1.5b (CPU).",
            f"- Estimator validated against theory and a real 19-qubit Aer circuit: RMSE slope {v('Log-log slope of RMSE vs shots, Tier B')} (theory -0.5); circuit cost {v('Tier A simulation cost per circuit')} s per circuit (classical simulation).", "",
            "## Key results", "",
            f"- Retrieval (N=all, Hit@3): Flat {v('Flat, N=all (20958): Hit@1').split(' / ')[1]}; quantum-sim S=1024 {v('Quantum-sim M=50 S=1024, N=all (20958)').split(' / ')[0]}; S=16384 {v('Quantum-sim M=50 S=16384, N=all (20958)').split(' / ')[0]}.",
            f"- Hallucination (N=all, seed 0): rises at S=64 (difference {v('T-c hallucination, N=all S=64').rsplit(', ', 2)[0]}, Holm p = {v('T-c hallucination, N=all S=64').rsplit(', ', 1)[1]}), no detectable change at S=1024 (difference {v('T-c hallucination, N=all S=1024').rsplit(', ', 2)[0]}, Holm p = {v('T-c hallucination, N=all S=1024').rsplit(', ', 1)[1]}).",
            f"- Mechanism: gold paragraph in context decides the outcome; the 1.5B generator rarely abstains when it is missing.",
            f"- Latency (N=all, median / p95 ms): Flat | IVF | quantum-sim | full scan = {v('Retrieval latency median / p95 ms, N=all (20958)')}. No latency benefit; emulated latency only.",
            f"- Break-even: hallucination within +-0.075 from S = {v('Break-even S (hallucination), N=all (20958)').split(' / ')[2]}; Hit@3 CI contains 0 from S = {v('Break-even S (Hit@3), N=all (20958)').split(' / ')[0]}.",
            f"- Reproducibility: clean-room clone reproduced {v('Clean-room reproduction').split(' / ')[1]} of {v('Clean-room reproduction').split(' / ')[0]} artifacts.", "",
            "## Honest framing", "",
            "No quantum speedup is claimed; the quantum arm is a classical simulation and its latency is emulated. Single dataset, embedder and small generator; 200 generated questions; faithfulness judge not validated by humans yet.", "",
            "## Figures and tables for the seminar (copies in `docs/seminar/`)", ""]
    for stem, title in SEMINAR:
        for ext in ("png", "csv"):
            shutil.copyfile(ROOT / "results" / "figures" / f"{stem}.{ext}", docs / "seminar" / f"{stem}.{ext}")
        summ.append(f"- {title}: `docs/seminar/{stem}.png` (data `{stem}.csv`)")
    summ += ["- Tables: T3 main retrieval table, T5b outcome table, T7d break-even (FINDINGS.md sections 2 and 3)", ""]
    (docs / "seminar_summary.md").write_text("\n".join(summ), encoding="utf-8", newline="\n")

    # ---- archive of results/ (git-ignored dist/)
    dist = ROOT / "dist"
    dist.mkdir(exist_ok=True)
    zp = dist / "qrag-lab-results.zip"
    n_files = 0
    with zipfile.ZipFile(zp, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted((ROOT / "results").rglob("*")):
            if p.is_file() and "__pycache__" not in p.parts:
                z.write(p, p.relative_to(ROOT).as_posix())
                n_files += 1
        for extra in ("FINDINGS.md", "requirements.lock", "docs/manuscript_source_notes.md", "docs/seminar_summary.md"):
            z.write(ROOT / extra, extra)
    (out / "archive_info.json").write_text(json.dumps({"archive": "dist/qrag-lab-results.zip (git-ignored)", "files": n_files + 4, "bytes": zp.stat().st_size}, indent=2), encoding="utf-8")
    write_run_manifest(out, "phase10", a.run_id, seeds={"note": "no randomness; documentation only"},
                       config={"numbers_sheet_rows": len(N.rows), "methods_facts_rows": len(M.rows), "claims": len(CLAIMS)})
    print(f"numbers sheet {len(N.rows)} rows, methods facts {len(M.rows)}, claims {len(CLAIMS)}, archive {zp.stat().st_size / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
