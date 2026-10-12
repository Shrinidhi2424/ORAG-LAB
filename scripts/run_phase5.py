"""Phase 5: RAG pipeline + hallucination experiments (200 questions, plan H4).

Usage: python scripts/run_phase5.py --run-id <id> --steps build|generate|judge|analyze [--max-priority P0|P1] [--hours H]
- build    : all prompts of the run matrix -> prompts.jsonl (also usable for the Colab fallback C)
- generate : resumable; one JSONL line per answer in generations.jsonl; cache/llm/ holds the answers (R6)
- judge    : correctness, abstention, HHEM faithfulness (Ollama must be stopped first: RAM discipline H5)
- analyze  : taxonomy, rates with CIs, threshold sweep, McNemar (T-c, Holm), mediation by gold-in-context, controls, audit sheet
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
import psutil

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from qrag import judge as J  # noqa: E402
from qrag.manifest import write_run_manifest  # noqa: E402
from qrag.pipeline import Arm, PrecomputedRetrieval, build_record, load_paragraph_texts  # noqa: E402
from qrag.seed import set_global_seed  # noqa: E402
from qrag.stats import bootstrap_ci, holm, mcnemar_exact  # noqa: E402

DATA = ROOT / "data"
N_Q = 200
THRESHOLDS = (0.3, 0.5, 0.7)
DEFAULT_T = 0.5
JUDGE_CACHE = ROOT / "cache" / "judge"


def run_matrix() -> list[tuple[str, Arm]]:
    """Plan 5.3 in priority order."""
    m = [("P0", Arm("closed_book")), ("P0", Arm("oracle")), ("P0", Arm("random", seed=42))]
    for n in ("5000", "all"):
        m.append(("P0", Arm("classical", N=n)))
    for n in ("5000", "all"):
        for s in (64, 256, 1024):
            m.append(("P0", Arm("quantum", N=n, S=s, seed=0)))
    for n in ("5000", "all"):
        m.append(("P1", Arm("quantum", N=n, S=4096, seed=0)))
    m.append(("P1", Arm("classical", N="1000")))
    for s in (64, 256, 1024, 4096):
        m.append(("P1", Arm("quantum", N="1000", S=s, seed=0)))
    for n in ("5000", "all"):
        for seed in (1, 2):
            m.append(("P1", Arm("quantum", N=n, S=256, seed=seed)))
    return m


def jdump(p: Path, o) -> None:
    p.write_text(json.dumps(o, indent=2, ensure_ascii=False), encoding="utf-8")


def read_jsonl(p: Path) -> list[dict]:
    if not p.exists():
        return []
    with p.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(dict.fromkeys(k for r in rows for k in r)))
        w.writeheader()
        w.writerows(rows)


# ------------------------------------------------------------------------------------------------ build / generate

def step_build(out: Path) -> None:
    from qrag.generate import OllamaGenerator

    eval_set = json.loads((DATA / "eval_set.json").read_text(encoding="utf-8"))[:N_Q]  # first 200 of the fixed 300 (D8/H4)
    texts = load_paragraph_texts()
    prov = PrecomputedRetrieval(eval_set, len(texts))
    gen = OllamaGenerator()
    rows, keys_by_pri = [], {}
    for pri, arm in run_matrix():
        for qi, q in enumerate(eval_set):
            rec = build_record(arm, qi, q, prov.contexts(arm, qi), texts)
            rec["priority"] = pri
            rec["cache_key"] = gen.key(rec["messages"])
            rows.append(rec)
            keys_by_pri.setdefault(pri, set()).add(rec["cache_key"])
    with (out / "prompts.jsonl").open("w", encoding="utf-8", newline="\n") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    p0 = keys_by_pri["P0"]
    p1_new = keys_by_pri.get("P1", set()) - p0
    already = sum((gen.cache_dir / f"{k}.json").exists() for k in p0 | p1_new)
    info = {"questions": N_Q, "arms": [{"priority": p, **a.as_dict()} for p, a in run_matrix()], "records": len(rows),
            "unique_prompts_P0": len(p0), "unique_prompts_P1_extra": len(p1_new), "already_cached": already,
            "model": gen.model, "digest": gen.digest, "options": gen.options}
    jdump(out / "build_info.json", info)
    print(json.dumps({k: v for k, v in info.items() if k != "arms"}, indent=2))


def step_generate(out: Path, max_priority: str, hours: float) -> None:
    from qrag.generate import OllamaGenerator

    prompts = [r for r in read_jsonl(out / "prompts.jsonl") if r["priority"] <= max_priority]
    done = {(g["arm"], g["qi"]) for g in read_jsonl(out / "generations.jsonl")}
    gen = OllamaGenerator(keep_alive="2m")
    t_start, n_new, min_avail = time.perf_counter(), 0, psutil.virtual_memory().available
    todo = [r for r in prompts if (r["arm"], r["qi"]) not in done]
    print(f"{len(todo)} records to go ({len(prompts) - len(todo)} already logged)", flush=True)
    with (out / "generations.jsonl").open("a", encoding="utf-8", newline="\n") as f:
        for i, r in enumerate(todo):
            if time.perf_counter() - t_start > hours * 3600:
                print("time budget reached; stopping (resumable)", flush=True)
                break
            g = gen.generate(r["messages"])
            assert g["key"] == r["cache_key"]
            n_new += not g["cached"]
            min_avail = min(min_avail, psutil.virtual_memory().available)
            f.write(json.dumps({"arm": r["arm"], "qi": r["qi"], "priority": r["priority"], "cache_key": g["key"], "text": g["text"],
                                "cached_at_log_time": g["cached"], "done_reason": g["done_reason"], "wall_s": g["wall_s"],
                                "prompt_tokens": g["prompt_tokens"], "gen_tokens": g["gen_tokens"]}, ensure_ascii=False) + "\n")
            f.flush()
            if (i + 1) % 25 == 0:
                el = time.perf_counter() - t_start
                print(f"{i + 1}/{len(todo)} logged, {n_new} newly generated, {el / 60:.1f} min, "
                      f"min free RAM {min_avail / 1e9:.2f} GB", flush=True)
    gen.unload()
    jdump(out / f"generate_session_{int(time.time())}.json", {"max_priority": max_priority, "new_generations": n_new,
          "seconds": time.perf_counter() - t_start, "min_system_available_gb": min_avail / 1e9})


# ------------------------------------------------------------------------------------------------ judge

def jkey(premise: str, hyp: str) -> str:
    return hashlib.sha256(json.dumps([J.HHEM_REVISION, premise, hyp], ensure_ascii=False).encode("utf-8")).hexdigest()


def step_judge(out: Path) -> None:
    prompts = {(r["arm"], r["qi"]): r for r in read_jsonl(out / "prompts.jsonl")}
    gens = read_jsonl(out / "generations.jsonl")
    texts = load_paragraph_texts()
    JUDGE_CACHE.mkdir(parents=True, exist_ok=True)
    rows, need = [], {}
    for g in gens:
        p = prompts[(g["arm"], g["qi"])]
        C, A = J.contains_gold(g["text"], p["answers"]), J.is_abstain(g["text"])
        row = {"arm": g["arm"], "kind": p["arm_cfg"]["kind"], "N": p["arm_cfg"]["N"], "S": p["arm_cfg"]["S"], "seed": p["arm_cfg"]["seed"],
               "priority": g["priority"], "qi": g["qi"], "qid": p["qid"], "correct": C, "abstained": A, "gold_in_context": p["gold_in_context"],
               "answer": g["text"], "gen_wall_s": g["wall_s"], "prompt_tokens": g["prompt_tokens"], "gen_tokens": g["gen_tokens"],
               "done_reason": g["done_reason"], "hhem": None}
        if p["context_idx"] is not None and not A:
            premise = "\n\n".join(texts[i] for i in p["context_idx"])
            hyp = J.hypothesis(p["question"], g["text"])
            k = jkey(premise, hyp)
            row["_jk"] = k
            if not (JUDGE_CACHE / f"{k}.json").exists():
                need[k] = (premise, hyp)
        rows.append(row)
    print(f"{len(rows)} answers; {len(need)} HHEM pairs to score", flush=True)
    t0 = time.perf_counter()
    if need:
        judge = J.HHEMJudge()
        print(f"HHEM loaded in {time.perf_counter() - t0:.1f} s, RSS {psutil.Process().memory_info().rss / 1e9:.2f} GB", flush=True)
        items = list(need.items())
        for b in range(0, len(items), 8):
            chunk = items[b : b + 8]
            for (k, _), s in zip(chunk, judge.score([v for _, v in chunk], batch=4)):
                (JUDGE_CACHE / f"{k}.json").write_text(json.dumps({"hhem": s, "revision": J.HHEM_REVISION}), encoding="utf-8")
            if (b // 8) % 25 == 0:
                print(f"scored {b + len(chunk)}/{len(items)} ({(time.perf_counter() - t0) / 60:.1f} min)", flush=True)
    for r in rows:
        k = r.pop("_jk", None)
        if k:
            r["hhem"] = json.loads((JUDGE_CACHE / f"{k}.json").read_text(encoding="utf-8"))["hhem"]
    write_csv(out / "judged.csv", rows)
    jdump(out / "judge_info.json", {"model": J.HHEM_REPO, "revision": J.HHEM_REVISION, "pairs_scored_this_run": len(need),
                                     "seconds": time.perf_counter() - t0, "peak_rss_gb": getattr(psutil.Process().memory_info(), "peak_wset", 0) / 1e9,
                                     "hypothesis_template": J.hypothesis("<question>", "<answer>"), "premise": "the k retrieved paragraphs joined by blank lines",
                                     "not_scored": "closed-book (no premise) and abstained answers"})


# ------------------------------------------------------------------------------------------------ analyze

def classify(r: dict, t: float) -> str:
    F = None if r["hhem"] in ("", None) else float(r["hhem"]) >= t
    if r["kind"] == "closed_book":
        return "abstained" if r["abstained"] else ("correct_closed_book" if r["correct"] else "wrong_closed_book")
    return J.outcome(r["correct"], r["abstained"], F, r["gold_in_context"])


def as_bool(x) -> bool:
    return x in (True, "True")


def step_analyze(out: Path) -> None:
    rows = list(csv.DictReader((out / "judged.csv").open(encoding="utf-8")))
    for r in rows:
        for b in ("correct", "abstained", "gold_in_context"):
            r[b] = as_bool(r[b])
    arms = list(dict.fromkeys(r["arm"] for r in rows))
    by_arm = {a: sorted((r for r in rows if r["arm"] == a), key=lambda r: int(r["qi"])) for a in arms}
    complete = {a: len(v) == N_Q for a, v in by_arm.items()}
    summary, sweep = [], []
    for a, rs in by_arm.items():
        if not complete[a]:
            continue
        r0 = rs[0]
        base = {"arm": a, "kind": r0["kind"], "N": r0["N"], "S": r0["S"], "seed": r0["seed"], "priority": r0["priority"], "n": len(rs)}
        for t in THRESHOLDS:
            oc = [classify(r, t) for r in rs]
            row = dict(base, threshold=t)
            for o in J.OUTCOMES + ("correct_closed_book", "wrong_closed_book"):
                row[f"n_{o}"] = oc.count(o)
            hall = np.array([o in ("hallucinated", "misread") for o in oc], float)
            if r0["kind"] == "closed_book":
                hall = np.array([o == "wrong_closed_book" for o in oc], float)
            row.update({k: v for k, v in zip(("hallucination_rate", "hall_lo", "hall_hi"), bootstrap_ci(hall))})
            non_abs = [r for r, o in zip(rs, oc) if o != "abstained"]
            if r0["kind"] != "closed_book" and non_abs:
                ung = np.array([float(r["hhem"]) < t for r in non_abs], float)
                row.update({k: v for k, v in zip(("ungrounded_answer_rate", "ungr_lo", "ungr_hi"), bootstrap_ci(ung))})
            if t == DEFAULT_T:
                for name, vec in (("correct_rate", [r["correct"] and not r["abstained"] for r in rs]), ("abstention_rate", [r["abstained"] for r in rs]),
                                  ("gold_in_context_rate", [r["gold_in_context"] for r in rs])):
                    e, lo, hi = bootstrap_ci(np.array(vec, float))
                    row.update({name: e, f"{name}_lo": lo, f"{name}_hi": hi})
                row["median_gen_wall_s"] = float(np.median([float(r["gen_wall_s"]) for r in rs]))
                row["median_prompt_tokens"] = float(np.median([float(r["prompt_tokens"]) for r in rs]))
                summary.append(row)
            sweep.append(row)
    write_csv(out / "outcomes_by_arm.csv", summary)
    write_csv(out / "threshold_sweep.csv", sweep)

    # paired comparisons vs the classical arm at the same N (quantum seed-specific), T-c pre-registered at N=all
    tests = []
    for a, rs in by_arm.items():
        r0 = rs[0]
        if r0["kind"] != "quantum" or not complete[a]:
            continue
        ca = f"classical_N{r0['N']}_k3"
        if not complete.get(ca):
            continue
        cl = by_arm[ca]
        for metric, fn in (("hallucinated_or_misread", lambda r: classify(r, DEFAULT_T) in ("hallucinated", "misread")),
                           ("correct", lambda r: r["correct"] and not r["abstained"])):
            qa, ca_ = np.array([fn(r) for r in rs]), np.array([fn(r) for r in cl])
            n10, n01, p = mcnemar_exact(qa, ca_)
            d, lo, hi = bootstrap_ci(qa.astype(float) - ca_.astype(float))
            tests.append({"metric": metric, "arm": a, "N": r0["N"], "S": r0["S"], "seed": r0["seed"], "quantum_rate": float(qa.mean()), "classical_rate": float(ca_.mean()),
                          "diff": d, "diff_lo": lo, "diff_hi": hi, "quantum_only": n10, "classical_only": n01, "p_mcnemar": p,
                          "family": "T-c" if (metric == "hallucinated_or_misread" and r0["N"] == "all" and r0["seed"] == "0" and r0["S"] in ("64", "256", "1024")) else "exploratory"})
    fam = [i for i, t in enumerate(tests) if t["family"] == "T-c"]
    for i, a in zip(fam, holm([tests[i]["p_mcnemar"] for i in fam])):
        tests[i]["p_holm_T-c"] = float(a)
    if tests:
        write_csv(out / "paired_tests.csv", tests)

    # mediation view: outcomes split by whether the gold paragraph reached the context
    med = []
    for a, rs in by_arm.items():
        if not complete[a] or rs[0]["kind"] in ("closed_book",):
            continue
        for g in (True, False):
            sub = [r for r in rs if r["gold_in_context"] == g]
            if not sub:
                continue
            oc = [classify(r, DEFAULT_T) for r in sub]
            med.append({"arm": a, "gold_in_context": g, "n": len(sub), "correct_rate": float(np.mean([r["correct"] and not r["abstained"] for r in sub])),
                        "abstention_rate": float(np.mean([r["abstained"] for r in sub])),
                        "hallucinated_or_misread_rate": float(np.mean([o in ("hallucinated", "misread") for o in oc]))})
    if med:
        write_csv(out / "mediation_by_gold_in_context.csv", med)

    # controls sanity (exit gate)
    s = {r["arm"]: r for r in summary}
    ctl = {}
    if all(k in s for k in ("closed_book", "oracle", "random")):
        cb, orc, rnd = s["closed_book"], s["oracle"], s["random"]
        ctl = {"oracle_correct_gt_closed_book": orc["correct_rate_lo"] > cb["correct_rate_hi"],
               "random_correct_le_closed_book": rnd["correct_rate"] <= cb["correct_rate_hi"],
               "oracle_correct": orc["correct_rate"], "closed_book_correct": cb["correct_rate"], "random_correct": rnd["correct_rate"],
               "rule": "oracle CI entirely above closed-book CI; random point estimate not above closed-book upper CI"}
        jdump(out / "controls_check.json", ctl)

    # audit sheet (plan 5.6, P1): 50 random RAG answers for the human to label
    pool = [r for r in rows if r["kind"] not in ("closed_book",) and r["priority"] == "P0" and complete[r["arm"]]]
    if pool:
        prompts = {(p["arm"], int(p["qi"])): p for p in read_jsonl(out / "prompts.jsonl")}
        texts = load_paragraph_texts()
        pick = np.random.default_rng(42).choice(len(pool), size=min(50, len(pool)), replace=False)
        audit = []
        for i in sorted(pick):
            r = pool[i]
            p = prompts[(r["arm"], int(r["qi"]))]
            audit.append({"audit_id": len(audit) + 1, "arm": r["arm"], "qid": r["qid"], "question": p["question"], "gold_answers": " | ".join(sorted(set(p["answers"]))),
                          "contexts": "\n---\n".join(texts[c] for c in p["context_idx"]), "answer": r["answer"], "auto_correct": r["correct"], "auto_abstained": r["abstained"],
                          "auto_hhem": r["hhem"], "auto_gold_in_context": r["gold_in_context"], "auto_outcome": classify(r, DEFAULT_T),
                          "human_correct(1/0)": "", "human_supported_by_context(1/0)": "", "human_outcome": "", "notes": ""})
        write_csv(out / "audit_template.csv", audit)
        write_csv(ROOT / "results" / "audit_template.csv", audit)
    print(json.dumps({"complete_arms": sum(complete.values()), "incomplete": [a for a, c in complete.items() if not c], "controls": ctl}, indent=2))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--steps", nargs="+", required=True)
    ap.add_argument("--max-priority", default="P0")
    ap.add_argument("--hours", type=float, default=12.0)
    args = ap.parse_args()
    set_global_seed(42)
    out = ROOT / "results" / "phase5" / args.run_id
    out.mkdir(parents=True, exist_ok=True)
    for s in args.steps:
        print(f"=== step: {s}", flush=True)
        {"build": lambda: step_build(out), "generate": lambda: step_generate(out, args.max_priority, args.hours),
         "judge": lambda: step_judge(out), "analyze": lambda: step_analyze(out)}[s]()
        write_run_manifest(out / "manifests" / s, "phase5", args.run_id, seeds={"global": 42, "ollama": 42, "random_context": "[42, qi]", "audit": 42},
                           config={"step": s, "questions": N_Q, "max_priority": args.max_priority, "thresholds": list(THRESHOLDS)})


if __name__ == "__main__":
    main()
