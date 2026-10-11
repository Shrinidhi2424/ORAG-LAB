"""Phase 1: corpus, eval set, ladder, embeddings, exact ground truth, sanity checks, contamination card.

Usage: python scripts/run_phase1.py --run-id <id> [--steps corpus embed groundtruth sanity card] [--force]
Raw outputs go to results/phase1/<run_id>/ (R3); large arrays go to git-ignored data/*.npy.
"""
from __future__ import annotations

import argparse
import csv
import gc
import json
import re
import sys
import time
from pathlib import Path

import numpy as np
import psutil

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from qrag import embed as E  # noqa: E402
from qrag.corpus import build_eval_set, build_ladder, extract_paragraphs  # noqa: E402
from qrag.index_classical import exact_topk, gold_ranks  # noqa: E402
from qrag.manifest import write_run_manifest  # noqa: E402
from qrag.metrics import hit_at_k, mrr_at_k, ndcg_at_k, precision_at_k  # noqa: E402
from qrag.seed import set_global_seed  # noqa: E402

DATA = ROOT / "data"
ALL_STEPS = ["corpus", "embed", "groundtruth", "sanity", "card"]
KS = (1, 3, 5, 10)


def jdump(path: Path, obj) -> None:
    path.write_text(json.dumps(obj, indent=2), encoding="utf-8")


def load_paragraphs() -> list[dict]:
    with (DATA / "paragraphs.jsonl").open(encoding="utf-8") as f:
        return [json.loads(line) for line in f]


def step_corpus(out: Path) -> None:
    paragraphs, pstats = extract_paragraphs()
    eval_set, estats = build_eval_set(paragraphs, n=300, seed=42)
    rungs, lstats = build_ladder(paragraphs, eval_set, seed=42)
    with (DATA / "paragraphs.jsonl").open("w", encoding="utf-8", newline="\n") as f:
        for p in paragraphs:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")
    jdump(DATA / "eval_set.json", eval_set)
    jdump(DATA / "ladder_N.json", {"seed": 42, "n_paragraphs": len(paragraphs), "rungs": rungs, **lstats})
    lens = np.array([len(p["text"].split()) for p in paragraphs])
    gold = {q["gold_idx"] for q in eval_set}
    nested = all(set(rungs[a]) <= set(rungs[b]) for a, b in zip(list(rungs)[:-1], list(rungs)[1:]))
    gold_everywhere = all(gold <= set(r) for r in rungs.values())
    stats = {
        **pstats, **estats, **lstats,
        "dev_paragraphs_in_corpus": sum(p["split"] == "dev" for p in paragraphs),
        "words_per_paragraph": {"mean": float(lens.mean()), "median": float(np.median(lens)), "p95": float(np.percentile(lens, 95)),
                                "max": int(lens.max())},
        "ladder_sizes": {k: len(v) for k, v in rungs.items()},
        "ladder_nested": nested, "gold_in_every_rung": gold_everywhere,
    }
    assert nested and gold_everywhere
    jdump(out / "corpus_stats.json", stats)
    print(json.dumps(stats, indent=2))


def step_embed(out: Path, force: bool) -> None:
    if (DATA / "emb_paragraphs.npy").exists() and not force:
        print("embeddings exist; use --force to recompute")
        return
    paragraphs = load_paragraphs()
    eval_set = json.loads((DATA / "eval_set.json").read_text(encoding="utf-8"))
    model = E.load_model()
    tok = model.tokenizer
    n_tok = np.array([len(x) for x in tok([p["text"] for p in paragraphs], add_special_tokens=True)["input_ids"]])
    max_len = int(model.max_seq_length)
    proc = psutil.Process()
    t0 = time.perf_counter()
    qv = E.embed_texts(model, [q["question"] for q in eval_set])
    t_q = time.perf_counter() - t0
    t0 = time.perf_counter()
    pv = E.embed_texts(model, [p["text"] for p in paragraphs])
    t_p = time.perf_counter() - t0
    rss = proc.memory_info().rss
    from huggingface_hub import hf_hub_download

    revision = Path(hf_hub_download(E.MODEL_NAME, "config.json")).parent.name
    np.save(DATA / "emb_paragraphs.npy", pv)
    np.save(DATA / "emb_queries.npy", qv)
    np.save(DATA / "emb_paragraphs_512.npy", E.pad_to_512(pv))
    np.save(DATA / "emb_queries_512.npy", E.pad_to_512(qv))
    info = {
        "model": E.MODEL_NAME, "revision": revision, "max_seq_length": max_len, "device": "cpu",
        "torch_threads": int(__import__("torch").get_num_threads()), "batch_size": 64,
        "n_paragraphs": len(paragraphs), "n_queries": len(qv), "dim": int(pv.shape[1]), "padded_dim": E.PADDED_DIM,
        "paragraph_embed_s": t_p, "paragraphs_per_s": len(paragraphs) / t_p,
        "query_embed_s": t_q, "queries_per_s": len(qv) / t_q,
        "process_rss_gb_after_embed": rss / 1e9,
        "paragraph_tokens": {"mean": float(n_tok.mean()), "median": float(np.median(n_tok)), "max": int(n_tok.max())},
        "paragraphs_truncated": int((n_tok > max_len).sum()),
        "paragraphs_truncated_frac": float((n_tok > max_len).mean()),
    }
    jdump(out / "embed_info.json", info)
    print(json.dumps(info, indent=2))
    del model
    gc.collect()  # free the embedder before later stages (H5)


def load_arrays():
    return (np.load(DATA / "emb_paragraphs.npy"), np.load(DATA / "emb_queries.npy"),
            json.loads((DATA / "eval_set.json").read_text(encoding="utf-8")),
            json.loads((DATA / "ladder_N.json").read_text(encoding="utf-8")))


