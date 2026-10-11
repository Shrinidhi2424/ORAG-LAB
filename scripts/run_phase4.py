"""Phase 4: retrieval-only experiments - main comparison, scalability, shot/shortlist ablations, failures, tests.

Usage: python scripts/run_phase4.py --run-id <id> [--steps main latency slopes failures tests]
Outputs: results/phase4/<run_id>/ (R3). Consumes Phase 1 ground truth, Phase 2 baselines, Phase 3 rankings.
Latency here is IN-PROCESS and EMULATED-estimator latency for the quantum-sim arm (not quantum latency).
"""
from __future__ import annotations

import argparse
import csv
import json
import statistics
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import psutil
from scipy import stats as sps
from threadpoolctl import threadpool_limits

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import faiss  # noqa: E402

from qrag import emulator as EM  # noqa: E402
from qrag.index_classical import build_flat, build_ivf, default_nlist, ranks_from_ids, search  # noqa: E402
from qrag.manifest import write_run_manifest  # noqa: E402
from qrag.metrics import rbo_ext_matrix  # noqa: E402
from qrag.rerank import QuantumSimRetriever  # noqa: E402
from qrag.seed import set_global_seed  # noqa: E402
from qrag.stats import bootstrap_ci, holm, loglog_slope_ci, mcnemar_exact, paired_bootstrap_p  # noqa: E402

DATA = ROOT / "data"
KS = (1, 3, 5, 10)
MAIN_S = (256, 1024, 4096, 16384)
LAT_S = (64, 256, 1024, 4096, 16384)
LAT_M = (20, 50, 100)
FULL_S = (256, 1024, 16384)
TEST_S = (256, 1024, 4096)
N_REPEATS, N_WARMUP, N_TIMED = 5, 10, 100
MISSING = 10**6


def jdump(path: Path, obj) -> None:
    path.write_text(json.dumps(obj, indent=2), encoding="utf-8")


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(dict.fromkeys(k for r in rows for k in r)))
        w.writeheader()
        w.writerows(rows)


def cur(phase: str) -> Path:
    return ROOT / "results" / phase / (ROOT / "results" / phase / ".current_run").read_text(encoding="utf-8").strip()


def load():
    pv, qv = np.load(DATA / "emb_paragraphs.npy"), np.load(DATA / "emb_queries.npy")
    eval_set = json.loads((DATA / "eval_set.json").read_text(encoding="utf-8"))
    ladder = json.loads((DATA / "ladder_N.json").read_text(encoding="utf-8"))
    p1 = cur("phase1")
    gold_idx = np.array([q["gold_idx"] for q in eval_set])
    rungs = {}
    for name, members in ladder["rungs"].items():
        members = np.array(members)
        gt = np.load(p1 / f"ground_truth_N{name}.npz")
        rungs[name] = {"members": members, "corpus": np.ascontiguousarray(pv[members]),
                       "gold_pos": np.searchsorted(members, gold_idx), "gt_pos": np.searchsorted(members, gt["paragraph_idx"])}
    return pv, qv, eval_set, rungs


def metric_vectors(ranks: np.ndarray) -> dict[str, np.ndarray]:
    v = {f"Hit@{k}": (ranks <= k).astype(float) for k in KS}
    v["MRR@10"] = np.where(ranks <= 10, 1.0 / ranks, 0.0)
    v["nDCG@10"] = np.where(ranks <= 10, 1.0 / np.log2(ranks + 1.0), 0.0)
    return v


def ci_cols(row: dict, name: str, per_query: np.ndarray) -> None:
    est, lo, hi = bootstrap_ci(per_query)
    row.update({name: est, f"{name}_lo": lo, f"{name}_hi": hi})


# ------------------------------------------------------------------------------------------- 4.1 main table

