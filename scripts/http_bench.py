"""HTTP load driver for the orchestrator (latency layer 2 and concurrency). Standard library + numpy + httpx + psutil only,
so it runs unchanged on the Windows host (through Docker Desktop's published port) or inside a container on the stack's
Docker network (the cloud-like path).

CLI: python scripts/http_bench.py --base http://orchestrator:8000 --profile small --client in_network --out DIR [--data DIR]
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import json
import statistics
import time
from pathlib import Path

import httpx
import numpy as np
import psutil

NS = ("1000", "5000", "all")
ARMS = {"classical": {"arm": "classical"}, "quantum": {"arm": "quantum", "M": 50, "shots": 1024, "seed": 0}}
N_REPEATS, N_WARMUP, N_TIMED = 5, 10, 100
CONC_LEVELS, CONC_REQUESTS, CONC_REPEATS, CONC_WARM = (1, 4, 16), 300, 3, 20


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(dict.fromkeys(k for r in rows for k in r)))
        w.writeheader()
        w.writerows(rows)


def cpu_mhz() -> float | None:
    try:
        f = psutil.cpu_freq()
        return None if f is None else f.current
    except Exception:  # noqa: BLE001
        return None


def questions(data_dir: Path, n: int) -> list[str]:
    ev = json.loads((data_dir / "eval_set.json").read_text(encoding="utf-8"))
    return [q["question"] for q in ev[:n]]


def payload(question: str, arm: str, n: str) -> dict:
    return {"question": question, "k": 3, "N": n, **ARMS[arm]}


def run_latency(base: str, profile: str, client_kind: str, qs: list[str]) -> tuple[list[dict], list[dict]]:
    conds = [(a, n) for a in ARMS for n in NS]
    raw, freq = [], []
    with httpx.Client(base_url=base, timeout=120.0) as c:
        for rep in range(N_REPEATS):
            f0 = cpu_mhz()
            for ci in np.random.default_rng(42 + rep).permutation(len(conds)):
                arm, n = conds[ci]
                for q in qs[:N_WARMUP]:
                    c.post("/rag/retrieval-only", json=payload(q, arm, n))
                for qi in range(N_WARMUP, N_WARMUP + N_TIMED):
                    t0 = time.perf_counter()
                    r = c.post("/rag/retrieval-only", json=payload(qs[qi], arm, n))
                    e2e = (time.perf_counter() - t0) * 1e3
                    row = {"profile": profile, "client": client_kind, "arm": arm, "N": n, "repeat": rep, "query_i": qi, "status": r.status_code, "e2e_ms": e2e}
                    if r.status_code == 200:
                        row.update(r.json()["timings"])
                    raw.append(row)
            freq.append({"profile": profile, "client": client_kind, "repeat": rep, "cpu_mhz_start": f0, "cpu_mhz_end": cpu_mhz()})
            print(f"[{profile}/{client_kind}] latency repeat {rep} done", flush=True)
    return raw, freq


def summarize_latency(raw: list[dict]) -> list[dict]:
    rows = []
    for (prof, kind, arm, n) in dict.fromkeys((r["profile"], r["client"], r["arm"], r["N"]) for r in raw):
        key = (prof, kind, arm, n)
        allr = [r for r in raw if (r["profile"], r["client"], r["arm"], r["N"]) == key]
        sel = [r for r in allr if r["status"] == 200]
        e2e = np.array([r["e2e_ms"] for r in sel])
        reps = sorted({r["repeat"] for r in sel})
        rep_med = [statistics.median(r["e2e_ms"] for r in sel if r["repeat"] == rp) for rp in reps]
        med = lambda key_: float(np.median([r[key_] for r in sel if key_ in r]))  # noqa: E731
        ret_c, ret_h = f"{arm}_compute_ms", f"{arm}_hop_ms"
        rows.append({"profile": prof, "client": kind, "arm": arm, "N": n, "n": len(sel), "errors": len(allr) - len(sel),
                     "e2e_median_ms": float(np.median(e2e)), "e2e_p95_ms": float(np.percentile(e2e, 95)), "e2e_mean_ms": float(e2e.mean()),
                     "repeat_median_min_ms": min(rep_med), "repeat_median_max_ms": max(rep_med), "orchestrator_total_median_ms": med("orchestrator_total_ms"),
                     "embed_hop_median_ms": med("embedder_hop_ms"), "embed_compute_median_ms": med("embedder_compute_ms"),
                     "retrieve_hop_median_ms": med(ret_h), "retrieve_compute_median_ms": med(ret_c), "retrieve_search_median_ms": med("retrieve_search_ms"),
                     "retrieve_estimate_median_ms": med("retrieve_estimate_ms") if arm == "quantum" else "",
                     "embed_service_overhead_median_ms": float(np.median([r["embedder_hop_ms"] - r["embedder_compute_ms"] for r in sel])),
                     "retrieve_service_overhead_median_ms": float(np.median([r[ret_h] - r[ret_c] for r in sel])),
                     "client_to_orchestrator_overhead_median_ms": float(np.median([r["e2e_ms"] - r["orchestrator_total_ms"] for r in sel]))})
    return rows


async def conc_once(base: str, payloads: list[dict], concurrency: int) -> dict:
    limits = httpx.Limits(max_connections=concurrency + 4, max_keepalive_connections=concurrency + 4)
    async with httpx.AsyncClient(base_url=base, timeout=300.0, limits=limits) as c:
        sem = asyncio.Semaphore(concurrency)
        lat, errs = [], 0

        async def one(p: dict) -> None:
            nonlocal errs
            async with sem:
                t0 = time.perf_counter()
                try:
                    ok = (await c.post("/rag/retrieval-only", json=p)).status_code == 200
                except httpx.HTTPError:
                    ok = False
                lat.append((time.perf_counter() - t0) * 1e3)
                errs += 0 if ok else 1

        t0 = time.perf_counter()
        await asyncio.gather(*[one(p) for p in payloads])
        wall = time.perf_counter() - t0
    return {"wall_s": wall, "throughput_rps": len(payloads) / wall, "median_ms": float(np.median(lat)), "p95_ms": float(np.percentile(lat, 95)),
            "errors": errs, "requests": len(payloads)}


def run_concurrency(base: str, profile: str, client_kind: str, qs: list[str]) -> list[dict]:
    rows = []
    for arm in ARMS:
        for conc in CONC_LEVELS:
            asyncio.run(conc_once(base, [payload(qs[i % len(qs)], arm, "all") for i in range(CONC_WARM)], conc))  # warm-up, discarded
            for rep in range(CONC_REPEATS):
                res = asyncio.run(conc_once(base, [payload(qs[(rep * 31 + i) % len(qs)], arm, "all") for i in range(CONC_REQUESTS)], conc))
                rows.append({"profile": profile, "client": client_kind, "arm": arm, "N": "all", "clients": conc, "repeat": rep, **res})
                print(f"[{profile}/{client_kind}] {arm} clients={conc} rep={rep}: {res['throughput_rps']:.1f} rps, p95 {res['p95_ms']:.0f} ms, errors {res['errors']}", flush=True)
    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--profile", required=True)
    ap.add_argument("--client", required=True, choices=["host_port", "in_network"])
    ap.add_argument("--out", required=True)
    ap.add_argument("--data", default="data")
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    qs = questions(Path(args.data), N_WARMUP + N_TIMED)
    raw, freq = run_latency(args.base, args.profile, args.client, qs)
    write_csv(out / "latency_raw.csv", raw)
    (out / "cpu_freq_per_repeat.json").write_text(json.dumps(freq, indent=2), encoding="utf-8")
    write_csv(out / "concurrency.csv", run_concurrency(args.base, args.profile, args.client, qs))


if __name__ == "__main__":
    main()
