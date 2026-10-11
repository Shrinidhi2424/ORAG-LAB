"""SQuAD v1.1 corpus, evaluation set and nested corpus ladder (Phase 1, tasks 1.1-1.3)."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "squad_v1.1"
LADDER_SIZES = [1000, 2000, 5000, 10000]  # plus "all"


def paragraph_id(text: str) -> str:
    """Stable, order-independent id: sha1 of the exact paragraph text."""
    return "p" + hashlib.sha1(text.encode("utf-8")).hexdigest()[:12]


def load_squad(split: str) -> dict:
    return json.loads((RAW / f"{split}-v1.1.json").read_text(encoding="utf-8"))


def extract_paragraphs() -> tuple[list[dict], dict]:
    """Unique paragraphs of train + dev (exact-duplicate texts merged). Order: train then dev, file order."""
    paragraphs, seen, stats = [], {}, {"raw": {}, "duplicates_dropped": 0}
    for split in ("train", "dev"):
        n_raw = 0
        for article in load_squad(split)["data"]:
            for p in article["paragraphs"]:
                n_raw += 1
                text = p["context"]
                pid = paragraph_id(text)
                if pid in seen:
                    stats["duplicates_dropped"] += 1
                    assert paragraphs[seen[pid]]["text"] == text, f"sha1 collision on {pid}"
                    continue
                seen[pid] = len(paragraphs)
                paragraphs.append({"idx": len(paragraphs), "id": pid, "split": split, "title": article["title"], "text": text})
        stats["raw"][split] = n_raw
    stats["unique_paragraphs"] = len(paragraphs)
    return paragraphs, stats


def build_eval_set(paragraphs: list[dict], n: int = 300, seed: int = 42) -> tuple[list[dict], dict]:
    """n dev questions sampled with a fixed seed; each keeps its gold paragraph id and all answer annotations."""
    by_id = {p["id"]: p for p in paragraphs}
    candidates = []
    for article in load_squad("dev")["data"]:
        for p in article["paragraphs"]:
            gid = paragraph_id(p["context"])
            if gid not in by_id:
                continue
            for qa in p["qas"]:
                candidates.append({"qid": qa["id"], "question": qa["question"], "gold_id": gid,
                                   "gold_idx": by_id[gid]["idx"], "answers": [a["text"] for a in qa["answers"]]})
    rng = np.random.default_rng(seed)
    order = rng.permutation(len(candidates))[:n]
    chosen = [candidates[i] for i in order]  # order = sampling order (first 200 are the LLM subset, plan D8)
    return chosen, {"candidate_questions": len(candidates), "n_eval": len(chosen),
                    "distinct_gold_paragraphs": len({q["gold_id"] for q in chosen})}


def build_ladder(paragraphs: list[dict], eval_set: list[dict], seed: int = 42) -> tuple[dict, dict]:
    """Nested rungs. Every rung holds all gold paragraphs of the eval set; distractors come from one
    fixed permutation of the non-gold paragraphs, so rung_k is a subset of rung_{k+1}."""
    gold = sorted({q["gold_idx"] for q in eval_set})
    gold_set = set(gold)
    non_gold = np.array([p["idx"] for p in paragraphs if p["idx"] not in gold_set])
    perm = np.random.default_rng(seed).permutation(len(non_gold))
    ordered = non_gold[perm]
    sizes = list(LADDER_SIZES)
    notes = []
    kept = []
    for n in sizes:
        if n < len(gold):
            notes.append(f"rung {n} skipped: only {len(gold)} gold paragraphs")
        else:
            kept.append(n)
    rungs = {}
    for n in kept:
        rungs[str(n)] = sorted(gold + ordered[: n - len(gold)].tolist())
    rungs["all"] = [p["idx"] for p in paragraphs]
    return rungs, {"n_gold": len(gold), "notes": notes}