def step_main(out: Path, qv, rungs) -> None:
    best = json.loads((cur("phase2") / "best_nprobe.json").read_text(encoding="utf-8"))
    p3 = cur("phase3") / "rankings"
    rows = []
    for n, r in rungs.items():
        flat = build_flat(r["corpus"])
        nlist = default_nlist(len(r["corpus"]))
        ivf = build_ivf(r["corpus"], nlist)
        ivf.nprobe = best[n]["best_nprobe"]
        gt10 = r["gt_pos"][:, :10]
        for arm, idx, label in (("Flat", flat, ""), (f"IVF (nprobe {best[n]['best_nprobe']})", ivf, str(best[n]["best_nprobe"]))):
            ids, _, _ = search(idx, qv, 50)
            row = {"N": n, "arm": arm, "S": "", "M": "", "nprobe": label}
            for name, vec in metric_vectors(ranks_from_ids(ids, r["gold_pos"])).items():
                ci_cols(row, name, vec)
            ov = np.array([len(set(a[:10]) & set(b[:10])) / 10 for a, b in zip(ids, gt10)])
            ci_cols(row, "Overlap@10", ov)
            ci_cols(row, "RBO", rbo_ext_matrix(ids[:, :10], gt10, 0.9))
            rows.append(row)
        z = np.load(p3 / f"N{n}_M50_tieclassical.npz")
        shots = list(z["shots"])
        for s in MAIN_S:
            si = shots.index(s)
            rank = z["gold_rank"][si]  # (seed, Q)
            row = {"N": n, "arm": "Quantum-sim", "S": s, "M": 50, "nprobe": ""}
            mv = [metric_vectors(rank[k]) for k in range(rank.shape[0])]
            for name in mv[0]:
                per_seed = np.stack([m[name] for m in mv])
                ci_cols(row, name, per_seed.mean(0))
                row[f"{name}_sd_seeds"] = float(per_seed.mean(1).std(ddof=1))
            ci_cols(row, "Overlap@10", z["overlap"][si][:, :, 3].astype(float).mean(0))
            ci_cols(row, "RBO", z["rbo"][si].astype(float).mean(0))
            rows.append(row)
    write_csv(out / "main_table.csv", rows)
    print(f"main table: {len(rows)} rows")


# ------------------------------------------------------------------------------------------- 4.2/4.3 latency

def hygiene() -> dict:
    def sh(cmd):
        try:
            return subprocess.run(cmd, capture_output=True, text=True, timeout=15).stdout.strip()
        except Exception as e:  # noqa: BLE001
            return f"unavailable: {e}"

    bat = psutil.sensors_battery()
    return {"threads": "faiss 1, BLAS/numpy 1 (threadpoolctl)", "power_plugged": None if bat is None else bool(bat.power_plugged),
            "battery_percent": None if bat is None else bat.percent, "power_scheme": sh(["powercfg", "/getactivescheme"]),
            "cpu_temperature": "not monitored; cpu_freq at repeat boundaries logged as throttling proxy",
            "interleaving": "all conditions shuffled per repeat (seeded) so thermal drift hits all arms alike (H7)",
            "warmup_queries_discarded": N_WARMUP, "timed_queries": N_TIMED, "repeats": N_REPEATS}


def step_latency(out: Path, qv, rungs) -> None:
    best = json.loads((cur("phase2") / "best_nprobe.json").read_text(encoding="utf-8"))
    queries = [np.ascontiguousarray(qv[i : i + 1]) for i in range(N_WARMUP + N_TIMED)]
    flat, ivf, qsim = {}, {}, {}
    conds = []
    for n, r in rungs.items():
        flat[n] = build_flat(r["corpus"])
        ivf[n] = build_ivf(r["corpus"], default_nlist(len(r["corpus"])))
        ivf[n].nprobe = best[n]["best_nprobe"]
        conds += [("flat", n, "", "", 10), ("ivf", n, "", "", 10)]
        for m in LAT_M:
            for s in LAT_S:
                qsim[(n, m, s)] = QuantumSimRetriever(r["corpus"], m, s, seed=0, flat_index=flat[n])
                conds.append(("qsim", n, m, s, 10))
        for s in FULL_S:
            qsim[(n, "full", s)] = QuantumSimRetriever(r["corpus"], None, s, seed=0)
            conds.append(("qsim", n, "full", s, 10))
    raw, freq = [], []
    with threadpool_limits(limits=1):
        faiss.omp_set_num_threads(1)
        for rep in range(N_REPEATS):
            f0 = psutil.cpu_freq().current
            for ci in np.random.default_rng(42 + rep).permutation(len(conds)):
                arm, n, m, s, k = conds[ci]
                if arm == "qsim":
                    ret = qsim[(n, m, s)]
                    ret.rng = np.random.default_rng(1000 * rep + 7)

                    def call(q, st):  # noqa: E306
                        ret.retrieve(q, k, st)
                else:
                    idx = flat[n] if arm == "flat" else ivf[n]

                    def call(q, st):  # noqa: E306
                        idx.search(q, k)
                for q in queries[:N_WARMUP]:
                    call(q, {})
                for qi in range(N_WARMUP, N_WARMUP + N_TIMED):
                    st = {}
                    t0 = time.perf_counter()
                    call(queries[qi], st)
                    raw.append({"arm": arm, "N": n, "M": m, "S": s, "k": k, "repeat": rep, "query_i": qi,
                                "total_s": time.perf_counter() - t0, **st})
            freq.append({"repeat": rep, "cpu_mhz_start": f0, "cpu_mhz_end": psutil.cpu_freq().current})
            print("repeat", rep, "done", flush=True)
    write_csv(out / "latency_raw.csv", raw)
    jdump(out / "cpu_freq_per_repeat.json", freq)
    jdump(out / "hygiene.json", hygiene())
    summ = []
    for arm, n, m, s, k in conds:
        sel = [r for r in raw if (r["arm"], r["N"], r["M"], r["S"]) == (arm, n, m, s)]
        tot = np.array([r["total_s"] for r in sel]) * 1e3
        rep_med = [statistics.median(r["total_s"] for r in sel if r["repeat"] == rp) * 1e3 for rp in range(N_REPEATS)]
        row = {"arm": arm, "N": n, "M": m, "S": s, "k": k, "n": len(tot), "median_ms": float(np.median(tot)),
               "p95_ms": float(np.percentile(tot, 95)), "mean_ms": float(tot.mean()), "repeat_median_min_ms": min(rep_med),
               "repeat_median_max_ms": max(rep_med), "repeat_medians_ms": ";".join(f"{x:.5f}" for x in rep_med)}
        if arm == "qsim":
            for st in ("search_s", "estimate_s", "rank_s"):
                row[f"median_{st[:-2]}_ms"] = float(np.median([r[st] for r in sel]) * 1e3)
        summ.append(row)
    write_csv(out / "latency_summary.csv", summ)


