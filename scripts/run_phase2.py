"""Phase 2: classical FAISS baseline (Flat exact, IVFFlat) - quality, build cost, footprint and latency.

Usage: python scripts/run_phase2.py --run-id <id> [--steps quality build latency qembed]
Outputs go to results/phase2/<run_id>/ (R3). In-process timing, single thread (see hygiene.json).
"""
from __future__ import annotations

import argparse
import csv
import gc
import json
import statistics
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import psutil

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import faiss  # noqa: E402

from qrag import embed as E  # noqa: E402
from qrag.index_classical import (build_flat, build_ivf, default_nlist, index_bytes, overlap_at_k,  # noqa: E402
                                  ranks_from_ids, search)
from qrag.manifest import write_run_manifest  # noqa: E402
from qrag.seed import set_global_seed  # noqa: E402
from qrag.stats import bootstrap_ci  # noqa: E402
from qrag.timing import summarize  # noqa: E402

DATA = ROOT / "data"
KS = (1, 3, 5, 10)
NPROBES = (1, 2, 4, 8, 16, 32)
N_REPEATS, N_WARMUP, N_TIMED = 5, 10, 100
RECALL_TARGET = 0.95  # rule for "best nprobe": smallest nprobe with mean Overlap@10 vs exact >= this
THREADS = 1
proc = psutil.Process()


def jdump(path: Path, obj) -> None:
    path.write_text(json.dumps(obj, indent=2), encoding="utf-8")


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def load_inputs():
    pv, qv = np.load(DATA / "emb_paragraphs.npy"), np.load(DATA / "emb_queries.npy")
    eval_set = json.loads((DATA / "eval_set.json").read_text(encoding="utf-8"))
    ladder = json.loads((DATA / "ladder_N.json").read_text(encoding="utf-8"))
    p1 = ROOT / "results" / "phase1" / (ROOT / "results/phase1/.current_run").read_text(encoding="utf-8").strip()
    gold_idx = np.array([q["gold_idx"] for q in eval_set])
    rungs = {}
    for name, members in ladder["rungs"].items():
        members = np.array(members)
        gt = np.load(p1 / f"ground_truth_N{name}.npz")
        rungs[name] = {"members": members, "corpus": np.ascontiguousarray(pv[members]),
                       "gold_pos": np.searchsorted(members, gold_idx),
                       "gt_pos": np.searchsorted(members, gt["paragraph_idx"])}
    return qv, eval_set, rungs


def metric_vectors(ranks: np.ndarray) -> dict[str, np.ndarray]:
    v = {f"Hit@{k}": (ranks <= k).astype(float) for k in KS}
    v["MRR@10"] = np.where(ranks <= 10, 1.0 / ranks, 0.0)
    v["nDCG@10"] = np.where(ranks <= 10, 1.0 / np.log2(ranks + 1.0), 0.0)
    return v


def quality_row(arm: str, n: str, nlist, nprobe, ranks, ids, gt_pos) -> dict:
    row = {"arm": arm, "N": n, "nlist": nlist, "nprobe": nprobe}
    for name, vec in metric_vectors(ranks).items():
        est, lo, hi = bootstrap_ci(vec)
        row.update({name: est, f"{name}_lo": lo, f"{name}_hi": hi})
    row["P@3"], row["P@10"] = row["Hit@3"] / 3, row["Hit@10"] / 10
    row["Overlap@10_vs_exact"] = float(overlap_at_k(ids, gt_pos, 10).mean())
    row["Overlap@50_vs_exact"] = float(overlap_at_k(ids, gt_pos, 50).mean())
    row["missing_results"] = int((ids < 0).sum())
    return row


