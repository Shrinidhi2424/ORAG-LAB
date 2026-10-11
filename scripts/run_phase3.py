"""Phase 3: SWAP-test (quantum-inspired) retrieval arm - Tier A circuits, Tier B emulator, validation, retrieval.

Usage: python scripts/run_phase3.py --run-id <id> [--steps timing validate retrieval summarize tierA_e2e resources]
Outputs: results/phase3/<run_id>/ (R3). Per-config rankings go to rankings/*.npz (regenerable, seeded).
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy import stats as sps

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from qrag import emulator as EM  # noqa: E402
from qrag.manifest import write_run_manifest  # noqa: E402
from qrag.metrics import rbo_ext_matrix  # noqa: E402
from qrag.quantum_swap import SwapTester, resource_counts  # noqa: E402
from qrag.seed import set_global_seed  # noqa: E402
from qrag.stats import bootstrap_ci  # noqa: E402

DATA = ROOT / "data"
SHOTS = list(EM.SHOTS_GRID)
S_INF = 0  # code for the noise-free limit (exact cos^2) in arrays
S_ALL = SHOTS + [S_INF]
SEEDS = [0, 1, 2, 3, 4]
MODES = [20, 50, 100, "full"]
TOPK = 10
KS = (1, 3, 5, 10)
MISSING = 10**6
CHUNK = 20  # queries per chunk (H8)


def jdump(path: Path, obj) -> None:
    path.write_text(json.dumps(obj, indent=2), encoding="utf-8")


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def load():
    pv = np.load(DATA / "emb_paragraphs_512.npy")
    qv = np.load(DATA / "emb_queries_512.npy")
    eval_set = json.loads((DATA / "eval_set.json").read_text(encoding="utf-8"))
    ladder = json.loads((DATA / "ladder_N.json").read_text(encoding="utf-8"))
    return pv, qv, eval_set, ladder


def cosf64(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a.astype(np.float64), b.astype(np.float64)))


# ---------------------------------------------------------------- 3.3 timing + validation (Tier A vs Tier B)

def step_timing(out: Path, pv, qv) -> None:
    res = {}
    for te in (True, False):
        t = SwapTester(transpile_each=te)
        times, ests = [], []
        for i in range(21):
            t0 = time.perf_counter()
            ests.append(t.similarity(qv[i], pv[i * 97], 4096, seed=i))
            times.append(time.perf_counter() - t0)
        res["with_transpile" if te else "without_transpile"] = {"per_pair_s_median_excl_first": float(np.median(times[1:])),
                                                               "per_pair_s_max": float(max(times)), "n": 20, "shots": 4096}
        res.setdefault("estimates", []).append(ests)
    res["identical_estimates_both_modes"] = res["estimates"][0] == res["estimates"][1]
    del res["estimates"]
    # H8: time one emulator chunk first (20 queries x full corpus x S=1024)
    cos = qv[:CHUNK] @ pv.T
    t0 = time.perf_counter()
    k = EM.zero_counts(cos, 1024, EM.config_rng(0, 1024))
    keys = EM.rank_keys(EM.c2_from_counts(k, 1024), cos)
    EM.topk_from_keys(keys, TOPK)
    res["tierB_chunk_full_scan"] = {"queries": CHUNK, "candidates": int(pv.shape[0]), "shots": 1024, "seconds": time.perf_counter() - t0}
    res["decision"] = ("Tier A runs WITHOUT transpile (Aer executes set_statevector/h/cswap natively; same seed gives identical "
                       "estimates) " + ("- per-pair cost below 2 s, no pair-count reduction needed" if res["with_transpile"]["per_pair_s_median_excl_first"] <= 2 else "- per-pair cost > 2 s: counts reduced"))
    jdump(out / "tierA_timing.json", res)
    print(json.dumps(res, indent=2))


def validation_pairs(pv, qv, p1_dir: Path, n_each: int = 250):
    rng = np.random.default_rng(42)
    pairs = []
    for i in range(n_each):
        a, b = rng.choice(pv.shape[0], 2, replace=False)
        pairs.append(("random_corpus_pair", int(a), int(b), pv[a], pv[b]))
    gt = np.load(p1_dir / "ground_truth_Nall.npz")["paragraph_idx"]
    for i in range(n_each):
        q, r = int(rng.integers(0, qv.shape[0])), int(rng.integers(0, 50))
        pairs.append(("query_top50_pair", q, int(gt[q, r]), qv[q], pv[gt[q, r]]))
    return pairs


def step_validate(out: Path, pv, qv, p1_dir: Path) -> None:
    tester = SwapTester(transpile_each=False)
    pairs = validation_pairs(pv, qv, p1_dir)
    cos = np.array([cosf64(a, b) for _, _, _, a, b in pairs])
    S = 4096
    # (a) + (b-part 1): one Tier A and one Tier B estimate per pair at S = 4096, unclipped (unbiased)
    rows, estA, tA = [], [], []
    for i, (kind, ia, ib, a, b) in enumerate(pairs):
        t0 = time.perf_counter()
        estA.append(tester.similarity(a, b, S, seed=1000 + i))
        tA.append(time.perf_counter() - t0)
    estA = np.array(estA)
    estB = EM.estimate_c2(cos, S, EM.config_rng(42, S, 1), clip=False)
    sd = EM.theory_sd(cos, S)
    for i, (kind, ia, ib, _, _) in enumerate(pairs):
        rows.append({"pair": i, "type": kind, "a": ia, "b": ib, "cos": cos[i], "c2_true": cos[i] ** 2, "est_tierA": estA[i],
                     "est_tierB": estB[i], "sd_theory": sd[i], "tierA_seconds": tA[i]})
    write_csv(out / "validation_pairs.csv", rows)
    c2 = cos**2
    zA, zB = (estA - c2) / sd, (estB - c2) / sd

    def errstats(est, z):
        e = est - c2
        return {"bias": float(e.mean()), "mae": float(np.abs(e).mean()), "rmse": float(np.sqrt((e**2).mean())),
                "z_mean": float(z.mean()), "z_sd": float(z.std(ddof=1)), "frac_abs_z_le_2": float((np.abs(z) <= 2).mean()),
                "frac_abs_z_le_3": float((np.abs(z) <= 3).mean()), "ks_vs_normal_p": float(sps.kstest(z, "norm").pvalue)}

    val = {"shots": S, "n_pairs": len(pairs), "pair_types": {"random_corpus_pair": 250, "query_top50_pair": 250},
           "theory_rmse": float(np.sqrt((sd**2).mean())), "theory_mae_normal_approx": float(np.sqrt(2 / np.pi) * sd.mean()),
           "tierA": errstats(estA, zA), "tierB": errstats(estB, zB),
           "ks_two_sample_z_tierA_vs_tierB": {"stat": float(sps.ks_2samp(zA, zB).statistic), "p": float(sps.ks_2samp(zA, zB).pvalue)},
           "tierA_seconds_per_pair_median": float(np.median(tA)), "cos_range": [float(cos.min()), float(cos.max())],
           "estimates_unclipped": True}
    # (b) repeated estimates: 50 pairs (25 of each type) x 20 repeats per tier
    sub = list(range(25)) + list(range(250, 275))
    R = 20
    A = np.array([[tester.similarity(pairs[i][3], pairs[i][4], S, seed=50_000 + 100 * i + r) for r in range(R)] for i in sub])
    B = EM.estimate_c2(np.repeat(cos[sub, None], R, axis=1), S, EM.config_rng(42, S, 2), clip=False)
    sd_sub = sd[sub][:, None]
    zA2, zB2 = ((A - c2[sub, None]) / sd_sub).ravel(), ((B - c2[sub, None]) / sd_sub).ravel()
    var_ratio = A.var(axis=1, ddof=1) / B.var(axis=1, ddof=1)
    val["repeated"] = {"pairs": len(sub), "repeats": R, "shots": S,
                       "mean_abs_diff_of_pair_means": float(np.abs(A.mean(1) - B.mean(1)).mean()),
                       "mean_abs_diff_of_pair_means_expected_sd": float(np.sqrt(2) * sd[sub].mean() / np.sqrt(R)),
                       "var_ratio_A_over_B_median": float(np.median(var_ratio)),
                       "var_ratio_A_over_B_iqr": [float(np.percentile(var_ratio, 25)), float(np.percentile(var_ratio, 75))],
                       "tierA_var_over_theory_mean": float((A.var(1, ddof=1) / sd[sub] ** 2).mean()),
                       "tierB_var_over_theory_mean": float((B.var(1, ddof=1) / sd[sub] ** 2).mean()),
                       "ks_two_sample_pooled_z": {"stat": float(sps.ks_2samp(zA2, zB2).statistic), "p": float(sps.ks_2samp(zA2, zB2).pvalue)}}
    np.savez_compressed(out / "validation_repeated.npz", tierA=A, tierB=B, cos=cos[sub], pair_index=np.array(sub))
    # (c) RMSE vs shots: Tier B on all 500 pairs x 20 repeats; Tier A on 100 pairs x 1 repeat at 5 shot settings
    curve = []
    subA = list(range(50)) + list(range(250, 300))
    sA = [64, 256, 1024, 4096, 16384]
    for s in SHOTS:
        eB = EM.estimate_c2(np.repeat(cos[:, None], R, axis=1), s, EM.config_rng(42, s, 3), clip=False) - c2[:, None]
        curve.append({"tier": "B", "shots": s, "n_pairs": len(cos), "repeats": R, "rmse": float(np.sqrt((eB**2).mean())),
                      "theory_rmse": float(np.sqrt(((1 - cos**4) / s).mean()))})
    for s in sA:
        eA = np.array([tester.similarity(pairs[i][3], pairs[i][4], s, seed=90_000 + 10 * i + sA.index(s)) for i in subA]) - c2[subA]
        curve.append({"tier": "A", "shots": s, "n_pairs": len(subA), "repeats": 1, "rmse": float(np.sqrt((eA**2).mean())),
                      "theory_rmse": float(np.sqrt(((1 - cos[subA] ** 4) / s).mean()))})
    write_csv(out / "f2_error_vs_shots.csv", curve)
    for tier in ("A", "B"):
        pts = [c for c in curve if c["tier"] == tier]
        x, y = np.log([c["shots"] for c in pts]), np.log([c["rmse"] for c in pts])
        fit = sps.linregress(x, y)
        val[f"loglog_slope_tier{tier}"] = {"slope": float(fit.slope), "stderr": float(fit.stderr),
                                          "ci95": [float(fit.slope - 1.96 * fit.stderr), float(fit.slope + 1.96 * fit.stderr)], "theory": -0.5}
    jdump(out / "validation.json", val)
    print(json.dumps(val, indent=2))


# ---------------------------------------------------------------- 3.3d + 3.4 + 3.7 + 3.8 retrieval with Tier B

def kendall_rows(c2: np.ndarray, cos: np.ndarray) -> np.ndarray:
    return np.array([sps.kendalltau(c2[i], cos[i]).statistic for i in range(c2.shape[0])], dtype=np.float32)


def run_config(cos_cand, cand_pos, gold_pos, cl_top, shots, rng, tie, tie_rng, want_tau):
    """One (N, mode, S, seed, tie) run over all queries. cos_cand: (Q, M) cosines of candidates, cand_pos: (Q, M)."""
    Q, M = cos_cand.shape
    top = np.empty((Q, TOPK), dtype=np.int32)
    cnt = np.full((Q, TOPK), -1, dtype=np.int16)
    rank = np.empty(Q, dtype=np.int64)
    tau = np.full(Q, np.nan, dtype=np.float32)
    for s in range(0, Q, CHUNK):
        c = cos_cand[s : s + CHUNK].astype(np.float64)
        if shots == S_INF:
            k, c2 = None, c**2
        else:
            k = EM.zero_counts(c, shots, rng)
            c2 = EM.c2_from_counts(k, shots, clip=True)
        keys = EM.rank_keys(c2, c, tie=tie, rng=tie_rng)
        order = EM.topk_from_keys(keys, TOPK)
        rows = np.arange(order.shape[0])[:, None]
        top[s : s + CHUNK] = cand_pos[s : s + CHUNK][rows, order]
        if k is not None:
            cnt[s : s + CHUNK] = k[rows, order].astype(np.int16)
        g = gold_pos[s : s + CHUNK]
        in_c = cand_pos[s : s + CHUNK] == g[:, None]
        has = in_c.any(1)
        gcol = in_c.argmax(1)
        kg = keys[np.arange(len(g)), gcol][:, None]
        cols = np.arange(M)[None, :]
        r = 1 + (keys > kg).sum(1) + ((keys == kg) & (cols < gcol[:, None])).sum(1)
        rank[s : s + CHUNK] = np.where(has, r, MISSING)
        if want_tau:
            tau[s : s + CHUNK] = kendall_rows(c2, c)
    eq = top[:, :, None] == cl_top[:, None, :]
    overlap = np.stack([eq[:, :k_, :k_].any(-1).sum(-1) / k_ for k_ in KS], axis=1).astype(np.float32)
    rbo = rbo_ext_matrix(top, cl_top, p=0.9).astype(np.float32)
    return {"top": top, "counts": cnt, "gold_rank": rank, "overlap": overlap, "rbo": rbo, "tau": tau,
            "top1_changed": top[:, 0] != cl_top[:, 0]}


def step_retrieval(out: Path, pv, qv, eval_set, ladder) -> None:
    rdir = out / "rankings"
    rdir.mkdir(exist_ok=True)
    gold_idx = np.array([q["gold_idx"] for q in eval_set])
    timing, audit = [], {}
    for n_name, members in ladder["rungs"].items():
        members = np.array(members)
        corpus = pv[members]
        cos_all = qv @ corpus.T  # (300, N) float32, exact cosine of padded vectors
        order_all = np.argsort(-cos_all, axis=1, kind="stable")
        gold_pos = np.searchsorted(members, gold_idx)
        cl_top = order_all[:, :TOPK].astype(np.int32)
        # 3.3d negative-cosine audit
        top_cos = np.take_along_axis(cos_all, order_all[:, :100], 1)
        c2_inf_top = np.argsort(-(cos_all.astype(np.float64) ** 2), axis=1, kind="stable")[:, :TOPK]
        audit[n_name] = {"negative_cos_in_exact_top10": int((top_cos[:, :10] < 0).sum()),
                         "negative_cos_in_exact_top100": int((top_cos < 0).sum()),
                         "queries_where_noisefree_cos2_full_scan_top10_differs_from_cos_top10":
                             int((np.sort(c2_inf_top, 1) != np.sort(cl_top, 1)).any(1).sum()),
                         "min_cos_in_full_corpus": float(cos_all.min())}
        jobs = [(m, "classical") for m in MODES] + [(50, "random")]
        for mode, tie in jobs:
            if mode == "full":
                cand_pos = np.broadcast_to(np.arange(len(members), dtype=np.int32), cos_all.shape)
                cos_cand = cos_all
                m_code = 0
            else:
                cand_pos = order_all[:, :mode].astype(np.int32)
                cos_cand = np.take_along_axis(cos_all, cand_pos, 1)
                m_code = mode
            res = {key: [] for key in ("top", "counts", "gold_rank", "overlap", "rbo", "tau", "top1_changed")}
            for shots in S_ALL:
                per_seed = {key: [] for key in res}
                for seed in SEEDS:
                    if shots == S_INF and seed > 0 and tie == "classical":
                        r = {key: v.copy() for key, v in first.items()}  # noqa: F821 - deterministic limit, copy seed 0
                    else:
                        rng = EM.config_rng(seed, shots, m_code, len(members))
                        tie_rng = EM.config_rng(seed, shots, m_code, len(members), 99) if tie == "random" else None
                        t0 = time.perf_counter()
                        r = run_config(cos_cand, cand_pos, gold_pos, cl_top, shots, rng, tie, tie_rng,
                                       want_tau=(mode != "full" and tie == "classical"))
                        timing.append({"N": n_name, "mode": mode, "tie": tie, "shots": shots, "seed": seed,
                                       "seconds": time.perf_counter() - t0, "queries": len(qv), "candidates_per_query": cos_cand.shape[1]})
                    if seed == 0:
                        first = r
                    for key in res:
                        per_seed[key].append(r[key])
                for key in res:
                    res[key].append(np.stack(per_seed[key]))
            arrays = {key: np.stack(v) for key, v in res.items()}  # (S, seed, Q, ...)
            arrays["top"] = members[arrays["top"]].astype(np.int32)  # positions -> global paragraph idx
            np.savez_compressed(rdir / f"N{n_name}_M{mode}_tie{tie}.npz", shots=np.array(S_ALL), seeds=np.array(SEEDS),
                                classical_top10=members[cl_top].astype(np.int32), classical_gold_rank=(1 + (cos_all > np.take_along_axis(cos_all, gold_pos[:, None], 1)).sum(1)),
                                **arrays)
            print(f"N={n_name} mode={mode} tie={tie} done", flush=True)
    write_csv(out / "tierB_run_timing.csv", timing)
    jdump(out / "negative_cosine_audit.json", audit)


def classical_ranks(cr: np.ndarray) -> np.ndarray:
    return cr.astype(np.int64)


def metric_vec(rank: np.ndarray) -> dict[str, np.ndarray]:
    v = {f"Hit@{k}": (rank <= k).astype(float) for k in KS}
    v["MRR@10"] = np.where(rank <= 10, 1.0 / rank, 0.0)
    v["nDCG@10"] = np.where(rank <= 10, 1.0 / np.log2(rank + 1.0), 0.0)
    return v


def step_summarize(out: Path) -> None:
    rows, thresholds = [], []
    for f in sorted((out / "rankings").glob("*.npz")):
        z = np.load(f)
        n_name, mode, tie = f.stem.split("_")[0][1:], f.stem.split("_")[1][1:], f.stem.split("_")[2][3:]
        cl = metric_vec(classical_ranks(z["classical_gold_rank"]))
        for si, shots in enumerate(z["shots"]):
            rank = z["gold_rank"][si]  # (seed, Q)
            mv = {k: np.stack([metric_vec(rank[s])[k] for s in range(rank.shape[0])]) for k in cl}
            for j, k_ in enumerate(KS):
                mv[f"Overlap@{k_}"] = z["overlap"][si][:, :, j].astype(float)
            mv["RBO"] = z["rbo"][si].astype(float)
            mv["Top1Changed"] = z["top1_changed"][si].astype(float)
            if not np.isnan(z["tau"][si]).all():
                mv["KendallTau"] = z["tau"][si].astype(float)
            row = {"N": n_name, "M": mode, "tie": tie, "shots": int(shots) if shots else "inf"}
            for name, arr in mv.items():
                seed_means = arr.mean(axis=1)
                est, lo, hi = bootstrap_ci(arr.mean(axis=0))  # per-query mean over seeds, bootstrap over queries
                row.update({name: est, f"{name}_sd_seeds": float(seed_means.std(ddof=1)), f"{name}_lo": lo, f"{name}_hi": hi})
            for name in ("Hit@1", "Hit@3", "MRR@10"):
                d, dlo, dhi = bootstrap_ci(mv[name].mean(axis=0) - cl[name])
                row.update({f"diff_{name}": d, f"diff_{name}_lo": dlo, f"diff_{name}_hi": dhi})
            rows.append(row)
        crow = {"N": n_name, "M": mode, "tie": tie, "shots": "classical"}
        for name, vec in cl.items():
            est, lo, hi = bootstrap_ci(vec)
            crow.update({name: est, f"{name}_lo": lo, f"{name}_hi": hi})
        rows.append(crow)
    keys = sorted({k for r in rows for k in r}, key=lambda k: (k not in ("N", "M", "tie", "shots"), k))
    rows = [{k: r.get(k, "") for k in keys} for r in rows]
    write_csv(out / "retrieval_metrics.csv", rows)
    # exit-gate threshold: smallest S such that for every S' >= S the paired 95% CI of (quantum - classical) contains 0
    groups = {}
    for r in rows:
        if r["shots"] not in ("classical", "inf"):
            groups.setdefault((r["N"], r["M"], r["tie"]), []).append(r)
    for (n_name, mode, tie), rs in groups.items():
        rs = sorted(rs, key=lambda r: int(r["shots"]))
        t = {"N": n_name, "M": mode, "tie": tie}
        for name in ("Hit@3", "MRR@10", "Hit@1"):
            ok = [float(r[f"diff_{name}_lo"]) <= 0 <= float(r[f"diff_{name}_hi"]) for r in rs]
            thr = next((int(rs[i]["shots"]) for i in range(len(rs)) if all(ok[i:])), None)
            t[f"min_shots_{name}_indistinguishable"] = thr if thr is not None else "absent"
            cl_row = next(r for r in rows if (r["N"], r["M"], r["tie"], r["shots"]) == (n_name, mode, tie, "classical"))
            ok2 = [float(cl_row[f"{name}_lo"]) <= float(r[name]) <= float(cl_row[f"{name}_hi"]) for r in rs]
            thr2 = next((int(rs[i]["shots"]) for i in range(len(rs)) if all(ok2[i:])), None)
            t[f"min_shots_{name}_within_classical_CI"] = thr2 if thr2 is not None else "absent"
        thresholds.append(t)
    write_csv(out / "shot_thresholds.csv", thresholds)
    print(f"summarized {len(rows)} rows")


# ---------------------------------------------------------------- 3.5 Tier A end-to-end subset, T6 resources

def step_tierA_e2e(out: Path, pv, qv, eval_set, ladder, n_queries=20, M=10, shots=1024) -> None:
    members = np.array(ladder["rungs"]["all"])
    corpus = pv[members]
    gold_pos = np.searchsorted(members, np.array([q["gold_idx"] for q in eval_set]))
    tester = SwapTester(transpile_each=False)
    rows, t_all = [], time.perf_counter()
    for qi in range(n_queries):
        cos = corpus @ qv[qi]
        cand = np.argsort(-cos, kind="stable")[:M]
        c = cos[cand].astype(np.float64)
        t0 = time.perf_counter()
        estA = np.array([tester.similarity(qv[qi], corpus[p], shots, seed=10_000 + qi * 100 + j, clip=True) for j, p in enumerate(cand)])
        tq = time.perf_counter() - t0
        estB = EM.estimate_c2(c, shots, EM.config_rng(0, shots, M, qi))
        for tier, est in (("A", estA), ("B", estB), ("classical", c**2)):
            o = cand[EM.topk_from_keys(EM.rank_keys(est, c), M)]
            g = int(np.where(o == gold_pos[qi])[0][0]) + 1 if gold_pos[qi] in o else MISSING
            rows.append({"query": qi, "tier": tier, "gold_rank": g, "top1": int(members[o[0]]), "top1_changed_vs_classical": bool(o[0] != cand[0]),
                         "overlap@3_vs_classical": len(set(o[:3]) & set(cand[:3])) / 3, "circuit_seconds_for_query": tq if tier == "A" else ""})
    total = time.perf_counter() - t_all
    write_csv(out / "tierA_e2e.csv", rows)
    summ = {"queries": n_queries, "M": M, "shots": shots, "N": "all", "total_seconds": total,
            "circuits": n_queries * M, "seconds_per_circuit": total / (n_queries * M)}
    for tier in ("A", "B", "classical"):
        rs = [r for r in rows if r["tier"] == tier]
        summ[tier] = {"Hit@1": float(np.mean([r["gold_rank"] <= 1 for r in rs])), "Hit@3": float(np.mean([r["gold_rank"] <= 3 for r in rs])),
                      "top1_changed_frac": float(np.mean([r["top1_changed_vs_classical"] for r in rs])),
                      "overlap@3_mean": float(np.mean([r["overlap@3_vs_classical"] for r in rs]))}
    jdump(out / "tierA_e2e_summary.json", summ)
    print(json.dumps(summ, indent=2))


def step_resources(out: Path, pv, qv) -> None:
    t0 = time.perf_counter()
    res = resource_counts(qv[0], pv[0])
    res["transpile_seconds"] = time.perf_counter() - t0
    res["note"] = "Counts for generic amplitude encoding (StatePreparation) of 512-d vectors; reported, never executed."
    jdump(out / "t6_resource_counts.json", res)
    print(json.dumps(res, indent=2))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--steps", nargs="*", default=["timing", "validate", "retrieval", "summarize", "tierA_e2e", "resources"])
    args = ap.parse_args()
    set_global_seed(42)
    out = ROOT / "results" / "phase3" / args.run_id
    out.mkdir(parents=True, exist_ok=True)
    p1 = ROOT / "results" / "phase1" / (ROOT / "results/phase1/.current_run").read_text(encoding="utf-8").strip()
    pv, qv, eval_set, ladder = load()
    for s in args.steps:
        print(f"=== step: {s}", flush=True)
        t0 = time.perf_counter()
        {"timing": lambda: step_timing(out, pv, qv), "validate": lambda: step_validate(out, pv, qv, p1),
         "retrieval": lambda: step_retrieval(out, pv, qv, eval_set, ladder), "summarize": lambda: step_summarize(out),
         "tierA_e2e": lambda: step_tierA_e2e(out, pv, qv, eval_set, ladder), "resources": lambda: step_resources(out, pv, qv)}[s]()
        print(f"step {s} took {time.perf_counter() - t0:.1f} s", flush=True)
    write_run_manifest(out, "phase3", args.run_id + "_" + "-".join(args.steps),
                       seeds={"global": 42, "tierB_streams": "SeedSequence([seed, shots, M, N(, 99 for random ties)])",
                              "retrieval_seeds": SEEDS, "aer_seed_simulator": "per-call, see code"},
                       config={"steps": args.steps, "shots": SHOTS, "modes_M": [str(m) for m in MODES], "topk": TOPK,
                               "tie_break_default": "classical cosine then position", "validation_shots": 4096})


if __name__ == "__main__":
    main()
