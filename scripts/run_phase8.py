"""Phase 8: robustness, error analysis, threats to validity.

Usage: python scripts/run_phase8.py --run-id <id> [--steps seeds thresholds nli examples audit threats]
Outputs: results/phase8/<run_id>/ (R3). Consumes Phase 1-6 artifacts. Only the `nli` step runs a model (alternative judge,
needs Ollama stopped: RAM discipline H5). Every other step re-aggregates existing artifacts.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from qrag import judge as J  # noqa: E402
from qrag.manifest import write_run_manifest  # noqa: E402
from qrag.seed import set_global_seed  # noqa: E402
from qrag.stats import bootstrap_ci, mcnemar_exact  # noqa: E402

DATA = ROOT / "data"
NLI_REPO, NLI_REV = "cross-encoder/nli-deberta-v3-base", "6c749ce3425cd33b46d187e45b92bbf96ee12ec7"
NLI_CACHE = ROOT / "cache" / "nli"
THRESHOLDS = (0.3, 0.5, 0.7)
SEED_NS = ("5000", "all")
RET_S = (64, 256, 1024, 4096, 16384)


def cur(phase: str) -> Path:
    return ROOT / "results" / phase / (ROOT / "results" / phase / ".current_run").read_text(encoding="utf-8").strip()


def rd(p: Path) -> list[dict]:
    return list(csv.DictReader(p.open(encoding="utf-8")))


def read_jsonl(p: Path) -> list[dict]:
    with p.open(encoding="utf-8") as f:
        return [json.loads(x) for x in f if x.strip()]


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(dict.fromkeys(k for r in rows for k in r)))
        w.writeheader()
        w.writerows(rows)


def jdump(path: Path, obj) -> None:
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def b(x) -> bool:
    return x in (True, "True")


def load_judged() -> dict[str, list[dict]]:
    """judged.csv grouped by arm, sorted by question index; booleans / floats parsed."""
    by: dict[str, list[dict]] = {}
    for r in rd(cur("phase5") / "judged.csv"):
        for k in ("correct", "abstained", "gold_in_context"):
            r[k] = b(r[k])
        r["qi"] = int(r["qi"])
        r["hhem"] = None if r["hhem"] in ("", None) else float(r["hhem"])
        by.setdefault(r["arm"], []).append(r)
    for v in by.values():
        v.sort(key=lambda r: r["qi"])
    return by


def hall(r: dict) -> bool:
    """Hallucinated or misread = a confident wrong answer (A.4): not correct and not abstained."""
    return (not r["correct"]) and (not r["abstained"])


def kappa(a: np.ndarray, c: np.ndarray) -> float:
    a, c = np.asarray(a, bool), np.asarray(c, bool)
    po = float((a == c).mean())
    pe = float(a.mean() * c.mean() + (1 - a.mean()) * (1 - c.mean()))
    return 1.0 if pe == 1 else (po - pe) / (1 - pe)


# ------------------------------------------------------------------------------------------------ 8.1 seeds
def step_seeds(out: Path) -> None:
    J_ = load_judged()
    prompts = {(p["arm"], p["qi"]): p for p in read_jsonl(cur("phase5") / "prompts.jsonl")}
    tests = [r for r in rd(cur("phase5") / "paired_tests.csv") if r["metric"] == "hallucinated_or_misread" and r["S"] == "256"]
    rows = []
    for n in SEED_NS:
        arms = [f"quantum_N{n}_M50_S256_seed{s}_k3" for s in (0, 1, 2)]
        cl = J_[f"classical_N{n}_k3"]
        H = np.array([[hall(r) for r in J_[a]] for a in arms], float)  # (3, 200)
        G = np.array([[r["gold_in_context"] for r in J_[a]] for a in arms], float)
        ctx = [[tuple(prompts[(a, q)]["context_idx"]) for q in range(H.shape[1])] for a in arms]
        same_ctx = np.array([len({ctx[s][q] for s in range(3)}) == 1 for q in range(H.shape[1])])
        flip = (H.min(0) != H.max(0))
        gflip = (G.min(0) != G.max(0))
        rate = H.mean(1)
        row = {"N": n, "S": 256, "classical_hall_rate": float(np.mean([hall(r) for r in cl])),
               **{f"hall_rate_seed{s}": float(rate[s]) for s in range(3)}, "hall_rate_mean": float(rate.mean()), "hall_rate_sd_seeds": float(rate.std(ddof=1)),
               "hall_rate_range": float(rate.max() - rate.min()),
               "flip_rate_hall_indicator": float(flip.mean()), "n_questions": int(H.shape[1]), "flip_rate_gold_in_context": float(gflip.mean()),
               "frac_questions_context_list_identical_all_seeds": float(same_ctx.mean()),
               "hall_flips_with_gold_in_context_flip": int((flip & gflip).sum()), "hall_flips_with_gold_in_context_constant": int((flip & ~gflip).sum()),
               "always_hall_all_seeds": float((H.min(0) == 1).mean()), "never_hall_any_seed": float((H.max(0) == 0).mean()),
               "classical_hall_but_quantum_never": float(np.mean([hall(cl[q]) and H[:, q].max() == 0 for q in range(H.shape[1])]))}
        for s in range(3):
            t = next(x for x in tests if x["N"] == n and x["seed"] == str(s))
            row[f"diff_vs_classical_seed{s}"] = f"{float(t['diff']):+.3f} [{float(t['diff_lo']):+.3f}, {float(t['diff_hi']):+.3f}] p={float(t['p_mcnemar']):.4f}"
        rows.append(row)
    write_csv(out / "seed_robustness_outcomes.csv", rows)

    # retrieval-level seed stability (Phase 3 rankings are git-ignored; regenerate with `python tasks.py phase3`)
    rk_dir = cur("phase3") / "rankings"
    eval_set = json.loads((DATA / "eval_set.json").read_text(encoding="utf-8"))
    gold = np.array([q["gold_idx"] for q in eval_set])
    ret = []
    for n in SEED_NS:
        f = rk_dir / f"N{n}_M50_tieclassical.npz"
        if not f.exists():
            continue
        z = np.load(f)
        shots = list(z["shots"])
        for s in RET_S:
            top = z["top"][shots.index(s)]  # (seeds, Q, 10)
            hit = (top[:, :, :3] == gold[None, :, None]).any(-1)
            t1 = top[:, :, 0]
            sets = [[frozenset(top[sd, q, :3]) for q in range(top.shape[1])] for sd in range(top.shape[0])]
            set_unstable = np.array([len({sets[sd][q] for sd in range(top.shape[0])}) > 1 for q in range(top.shape[1])])
            per_seed = hit.mean(1)
            ret.append({"N": n, "S": s, "seeds": int(top.shape[0]), "Hit@3_mean": float(per_seed.mean()), "Hit@3_sd_seeds": float(per_seed.std(ddof=1)),
                        "frac_queries_Hit@3_unstable": float((hit.any(0) & ~hit.all(0)).mean()), "frac_queries_top1_unstable": float((t1.min(0) != t1.max(0)).mean()),
                        "frac_queries_top3_set_unstable": float(set_unstable.mean())})
    if ret:
        write_csv(out / "seed_robustness_retrieval.csv", ret)
    else:
        jdump(out / "seed_robustness_retrieval_SKIPPED.json", {"reason": "Phase 3 rankings not present locally (git-ignored); run `python tasks.py phase3`"})


# ------------------------------------------------------------------------------------------------ 8.2 thresholds
def step_thresholds(out: Path) -> None:
    J_ = load_judged()
    rows = []
    for a, rs in J_.items():
        if not a.startswith("quantum") or len(rs) != 200:
            continue
        r0 = rs[0]
        cl = J_.get(f"classical_N{r0['N']}_k3")
        if not cl:
            continue
        for t in THRESHOLDS:
            def ung(r):
                return (not r["abstained"]) and r["hhem"] is not None and r["hhem"] < t
            qa, ca = np.array([ung(r) for r in rs]), np.array([ung(r) for r in cl])
            n10, n01, p = mcnemar_exact(qa, ca)
            d, lo, hi = bootstrap_ci(qa.astype(float) - ca.astype(float))
            rows.append({"arm": a, "N": r0["N"], "S": r0["S"], "seed": r0["seed"], "threshold": t, "quantum_ungrounded_rate": float(qa.mean()),
                         "classical_ungrounded_rate": float(ca.mean()), "diff": d, "diff_lo": lo, "diff_hi": hi, "quantum_only": n10, "classical_only": n01, "p_mcnemar": p})
    write_csv(out / "threshold_sensitivity_tests.csv", rows)
    # headline hallucination does not depend on the threshold (A.4: uses correctness, abstention, gold-in-context only)
    tt = rd(cur("phase5") / "threshold_sweep.csv")
    inv = all(len({x["hallucination_rate"] for x in tt if x["arm"] == a}) == 1 for a in {x["arm"] for x in tt})
    jdump(out / "threshold_invariance.json", {"hallucination_rate_identical_across_thresholds_for_all_arms": inv, "source": "phase5 threshold_sweep.csv"})


# ------------------------------------------------------------------------------------------------ 8.2 NLI judge
def step_nli(out: Path) -> None:
    import psutil
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    J_ = load_judged()
    prompts = {(p["arm"], p["qi"]): p for p in read_jsonl(cur("phase5") / "prompts.jsonl")}
    texts = {}
    with (DATA / "paragraphs.jsonl").open(encoding="utf-8") as f:
        for line in f:
            p = json.loads(line)
            texts[p["idx"]] = p["text"]
    NLI_CACHE.mkdir(parents=True, exist_ok=True)
    items = []  # (arm, qi, paragraph idx, key, premise, hypothesis)
    for a, rs in J_.items():
        if prompts[(a, 0)]["arm_cfg"]["kind"] == "closed_book" or rs[0]["priority"] != "P0":
            continue
        for r in rs:
            if r["abstained"] or r["hhem"] is None:
                continue
            p = prompts[(a, r["qi"])]
            hyp = J.hypothesis(p["question"], r["answer"])
            for ci in p["context_idx"]:
                key = hashlib.sha256(json.dumps([NLI_REV, texts[ci], hyp], ensure_ascii=False).encode("utf-8")).hexdigest()
                items.append((a, r["qi"], ci, key, texts[ci], hyp))
    todo = {k: (pr, hy) for _, _, _, k, pr, hy in items if not (NLI_CACHE / f"{k}.json").exists()}
    print(f"{len({(i[0], i[1]) for i in items})} answers, {len(items)} paragraph pairs, {len(todo)} to score", flush=True)
    t0 = time.perf_counter()
    peak = 0.0
    if todo:
        torch.set_num_threads(4)
        tok = AutoTokenizer.from_pretrained(NLI_REPO, revision=NLI_REV)
        model = AutoModelForSequenceClassification.from_pretrained(NLI_REPO, revision=NLI_REV).eval()
        ent = [i for i, l in model.config.id2label.items() if l.lower() == "entailment"][0]
        ks = list(todo)
        for s in range(0, len(ks), 8):
            chunk = ks[s : s + 8]
            enc = tok([todo[k][0] for k in chunk], [todo[k][1] for k in chunk], truncation=True, max_length=512, padding=True, return_tensors="pt")
            with torch.no_grad():
                pr = torch.softmax(model(**enc).logits, -1)[:, ent].tolist()
            for k, v in zip(chunk, pr):
                (NLI_CACHE / f"{k}.json").write_text(json.dumps({"entail": v, "revision": NLI_REV}), encoding="utf-8")
            peak = max(peak, psutil.Process().memory_info().rss / 1e9)
            if (s // 8) % 50 == 0:
                print(f"{s + len(chunk)}/{len(ks)} pairs ({(time.perf_counter() - t0) / 60:.1f} min), RSS {peak:.2f} GB", flush=True)
    per: dict[tuple, list[float]] = {}
    for a, qi, ci, k, _, _ in items:
        per.setdefault((a, qi), []).append(json.loads((NLI_CACHE / f"{k}.json").read_text(encoding="utf-8"))["entail"])
    rows = []
    for a, rs in J_.items():
        for r in rs:
            if (a, r["qi"]) in per:
                rows.append({"arm": a, "kind": r["kind"], "N": r["N"], "S": r["S"], "seed": r["seed"], "qi": r["qi"], "hhem": r["hhem"],
                             "nli_entail_max_over_paragraphs": max(per[(a, r["qi"])]), "correct": r["correct"], "gold_in_context": r["gold_in_context"]})
    write_csv(out / "nli_scores.csv", rows)

    from scipy.stats import spearmanr
    h = np.array([r["hhem"] for r in rows])
    n_ = np.array([r["nli_entail_max_over_paragraphs"] for r in rows])
    summ = {"model": NLI_REPO, "revision": NLI_REV, "answers_scored": len(rows), "paragraph_pairs": len(items), "seconds_this_run": time.perf_counter() - t0,
            "peak_rss_gb_this_run": peak, "premise_handling": "each retrieved paragraph scored separately (512-token limit); score = max P(entailment) over the paragraphs",
            "spearman_hhem_vs_nli": float(spearmanr(h, n_).statistic), "by_threshold": {}}
    for t in THRESHOLDS:
        fa, fb = h >= t, n_ >= t
        summ["by_threshold"][str(t)] = {"agreement": float((fa == fb).mean()), "kappa": kappa(fa, fb), "faithful_rate_hhem": float(fa.mean()), "faithful_rate_nli": float(fb.mean())}
    arms = []
    for a in dict.fromkeys(r["arm"] for r in rows):
        sub = [r for r in rows if r["arm"] == a]
        arms.append({"arm": a, "kind": sub[0]["kind"], "N": sub[0]["N"], "S": sub[0]["S"], "n_scored": len(sub),
                     "ungrounded_hhem_0.5": float(np.mean([r["hhem"] < 0.5 for r in sub])), "ungrounded_nli_0.5": float(np.mean([r["nli_entail_max_over_paragraphs"] < 0.5 for r in sub]))})
    write_csv(out / "nli_by_arm.csv", arms)
    # does the ordering of quantum vs classical (ungrounded rate, same N) agree across judges?
    agree = []
    for x in arms:
        if x["kind"] == "quantum":
            c = next((y for y in arms if y["kind"] == "classical" and y["N"] == x["N"]), None)
            if c:
                agree.append((x["ungrounded_hhem_0.5"] > c["ungrounded_hhem_0.5"]) == (x["ungrounded_nli_0.5"] > c["ungrounded_nli_0.5"]))
    summ["quantum_vs_classical_ungrounded_direction_agrees_across_judges"] = {"agree": int(sum(agree)), "total": len(agree)}
    jdump(out / "nli_summary.json", summ)


# ------------------------------------------------------------------------------------------------ 8.3 examples
def step_examples(out: Path) -> None:
    J_ = load_judged()
    prompts = {(p["arm"], p["qi"]): p for p in read_jsonl(cur("phase5") / "prompts.jsonl")}
    texts = {}
    with (DATA / "paragraphs.jsonl").open(encoding="utf-8") as f:
        for line in f:
            p = json.loads(line)
            texts[p["idx"]] = p["text"]
    eq, ep = np.load(DATA / "emb_queries.npy"), np.load(DATA / "emb_paragraphs.npy")
    gt = np.load(cur("phase1") / "ground_truth_Nall.npz")
    gold_rank = gt["gold_rank"]
    ca, qa = "classical_Nall_k3", "quantum_Nall_M50_S256_seed0_k3"
    rng = np.random.default_rng(8)

    def label(r):
        if r["abstained"]:
            return "abstained"
        if r["correct"]:
            return "correct"
        return "misread" if r["gold_in_context"] else "hallucinated"

    cats = {"quantum drops gold, answer becomes wrong": [], "quantum gains gold, answer becomes right": [],
            "both retrieve gold, quantum answer differs and is wrong": [], "neither retrieves gold (shared retrieval failure)": []}
    for q in range(200):
        c, k = J_[ca][q], J_[qa][q]
        if c["correct"] and not k["correct"] and not k["abstained"] and c["gold_in_context"] and not k["gold_in_context"]:
            cats["quantum drops gold, answer becomes wrong"].append(q)
        elif k["correct"] and not c["correct"] and k["gold_in_context"] and not c["gold_in_context"]:
            cats["quantum gains gold, answer becomes right"].append(q)
        elif c["gold_in_context"] and k["gold_in_context"] and c["correct"] and not k["correct"] and not k["abstained"]:
            cats["both retrieve gold, quantum answer differs and is wrong"].append(q)
        elif not c["gold_in_context"] and not k["gold_in_context"] and not c["correct"] and not k["correct"]:
            cats["neither retrieves gold (shared retrieval failure)"].append(q)
    quota = {"quantum drops gold, answer becomes wrong": 8, "quantum gains gold, answer becomes right": 4,
             "both retrieve gold, quantum answer differs and is wrong": 4, "neither retrieves gold (shared retrieval failure)": 4}
    rows, counts = [], {}
    for cat, qs in cats.items():
        counts[cat] = len(qs)
        pick = sorted(rng.choice(qs, size=min(quota[cat], len(qs)), replace=False).tolist()) if qs else []
        for q in pick:
            row = {"category": cat, "qi": q, "question": prompts[(ca, q)]["question"], "gold_answers": " | ".join(sorted(set(prompts[(ca, q)]["answers"]))),
                   "classical_gold_rank_Nall": int(gold_rank[q]) + 1 if gold_rank[q] >= 0 else ""}
            for tag, a in (("classical", ca), ("quantum_S256", qa)):
                r, ids = J_[a][q], prompts[(a, q)]["context_idx"]
                row[f"{tag}_retrieved_idx"] = " ".join(map(str, ids))
                row[f"{tag}_cosines"] = " ".join(f"{float(ep[i] @ eq[q]):.3f}" for i in ids)
                row[f"{tag}_gold_in_context"] = r["gold_in_context"]
                row[f"{tag}_answer"] = r["answer"].replace("\n", " ")
                row[f"{tag}_outcome"] = label(r)
                row[f"{tag}_hhem"] = "" if r["hhem"] is None else round(r["hhem"], 3)
            row["top1_quantum_context_head"] = texts[prompts[(qa, q)]["context_idx"][0]][:160].replace("\n", " ")
            rows.append(row)
    write_csv(out / "qualitative_examples.csv", rows)
    jdump(out / "qualitative_category_counts.json", {"pool_sizes_n200_N_all_S256_seed0": counts, "examples_written": len(rows), "selection": "seeded random (seed 8) within category, sorted by question index"})


# ------------------------------------------------------------------------------------------------ 8.4 audit
def step_audit(out: Path) -> None:
    f = ROOT / "results" / "audit_template.csv"
    rows = rd(f)
    lab = [r for r in rows if r["human_correct(1/0)"].strip() in ("0", "1")]
    res = {"audit_file": "results/audit_template.csv", "rows": len(rows), "rows_labelled": len(lab)}
    if len(lab) < 10:
        res["status"] = "pending: human labels not returned; kappa not computed"
        jdump(out / "audit_agreement.json", res)
        return
    hc = np.array([r["human_correct(1/0)"].strip() == "1" for r in lab])
    ac = np.array([b(r["auto_correct"]) for r in lab])
    res["correctness"] = {"agreement": float((hc == ac).mean()), "kappa": kappa(hc, ac)}
    sup = [r for r in lab if r["human_supported_by_context(1/0)"].strip() in ("0", "1") and r["auto_hhem"] not in ("", None) and not b(r["auto_abstained"])]
    if len(sup) >= 10:
        hs = np.array([r["human_supported_by_context(1/0)"].strip() == "1" for r in sup])
        af = np.array([float(r["auto_hhem"]) >= 0.5 for r in sup])
        res["faithfulness_hhem_0.5"] = {"n": len(sup), "agreement": float((hs == af).mean()), "kappa": kappa(hs, af)}
    ho = [r for r in lab if r["human_outcome"].strip()]
    if ho:
        res["outcome_taxonomy"] = {"n": len(ho), "agreement": float(np.mean([r["human_outcome"].strip() == r["auto_outcome"] for r in ho]))}
    res["status"] = "computed"
    jdump(out / "audit_agreement.json", res)


# ------------------------------------------------------------------------------------------------ 8.5 threats
def step_threats(out: Path) -> None:
    p1, p3, p4, p5, p6 = (cur(f"phase{i}") for i in (1, 3, 4, 5, 6))
    P2 = cur("phase2")
    ld = lambda p: json.loads(p.read_text(encoding="utf-8"))  # noqa: E731
    con = ld(p1 / "contamination_check.json")
    ctl = ld(p5 / "controls_check.json")
    val = ld(p3 / "validation.json")
    reg = ld(p5 / "regeneration_check.json")
    hyg = ld(P2 / "hygiene.json")
    cs = ld(p1 / "corpus_stats.json")
    emb = ld(p1 / "embed_info.json")
    outc = rd(p5 / "outcomes_by_arm.csv")
    jrows = rd(p5 / "judged.csv")
    trunc = sum(1 for r in jrows if r["done_reason"] == "length")
    a0 = next(r for r in outc if r["arm"] == "classical_Nall_k3")
    slopes = rd(p4 / "latency_slopes.csv")
    flat = next(r for r in slopes if r["series"].startswith("Flat"))
    gb = ld(cur("phase0") / "generator_bench_summary.json")
    seeds = rd(out / "seed_robustness_outcomes.csv")
    ca = ld(out / "audit_agreement.json") if (out / "audit_agreement.json").exists() else {"status": "not run"}
    ksA = val["ks_two_sample_z_tierA_vs_tierB"]
    cb = next(r for r in outc if r["arm"] == "closed_book")
    keys = list(val.keys())
    rep = ld(p3 / "validation.json").get("repeated", {})
    rows = [
        {"threat": "Embedder contamination", "evidence": f"model card mentions SQuAD: {con.get('mentions_squad')}; classical Hit@1 ceiling at N=all is limited by the embedder itself (Phase 1 ceiling table)",
         "direction": "optimistic absolute retrieval for both arms; relative arm differences unaffected (R1)", "artifact": "results/phase1/" + p1.name + "/contamination_check.json"},
        {"threat": "LLM parametric knowledge of SQuAD", "evidence": f"closed-book correct rate {float(cb['correct_rate']):.3f} [{float(cb['correct_rate_lo']):.3f}, {float(cb['correct_rate_hi']):.3f}] vs oracle {ctl['oracle_correct']:.3f}",
         "direction": "low leakage; RAG accuracy is driven by the context", "artifact": "results/phase5/" + p5.name + "/controls_check.json"},
        {"threat": "Single dataset (SQuAD v1.1), single-gold paragraph", "evidence": f"{cs['unique_paragraphs']} paragraphs, {cs['n_eval']} eval questions on {cs['distinct_gold_paragraphs']} gold paragraphs; P@k bounded by 1/k",
         "direction": "findings may not transfer to multi-hop / multi-gold corpora", "artifact": "results/phase1/" + p1.name + "/corpus_stats.json"},
        {"threat": "Single embedder (MiniLM-L6, 384-d, 256-token limit)", "evidence": f"{emb['paragraphs_truncated']} of {cs['unique_paragraphs']} paragraphs truncated at max_seq_length",
         "direction": "score margins among distractors set how many shots are needed; another embedder changes the break-even S", "artifact": "results/phase1/" + p1.name + "/embed_info.json"},
        {"threat": "Single small generator (1.5B, CPU)", "evidence": f"classical N=all abstention {float(a0['abstention_rate']):.3f}; hallucination rate {float(a0['hallucination_rate']):.3f}; chosen by H2 gate ({gb['chosen']})",
         "direction": "rarely abstains when gold is absent, so retrieval misses become confident errors; absolute rates model-specific", "artifact": "results/phase5/" + p5.name + "/outcomes_by_arm.csv"},
        {"threat": "Simulated, not real quantum", "evidence": "all quantum-arm numbers come from a classical simulation of the SWAP test; shots/gates are modelled counts", "direction": "no hardware noise, no state-preparation cost measured; no speedup claim possible", "artifact": "results/phase3/" + p3.name + "/t6_resource_counts.json"},
        {"threat": "Emulator (Tier B) vs circuit (Tier A) gap", "evidence": f"two-sample KS on standardised errors p={ksA['p']:.3f}; repeated-estimate pooled KS p<0.05 reported in Phase 3 (Failures section); slopes agree with theory",
         "direction": "equivalence supported on mean/variance, weaker on distribution shape (lattice-valued estimator)", "artifact": "results/phase3/" + p3.name + "/validation.json"},
        {"threat": "Small N relative to production", "evidence": f"largest rung {cs['unique_paragraphs']} paragraphs; Flat latency exponent {float(flat["slope_b"]):.2f} [{float(flat["slope_lo"]):.2f}, {float(flat["slope_hi"]):.2f}]",
         "direction": "scaling exponents have wide CIs; extrapolation to millions of vectors is not supported", "artifact": "results/phase4/" + p4.name + "/latency_slopes.csv"},
        {"threat": "String-match correctness and single automatic judge", "evidence": f"{trunc} answers cut by the 48-token limit; human audit: {ca.get('status')}" + (f"; kappa(correct) {ca['correctness']['kappa']:.2f}" if 'correctness' in ca else ""),
         "direction": "paraphrases counted wrong, mentions counted right; faithfulness judge unvalidated until labels return", "artifact": "results/audit_template.csv"},
        {"threat": "Generation not bit-reproducible", "evidence": f"identical text in {reg['identical_text']} of {reg["n_sampled"]} regenerated prompts; labels unchanged in {reg['same_correct_label']} of {reg["n_sampled"]}" if "identical_text" in reg else "see Phase 5 regeneration check",
         "direction": "exact reruns rely on the cache; labels were stable in the sample", "artifact": "results/phase5/" + p5.name + "/regeneration_check.json"},
        {"threat": "Limited seed coverage for hallucination", "evidence": "; ".join(f"N={s['N']}: rate sd across 3 seeds {float(s['hall_rate_sd_seeds']):.3f}, {float(s['flip_rate_hall_indicator']):.3f} of questions flip" for s in seeds),
         "direction": "T-c and break-even use seed 0 only; S=256 shows seed spread comparable to its CI", "artifact": "results/phase8/" + out.name + "/seed_robustness_outcomes.csv"},
        {"threat": "Sample size (200 questions for generation)", "evidence": f"hallucination CI half-width at classical N=all about {(float(a0['hall_hi']) - float(a0['hall_lo'])) / 2:.3f}",
         "direction": "differences below roughly that size cannot be resolved; equivalence claims are weak", "artifact": "results/phase5/" + p5.name + "/outcomes_by_arm.csv"},
        {"threat": "CPU-only, shared, thermally limited laptop", "evidence": f"power scheme: {hyg.get('power_scheme', 'n/a').strip().split('(')[-1].rstrip(')')}; CPU temperature: {hyg.get('cpu_temperature', 'n/a')}; repeat-median ranges in the latency tables",
         "direction": "small latency differences between arms are not interpretable; absolute latencies are host-specific", "artifact": "results/phase2/" + P2.name + "/hygiene.json"},
        {"threat": "Docker Desktop on Windows (WSL2) network path", "evidence": "published-port client path adds a constant delay (network diagnostic, Phase 6); in-network client used as primary",
         "direction": "HTTP overhead is specific to this host; no claim about real cloud deployments", "artifact": "results/phase6/" + p6.name + "/network_diagnostic.json"},
    ]
    write_csv(out / "threats_matrix.csv", rows)


STEPS = {"seeds": step_seeds, "thresholds": step_thresholds, "nli": step_nli, "examples": step_examples, "audit": step_audit, "threats": step_threats}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--steps", nargs="+", default=list(STEPS))
    a = ap.parse_args()
    set_global_seed(42)
    out = ROOT / "results" / "phase8" / a.run_id
    out.mkdir(parents=True, exist_ok=True)
    for s in a.steps:
        print(f"=== step: {s}", flush=True)
        STEPS[s](out)
        write_run_manifest(out / "manifests" / s, "phase8", a.run_id, seeds={"global": 42, "examples": 8, "nli_subset": "all P0 non-abstained RAG answers"},
                           config={"step": s, "thresholds": list(THRESHOLDS), "nli_model": NLI_REPO, "nli_revision": NLI_REV})
    write_run_manifest(out, "phase8", a.run_id, seeds={"global": 42}, config={"steps": a.steps})


if __name__ == "__main__":
    main()