def step_quality(out: Path, qv, rungs) -> None:
    rows, sanity, best = [], {}, {}
    for n, r in rungs.items():
        flat = build_flat(r["corpus"])
        ids, _, _ = search(flat, qv, 50)
        sanity[n] = {"flat_top50_identical_to_numpy_frac": float((ids == r["gt_pos"]).all(axis=1).mean()),
                     "flat_top10_set_identical_to_numpy_frac": float(np.mean([set(a[:10]) == set(b[:10]) for a, b in zip(ids, r["gt_pos"])]))}
        rows.append(quality_row("flat", n, "", "", ranks_from_ids(ids, r["gold_pos"]), ids, r["gt_pos"]))
        nlist = default_nlist(len(r["corpus"]))
        ivf = build_ivf(r["corpus"], nlist)
        cand = []
        for npr in NPROBES:
            ivf.nprobe = min(npr, nlist)
            ids, _, _ = search(ivf, qv, 50)
            row = quality_row("ivf", n, nlist, npr, ranks_from_ids(ids, r["gold_pos"]), ids, r["gt_pos"])
            rows.append(row)
            cand.append((npr, row["Overlap@10_vs_exact"]))
        ok = [p for p, o in cand if o >= RECALL_TARGET]
        best[n] = {"nlist": nlist, "best_nprobe": min(ok) if ok else max(p for p, _ in cand), "target_met": bool(ok),
                   "rule": f"smallest nprobe with mean Overlap@10 vs exact >= {RECALL_TARGET}; else largest swept"}
        print(n, sanity[n], best[n], flush=True)
    write_csv(out / "quality.csv", rows)
    jdump(out / "flat_vs_numpy_check.json", sanity)
    jdump(out / "best_nprobe.json", best)


def step_build(out: Path, rungs) -> dict:
    rows, indexes = [], {}
    for n, r in rungs.items():
        nlist = default_nlist(len(r["corpus"]))
        for arm in ("flat", "ivf"):
            times = []
            for _ in range(3):
                t0 = time.perf_counter()
                idx = build_flat(r["corpus"]) if arm == "flat" else build_ivf(r["corpus"], nlist)
                times.append(time.perf_counter() - t0)
            b = index_bytes(idx)
            rows.append({"arm": arm, "N": n, "corpus_size": len(r["corpus"]), "nlist": nlist if arm == "ivf" else "",
                         "build_s_median": statistics.median(times), "build_s_all": ";".join(f"{t:.4f}" for t in times),
                         "index_bytes": b, "bytes_per_vector": b / len(r["corpus"]),
                         "raw_vector_bytes": int(r["corpus"].nbytes)})
            indexes[(arm, n)] = idx
        print(n, rows[-2]["build_s_median"], rows[-1]["build_s_median"], flush=True)
    write_csv(out / "build.csv", rows)
    return indexes


def hygiene() -> dict:
    def sh(cmd):
        try:
            return subprocess.run(cmd, capture_output=True, text=True, timeout=15).stdout.strip()
        except Exception as e:  # noqa: BLE001
            return f"unavailable: {e}"

    bat = psutil.sensors_battery()
    return {"faiss_omp_threads": THREADS, "faiss_version": faiss.__version__,
            "power_plugged": None if bat is None else bool(bat.power_plugged),
            "battery_percent": None if bat is None else bat.percent,
            "power_scheme": sh(["powercfg", "/getactivescheme"]),
            "cpu_freq_mhz_at_start": psutil.cpu_freq().current if psutil.cpu_freq() else None,
            "cpu_temperature": "not monitored (no sensor tool on this host); cpu_freq per repeat logged as throttling proxy",
            "arm_order": "conditions shuffled per repeat (seeded) so thermal drift hits all conditions alike (H7)",
            "warmup_queries_discarded": N_WARMUP, "timed_queries": N_TIMED, "repeats": N_REPEATS,
            "other_load": "no other experiments running; user apps not controlled"}