def step_slopes(out: Path, rungs) -> None:
    summ = list(csv.DictReader((out / "latency_summary.csv").open(encoding="utf-8")))
    ns = list(rungs)
    sizes = [len(rungs[n]["corpus"]) for n in ns]

    def get(arm, m, s):
        return [next(r for r in summ if (r["arm"], r["N"], r["M"], r["S"]) == (arm, n, str(m), str(s))) for n in ns]

    groups = {"Flat (exact), k=10": ("flat", "", ""), "IVF best nprobe, k=10": ("ivf", "", "")}
    for m in LAT_M:
        groups[f"Quantum-sim shortlist M={m}, S=1024"] = ("qsim", m, 1024)
    for s in FULL_S:
        groups[f"Quantum-sim full scan, S={s}"] = ("qsim", "full", s)
    rows = []
    for name, (arm, m, s) in groups.items():
        rs = get(arm, m, s)
        ys = [np.array([float(x) for x in r["repeat_medians_ms"].split(";")]) for r in rs]
        b, lo, hi, r2 = loglog_slope_ci(sizes, ys)
        rows.append({"series": name, "slope_b": b, "slope_lo": lo, "slope_hi": hi, "r2_point_fit": r2,
                     **{f"median_ms_N{n}": float(r["median_ms"]) for n, r in zip(ns, rs)}})
    # memory vs N (Phase 2 build.csv) and modelled quantum cost
    build = list(csv.DictReader((cur("phase2") / "build.csv").open(encoding="utf-8")))
    t6 = json.loads((cur("phase3") / "t6_resource_counts.json").read_text(encoding="utf-8"))
    mem = []
    for n, nn in zip(ns, sizes):
        fb = next(int(b["index_bytes"]) for b in build if b["arm"] == "flat" and b["N"] == n)
        ib = next(int(b["index_bytes"]) for b in build if b["arm"] == "ivf" and b["N"] == n)
        mem.append({"N": n, "corpus_size": nn, "flat_index_bytes": fb, "ivf_index_bytes": ib, "padded_512d_vector_bytes_for_tierA": nn * 512 * 4,
                    "qsim_shortlist_index_bytes": fb, "qsim_fullscan_index_bytes": nn * 384 * 4})
    bs = [np.polyfit(np.log(sizes), np.log([m[k] for m in mem]), 1)[0] for k in ("flat_index_bytes", "ivf_index_bytes")]
    jdump(out / "memory_slopes.json", {"loglog_slope_flat_index_bytes": float(bs[0]), "loglog_slope_ivf_index_bytes": float(bs[1])})
    write_csv(out / "memory_vs_N.csv", mem)
    write_csv(out / "latency_slopes.csv", rows)
    cost = []
    two_q_full, two_q_core = t6["full_with_state_prep"]["two_qubit_gates"], t6["swap_test_core"]["two_qubit_gates"]
    for n, nn in zip(ns, sizes):
        for m in list(LAT_M) + ["full"]:
            for s in LAT_S:
                circuits = nn if m == "full" else m
                cost.append({"N": n, "M": m, "S": s, "MODELLED_circuits_per_query": circuits, "MODELLED_total_shots_per_query": circuits * s,
                             "MODELLED_2q_gate_executions_per_query_full_circuit": circuits * s * two_q_full,
                             "MODELLED_2q_gate_executions_per_query_swap_core_only": circuits * s * two_q_core})
    write_csv(out / "modelled_quantum_cost.csv", cost)
    print(json.dumps(rows, indent=1)[:1500])