def step_groundtruth(out: Path) -> None:
    pv, qv, eval_set, ladder = load_arrays()
    gold_idx = np.array([q["gold_idx"] for q in eval_set])
    rows = []
    for name, members in ladder["rungs"].items():
        members = np.array(members)  # global paragraph indices, ascending
        corpus = pv[members]
        gold_pos = np.searchsorted(members, gold_idx)
        assert (members[gold_pos] == gold_idx).all()
        t0 = time.perf_counter()
        pos, scores = exact_topk(qv, corpus, k=50)
        dt = time.perf_counter() - t0
        ranks = gold_ranks(qv, corpus, gold_pos)
        np.savez_compressed(out / f"ground_truth_N{name}.npz", paragraph_idx=members[pos].astype(np.int32), scores=scores,
                            gold_rank=ranks, members=members.astype(np.int32))
        row = {"N": name, "corpus_size": len(members), "brute_force_s": round(dt, 3)}
        row.update({f"Hit@{k}": hit_at_k(ranks, k) for k in KS})
        row.update({f"P@{k}": precision_at_k(ranks, k) for k in KS})
        row.update({"MRR@10": mrr_at_k(ranks, 10), "nDCG@10": ndcg_at_k(ranks, 10), "median_gold_rank": float(np.median(ranks))})
        rows.append(row)
        print(row, flush=True)
    with (out / "ceiling_by_N.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def step_sanity(out: Path) -> None:
    pv, qv, eval_set, ladder = load_arrays()
    pv512, qv512 = np.load(DATA / "emb_paragraphs_512.npy"), np.load(DATA / "emb_queries_512.npy")
    gold_idx = np.array([q["gold_idx"] for q in eval_set])
    gold_cos = np.einsum("ij,ij->i", qv, pv[gold_idx])
    cos512 = np.einsum("ij,ij->i", qv512, pv512[gold_idx])
    neg_top10 = {}
    for name in ladder["rungs"]:
        gt = np.load(out / f"ground_truth_N{name}.npz")
        top10 = gt["scores"][:, :10]
        neg_top10[name] = {"negative_cosine_in_top10": int((top10 < 0).sum()), "min_top10_score": float(top10.min())}
    norm_p, norm_q = np.linalg.norm(pv, axis=1), np.linalg.norm(qv, axis=1)
    res = {
        "has_nan": bool(np.isnan(pv).any() or np.isnan(qv).any()),
        "paragraph_norm": {"min": float(norm_p.min()), "max": float(norm_p.max())},
        "query_norm": {"min": float(norm_q.min()), "max": float(norm_q.max())},
        "padded_norm_max_abs_dev": float(max(abs(np.linalg.norm(pv512, axis=1) - 1).max(), abs(np.linalg.norm(qv512, axis=1) - 1).max())),
        "padding_cosine_max_abs_diff": float(np.abs(gold_cos - cos512).max()),
        "padding_columns_all_zero": bool((pv512[:, 384:] == 0).all() and (qv512[:, 384:] == 0).all()),
        "gold_cosine": {q: float(np.percentile(gold_cos, p)) for q, p in (("min", 0), ("p5", 5), ("p25", 25), ("median", 50), ("p75", 75), ("p95", 95), ("max", 100))},
        "gold_cosine_mean": float(gold_cos.mean()),
        "top10_negative_cosine": neg_top10,
    }
    res["classical_ceiling_hit_at_1_by_N"] = {r["N"]: float(r["Hit@1"]) for r in csv.DictReader((out / "ceiling_by_N.csv").open(encoding="utf-8"))}
    jdump(out / "sanity.json", res)
    np.savetxt(out / "gold_cosine.csv", gold_cos, header="gold_cosine", comments="")
    assert not res["has_nan"] and abs(res["paragraph_norm"]["min"] - 1) < 1e-4 and abs(res["paragraph_norm"]["max"] - 1) < 1e-4
    print(json.dumps(res, indent=2))


def step_card(out: Path) -> None:
    from huggingface_hub import hf_hub_download

    path = Path(hf_hub_download(E.MODEL_NAME, "README.md"))
    text = path.read_text(encoding="utf-8")
    (out / "model_card.md").write_text(text, encoding="utf-8")
    lines = text.splitlines()
    hits = [{"line": i + 1, "text": ln.strip()} for i, ln in enumerate(lines) if re.search(r"squad|wikipedia|wiki", ln, re.I)]
    res = {"source": f"https://huggingface.co/{E.MODEL_NAME}", "revision": path.parent.name, "card_lines": len(lines),
           "mentions_squad": any(re.search("squad", ln, re.I) for ln in lines), "squad_or_wiki_lines": hits}
    jdump(out / "contamination_check.json", res)
    print(json.dumps(res, indent=2))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--steps", nargs="*", default=ALL_STEPS)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    set_global_seed(42)
    out = ROOT / "results" / "phase1" / args.run_id
    out.mkdir(parents=True, exist_ok=True)
    for s in args.steps:
        print(f"=== step: {s}", flush=True)
        {"corpus": lambda: step_corpus(out), "embed": lambda: step_embed(out, args.force),
         "groundtruth": lambda: step_groundtruth(out), "sanity": lambda: step_sanity(out), "card": lambda: step_card(out)}[s]()
    write_run_manifest(out, "phase1", args.run_id, seeds={"global": 42, "eval_set": 42, "ladder": 42},
                       config={"steps": args.steps, "eval_n": 300, "ladder": [1000, 2000, 5000, 10000, "all"], "k_ground_truth": 50})


if __name__ == "__main__":
    main()
