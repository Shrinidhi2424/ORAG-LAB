"""Phase 5 integrity/reproducibility check: re-generate a seeded sample of prompts bypassing the cache and compare with
the stored answers (text, correctness label, abstention). Quantifies generation non-determinism of CPU Ollama (R6 note).

Usage: python scripts/check_regeneration.py --run-id <phase5 run id> [--n 60]
Writes results/phase5/<run_id>/regeneration_check.json (+ .csv).
"""
from __future__ import annotations

import argparse
import csv
import json
import random
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from qrag.generate import OllamaGenerator  # noqa: E402
from qrag.judge import contains_gold, is_abstain  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--n", type=int, default=60)
    args = ap.parse_args()
    run = ROOT / "results" / "phase5" / args.run_id
    prompts = [json.loads(l) for l in (run / "prompts.jsonl").open(encoding="utf-8")]
    stored = {(g["arm"], g["qi"]): g for g in map(json.loads, (run / "generations.jsonl").open(encoding="utf-8"))}
    rng = random.Random(7)
    pick = rng.sample(prompts, args.n)
    gen = OllamaGenerator(keep_alive="2m")
    rows, t0 = [], time.perf_counter()
    for p in pick:
        r = gen.client.chat(model=gen.model, messages=p["messages"], options=gen.options, keep_alive="2m")
        new, old = r.message.content.strip(), stored[(p["arm"], p["qi"])]["text"]
        row = {"arm": p["arm"], "qi": p["qi"], "kind": p["arm_cfg"]["kind"], "identical_text": new == old,
               "correct_old": contains_gold(old, p["answers"]) and not is_abstain(old), "correct_new": contains_gold(new, p["answers"]) and not is_abstain(new),
               "abstain_old": is_abstain(old), "abstain_new": is_abstain(new), "old": old, "new": new}
        row["same_correct_label"] = row["correct_old"] == row["correct_new"]
        row["same_abstain_label"] = row["abstain_old"] == row["abstain_new"]
        # immediate repeat of the same request (is the current runner state self-consistent?)
        r2 = gen.client.chat(model=gen.model, messages=p["messages"], options=gen.options, keep_alive="2m")
        row["repeat_identical_to_new"] = r2.message.content.strip() == new
        rows.append(row)
        print(("SAME " if row["identical_text"] else "DIFF ") + p["arm"], p["qi"], flush=True)
    gen.unload()
    n = len(rows)
    summ = {"n_sampled": n, "seed": 7, "identical_text": sum(r["identical_text"] for r in rows),
            "same_correct_label": sum(r["same_correct_label"] for r in rows), "same_abstain_label": sum(r["same_abstain_label"] for r in rows),
            "immediate_repeat_identical": sum(r["repeat_identical_to_new"] for r in rows),
            "correct_old": sum(r["correct_old"] for r in rows), "correct_new": sum(r["correct_new"] for r in rows),
            "seconds": time.perf_counter() - t0,
            "by_kind": {k: {"n": sum(r["kind"] == k for r in rows), "identical": sum(r["kind"] == k and r["identical_text"] for r in rows)} for k in sorted({r["kind"] for r in rows})},
            "note": "stored answers come from the cache; this check re-ran the model without the cache, in a different request order than the original run"}
    (run / "regeneration_check.json").write_text(json.dumps(summ, indent=2), encoding="utf-8")
    with (run / "regeneration_check.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(json.dumps(summ, indent=2))


if __name__ == "__main__":
    main()