# ------------------------------------------------------------------------------------------- 4.5 failures

def step_failures(out: Path, qv, eval_set, rungs) -> None:
    n, M, S, seed, kk = "all", 50, 256, 0, 3
    r = rungs[n]
    z = np.load(cur("phase3") / "rankings" / f"N{n}_M{M}_tieclassical.npz")
    si = list(z["shots"]).index(S)
    members, corpus = r["members"], r["corpus"]
    cos_all = qv @ corpus.T
    order_all = np.argsort(-cos_all, axis=1, kind="stable")
    cand_pos = order_all[:, :M]
    cos_cand = np.take_along_axis(cos_all, cand_pos, 1).astype(np.float64)
    rng = EM.config_rng(seed, S, M, len(members))  # replay of the Phase 3 stream (chunks of 20 queries, in order)
    counts = np.concatenate([EM.zero_counts(cos_cand[s : s + 20], S, rng) for s in range(0, len(qv), 20)])
    c2 = EM.c2_from_counts(counts, S)
    keys = EM.rank_keys(c2, cos_cand, tie="classical")
    qorder = EM.topk_from_keys(keys, 10)
    replay_top = members[np.take_along_axis(cand_pos, qorder, 1)]
    consistent = bool((replay_top == z["top"][si, seed]).all())
    assert consistent, "replay does not reproduce the Phase 3 ranking"
    paragraphs = {}
    with (DATA / "paragraphs.jsonl").open(encoding="utf-8") as f:
        for line in f:
            p = json.loads(line)
            paragraphs[p["idx"]] = p
    cl_rank = z["classical_gold_rank"]
    gold_idx = np.array([q["gold_idx"] for q in eval_set])
    q_rank_in_top = np.full(len(qv), MISSING)
    for i in range(len(qv)):
        w = np.where(replay_top[i] == gold_idx[i])[0]
        q_rank_in_top[i] = w[0] + 1 if len(w) else MISSING
    dropped = np.where((cl_rank <= kk) & (q_rank_in_top > kk))[0]
    gained = np.where((cl_rank > kk) & (q_rank_in_top <= kk))[0]
    summary = {"config": {"N": n, "M": M, "S": S, "seed": seed, "k": kk}, "replay_matches_phase3_ranking": consistent,
               "queries": len(qv), "gold_in_classical_top_k": int((cl_rank <= kk).sum()), "gold_in_quantum_top_k": int((q_rank_in_top <= kk).sum()),
               "dropped_by_quantum": int(len(dropped)), "gained_by_quantum": int(len(gained)),
               "dropped_gold_rank_in_shortlist_median": float(np.median([cl_rank[i] for i in dropped])) if len(dropped) else None,
               "dropped_gold_c2_hat_mean": float(np.mean([c2[i, np.where(cand_pos[i] == np.searchsorted(members, gold_idx[i]))[0][0]] for i in dropped])) if len(dropped) else None}
    pick = np.sort(np.random.default_rng(42).choice(dropped, size=min(20, len(dropped)), replace=False))
    ex = []
    for i in pick:
        gp = int(np.searchsorted(members, gold_idx[i]))
        gcol = int(np.where(cand_pos[i] == gp)[0][0])
        winners = replay_top[i][:kk]
        ex.append({"query_i": int(i), "qid": eval_set[i]["qid"], "question": eval_set[i]["question"], "gold_answers": " | ".join(sorted(set(eval_set[i]["answers"]))),
                   "gold_id": paragraphs[int(gold_idx[i])]["id"], "gold_classical_rank": int(cl_rank[i]), "gold_cos": float(cos_cand[i, gcol]),
                   "gold_zero_count_k": int(counts[i, gcol]), "gold_c2_hat": float(c2[i, gcol]), "gold_c2_true": float(cos_cand[i, gcol] ** 2),
                   "gold_quantum_rank_in_shortlist": int(1 + (keys[i] > keys[i, gcol]).sum() + ((keys[i] == keys[i, gcol]) & (np.arange(M) < gcol)).sum()),
                   "quantum_top3_ids": " | ".join(paragraphs[int(w)]["id"] for w in winners),
                   "quantum_top3_cos": " | ".join(f"{float(qv[i] @ corpus[np.searchsorted(members, w)]):.3f}" for w in winners),
                   "quantum_top3_c2_hat": " | ".join(f"{float(c2[i, np.where(cand_pos[i] == np.searchsorted(members, w))[0][0]]):.3f}" for w in winners),
                   "gold_paragraph_start": paragraphs[int(gold_idx[i])]["text"][:160].replace("\n", " "),
                   "quantum_top1_paragraph_start": paragraphs[int(winners[0])]["text"][:160].replace("\n", " ")})
    write_csv(out / "failure_examples.csv", ex)
    jdump(out / "failure_summary.json", summary)
    print(json.dumps(summary, indent=2))