def step_latency(out: Path, qv, rungs, indexes) -> None:
    queries = [np.ascontiguousarray(qv[i : i + 1]) for i in range(N_WARMUP + N_TIMED)]
    conds = []
    for n in rungs:
        nlist = default_nlist(len(rungs[n]["corpus"]))
        conds += [("flat", n, k, "") for k in (10, 50, 100)]
        conds += [("ivf", n, 50, min(p, nlist)) for p in NPROBES]
    raw, freq = [], []
    for rep in range(N_REPEATS):
        order = np.random.default_rng(42 + rep).permutation(len(conds))
        f0 = psutil.cpu_freq().current
        for ci in order:
            arm, n, k, npr = conds[ci]
            idx = indexes[(arm, n)]
            if arm == "ivf":
                idx.nprobe = npr
            for q in queries[:N_WARMUP]:
                idx.search(q, k)
            for qi in range(N_WARMUP, N_WARMUP + N_TIMED):
                _, _, dt = search(idx, queries[qi], k)
                raw.append({"arm": arm, "N": n, "k": k, "nprobe": npr, "repeat": rep, "query_i": qi, "seconds": dt})
        freq.append({"repeat": rep, "cpu_mhz_start": f0, "cpu_mhz_end": psutil.cpu_freq().current})
        print("repeat", rep, "done", flush=True)
    write_csv(out / "latency_raw.csv", raw)
    jdump(out / "cpu_freq_per_repeat.json", freq)
    summ = []
    for arm, n, k, npr in conds:
        sel = [r for r in raw if (r["arm"], r["N"], r["k"], r["nprobe"]) == (arm, n, k, npr)]
        st = summarize([r["seconds"] for r in sel]).as_dict()
        rep_med = [statistics.median(r["seconds"] for r in sel if r["repeat"] == rp) * 1e3 for rp in range(N_REPEATS)]
        summ.append({"arm": arm, "N": n, "k": k, "nprobe": npr, **st, "repeat_median_min_ms": min(rep_med), "repeat_median_max_ms": max(rep_med)})
    write_csv(out / "latency_summary.csv", summ)


def step_qembed(out: Path, eval_set) -> None:
    model = E.load_model()
    texts = [q["question"] for q in eval_set[: N_WARMUP + N_TIMED]]
    raw = []
    for rep in range(N_REPEATS):
        for i, t in enumerate(texts):
            t0 = time.perf_counter()
            model.encode([t], batch_size=1, show_progress_bar=False, convert_to_numpy=True, normalize_embeddings=True)
            dt = time.perf_counter() - t0
            if i >= N_WARMUP:
                raw.append({"repeat": rep, "query_i": i, "seconds": dt})
    write_csv(out / "query_embed_raw.csv", raw)
    st = summarize([r["seconds"] for r in raw]).as_dict()
    rep_med = [statistics.median(r["seconds"] for r in raw if r["repeat"] == rp) * 1e3 for rp in range(N_REPEATS)]
    jdump(out / "query_embed_summary.json", {**st, "repeat_median_min_ms": min(rep_med), "repeat_median_max_ms": max(rep_med),
                                              "note": "batch size 1, CPU, torch threads 4, includes tokenisation"})
    del model
    gc.collect()  # free embedder (H5)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--steps", nargs="*", default=["quality", "build", "latency", "qembed"])
    args = ap.parse_args()
    set_global_seed(42)
    faiss.omp_set_num_threads(THREADS)
    out = ROOT / "results" / "phase2" / args.run_id
    out.mkdir(parents=True, exist_ok=True)
    qv, eval_set, rungs = load_inputs()
    stage_rss, indexes = {}, None
    for s in args.steps:
        print(f"=== step: {s}", flush=True)
        if s == "quality":
            step_quality(out, qv, rungs)
        elif s == "build":
            indexes = step_build(out, rungs)
        elif s == "latency":
            indexes = indexes or step_build(out, rungs)
            jdump(out / "hygiene.json", hygiene())
            step_latency(out, qv, rungs, indexes)
        elif s == "qembed":
            step_qembed(out, eval_set)
        mi = proc.memory_info(); stage_rss[s] = getattr(mi, "peak_wset", mi.rss) / 1e9
    jdump(out / "stage_peak_rss_gb.json", {"note": "process peak working set (GB) after each stage (cumulative)", **stage_rss})
    write_run_manifest(out, "phase2", args.run_id, seeds={"global": 42, "ivf_kmeans": 42, "repeat_order": "42+repeat"},
                       config={"steps": args.steps, "nprobes": list(NPROBES), "repeats": N_REPEATS, "warmup": N_WARMUP,
                               "timed": N_TIMED, "faiss_threads": THREADS, "recall_target": RECALL_TARGET})


if __name__ == "__main__":
    main()