# ------------------------------------------------------------------------------------------- 4.6 tests (pre-registered, A.6)

def step_tests(out: Path, qv, rungs) -> None:
    p3 = cur("phase3") / "rankings"
    rows = []
    for n in rungs:
        z = np.load(p3 / f"N{n}_M50_tieclassical.npz")
        shots = list(z["shots"])
        cl = metric_vectors(z["classical_gold_rank"].astype(np.int64))
        for s in TEST_S:
            rank = z["gold_rank"][shots.index(s)]  # (seed, Q)
            per_seed = [metric_vectors(rank[k]) for k in range(rank.shape[0])]
            for fam, name in (("T-a", "Hit@3"), ("T-b", "MRR@10")):
                q_mean = np.stack([m[name] for m in per_seed]).mean(0)
                diff = q_mean - cl[name]
                est, lo, hi = bootstrap_ci(diff)
                row = {"family": fam, "metric": name, "N": n, "S": s, "classical": float(cl[name].mean()), "quantum_mean_over_seeds": float(q_mean.mean()),
                       "diff": est, "diff_lo": lo, "diff_hi": hi, "p_paired_bootstrap": paired_bootstrap_p(diff)}
                nz = diff[diff != 0]
                row["p_wilcoxon_signed_rank"] = float(sps.wilcoxon(nz).pvalue) if len(nz) else 1.0
                if name == "Hit@3":
                    a, b, p = mcnemar_exact(cl[name] > 0, per_seed[0][name] > 0)
                    row.update({"mcnemar_seed0_classical_only": a, "mcnemar_seed0_quantum_only": b, "p_mcnemar_seed0": p})
                rows.append(row)
    for fam in ("T-a", "T-b"):
        idx = [i for i, r in enumerate(rows) if r["family"] == fam]
        adj = holm([rows[i]["p_paired_bootstrap"] for i in idx])
        for i, a in zip(idx, adj):
            rows[i]["p_holm_primary"] = float(a)
            rows[i]["significant_at_0.05_holm"] = bool(a < 0.05)
    write_csv(out / "tests.csv", rows)
    print(f"{len(rows)} tests; significant (Holm): {sum(r['significant_at_0.05_holm'] for r in rows)}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--steps", nargs="*", default=["main", "latency", "slopes", "failures", "tests"])
    args = ap.parse_args()
    set_global_seed(42)
    out = ROOT / "results" / "phase4" / args.run_id
    out.mkdir(parents=True, exist_ok=True)
    pv, qv, eval_set, rungs = load()
    for s in args.steps:
        print(f"=== step: {s}", flush=True)
        t0 = time.perf_counter()
        {"main": lambda: step_main(out, qv, rungs), "latency": lambda: step_latency(out, qv, rungs),
         "slopes": lambda: step_slopes(out, rungs), "failures": lambda: step_failures(out, qv, eval_set, rungs),
         "tests": lambda: step_tests(out, qv, rungs)}[s]()
        print(f"step {s} took {time.perf_counter() - t0:.1f} s", flush=True)
    write_run_manifest(out, "phase4", args.run_id + "_" + "-".join(args.steps), seeds={"global": 42, "latency_query_rng": "1000*repeat+7", "bootstrap": 42},
                       config={"steps": args.steps, "main_S": list(MAIN_S), "latency_S": list(LAT_S), "latency_M": list(LAT_M), "full_scan_S": list(FULL_S),
                               "test_S": list(TEST_S), "repeats": N_REPEATS, "warmup": N_WARMUP, "timed": N_TIMED, "k_latency": 10})


if __name__ == "__main__":
    main()
