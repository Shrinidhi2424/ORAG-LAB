"""Phase 2 block of FINDINGS.md, generated from results/phase2/<run_id>/ artifacts (used by report.py)."""
from __future__ import annotations

import csv
import json
import xml.etree.ElementTree as ET
from pathlib import Path

from report import md_table, rel


def rd(path: Path) -> list[dict]:
    return list(csv.DictReader(path.open(encoding="utf-8")))


def ci(r: dict, m: str) -> str:
    return f"{float(r[m]):.3f} [{float(r[m + '_lo']):.3f}, {float(r[m + '_hi']):.3f}]"


def phase2_block(run: Path) -> tuple[str, list[list]]:
    idx: list[list] = []
    L = [f"Run `{run.name}` - manifest: `{rel(run / 'run_manifest.json')}`. FAISS single-threaded, in-process; "
         "quality on 300 queries (bootstrap 95% CI, 10k resamples); latency: batch-1 queries, 10 warm-up discarded, "
         "100 timed, 5 repeats, conditions shuffled per repeat.", ""]
    q = rd(run / "quality.csv") if (run / "quality.csv").exists() else []
    best = json.loads((run / "best_nprobe.json").read_text(encoding="utf-8")) if (run / "best_nprobe.json").exists() else {}
    lat = rd(run / "latency_summary.csv") if (run / "latency_summary.csv").exists() else []

    def lat_row(arm, n, k, npr=""):
        return next((r for r in lat if (r["arm"], r["N"], r["k"], r["nprobe"]) == (arm, n, str(k), str(npr))), None)

    if q:
        flat = [r for r in q if r["arm"] == "flat"]
        L += [f"**Classical Flat (exact) retrieval quality via FAISS IndexFlatIP** (`{rel(run / 'quality.csv')}`)", "",
              md_table(["N", "Hit@1", "Hit@3", "Hit@5", "Hit@10", "MRR@10", "nDCG@10", "P@3", "P@10"],
                       [[r["N"], *(ci(r, m) for m in ("Hit@1", "Hit@3", "Hit@5", "Hit@10", "MRR@10", "nDCG@10")),
                         f"{float(r['P@3']):.3f}", f"{float(r['P@10']):.3f}"] for r in flat]), ""]
        chk = run / "flat_vs_numpy_check.json"
        if chk.exists():
            c = json.loads(chk.read_text(encoding="utf-8"))
            L += [f"FAISS Flat vs numpy brute force (`{rel(chk)}`): fraction of queries with identical top-50 list / identical top-10 set: " +
                  "; ".join(f"N={n}: {v['flat_top50_identical_to_numpy_frac']:.3f} / {v['flat_top10_set_identical_to_numpy_frac']:.3f}" for n, v in c.items()), ""]
        ivf_rows = []
        for r in q:
            if r["arm"] != "ivf":
                continue
            lr = lat_row("ivf", r["N"], 50, r["nprobe"])
            ivf_rows.append([r["N"], r["nlist"], r["nprobe"], f"{float(r['Overlap@10_vs_exact']):.3f}", ci(r, "Hit@3"), ci(r, "Hit@10"),
                             f"{float(r['MRR@10']):.3f}", f"{float(lr['median_ms']):.3f}" if lr else "-", f"{float(lr['p95_ms']):.3f}" if lr else "-"])
        L += [f"**IVFFlat nprobe sweep** (nlist = round(sqrt N); k-means seed 42; Overlap@10 = recall of exact top-10; latency k=50, ms)", "",
              md_table(["N", "nlist", "nprobe", "Overlap@10 vs exact", "Hit@3", "Hit@10", "MRR@10", "median ms", "p95 ms"], ivf_rows), ""]
        if best:
            L += ["Best nprobe per N (" + next(iter(best.values()))["rule"] + f", `{rel(run / 'best_nprobe.json')}`): " +
                  ", ".join(f"N={n}: nprobe {v['best_nprobe']} (target met: {v['target_met']})" for n, v in best.items()), ""]
        r_all = flat[-1]
        idx.append(["P2-1", 2, f"Flat (FAISS) N={r_all['N']}: Hit@3 {float(r_all['Hit@3']):.3f}, MRR@10 {float(r_all['MRR@10']):.3f}", rel(run / "quality.csv")])

    if lat:
        fl = [lat_row("flat", r["N"], 50) for r in rd(run / "quality.csv") if r["arm"] == "flat"]
        rows = []
        for r in fl:
            ivf = best.get(r["N"])
            ir = lat_row("ivf", r["N"], 50, ivf["best_nprobe"]) if ivf else None
            rows.append([r["N"], f"{float(r['median_ms']):.3f}", f"{float(r['p95_ms']):.3f}",
                         f"{float(r['repeat_median_min_ms']):.3f}-{float(r['repeat_median_max_ms']):.3f}",
                         ir["nprobe"] if ir else "-", f"{float(ir['median_ms']):.3f}" if ir else "-", f"{float(ir['p95_ms']):.3f}" if ir else "-"])
        L += [f"**T4a Search latency per query, k=50** (`{rel(run / 'latency_summary.csv')}`; raw samples `{rel(run / 'latency_raw.csv')}`)", "",
              md_table(["N", "Flat median ms", "Flat p95 ms", "Flat run-to-run range of repeat medians (ms)", "IVF best nprobe", "IVF median ms", "IVF p95 ms"], rows), ""]
        kr = [[n, *(f"{float(lat_row('flat', n, k)['median_ms']):.3f}" for k in (10, 50, 100))] for n in [r["N"] for r in rd(run / "quality.csv") if r["arm"] == "flat"]]
        L += ["Flat search median ms by k (shortlist sizes used in Phase 3):", "", md_table(["N", "k=10", "k=50", "k=100"], kr), ""]
        idx.append(["P2-2", 2, f"Flat search median {float(fl[0]['median_ms']):.3f} ms (N={fl[0]['N']}) to {float(fl[-1]['median_ms']):.3f} ms (N={fl[-1]['N']}), k=50", rel(run / "latency_summary.csv")])

    qe = run / "query_embed_summary.json"
    if qe.exists():
        e = json.loads(qe.read_text(encoding="utf-8"))
        L += [f"**Query embedding latency** (`{rel(qe)}`): median {e['median_ms']:.2f} ms, p95 {e['p95_ms']:.2f} ms, n={e['n']}, "
              f"repeat medians {e['repeat_median_min_ms']:.2f}-{e['repeat_median_max_ms']:.2f} ms ({e['note']}).", ""]
        if lat and q:
            fl_last = lat_row("flat", rd(run / "quality.csv")[0]["N"] if False else [r for r in q if r["arm"] == "flat"][-1]["N"], 50)
            L += [f"Stage breakdown at N={fl_last['N']} (median ms): embed query {e['median_ms']:.2f} + Flat search {float(fl_last['median_ms']):.3f}.", ""]
        idx.append(["P2-3", 2, f"Query embedding median {e['median_ms']:.1f} ms (batch 1, CPU)", rel(qe)])

    bp = run / "build.csv"
    if bp.exists():
        b = rd(bp)
        L += [f"**Index build time and footprint** (`{rel(bp)}`; median of 3 builds, IVF includes k-means training)", "",
              md_table(["Arm", "N", "nlist", "Build s", "Index bytes", "Bytes/vector", "Raw vectors bytes"],
                       [[r["arm"], r["N"], r["nlist"], f"{float(r['build_s_median']):.4f}", r["index_bytes"], f"{float(r['bytes_per_vector']):.1f}", r["raw_vector_bytes"]] for r in b]), ""]
        fb = [r for r in b if r["arm"] == "flat"]
        idx.append(["P2-4", 2, f"Flat index {int(fb[-1]['index_bytes'])} bytes at N={fb[-1]['N']}", rel(bp)])

    hy = run / "hygiene.json"
    if hy.exists():
        h = json.loads(hy.read_text(encoding="utf-8"))
        fr = json.loads((run / "cpu_freq_per_repeat.json").read_text(encoding="utf-8"))
        mhz = [x for r in fr for x in (r["cpu_mhz_start"], r["cpu_mhz_end"])]
        L += [f"**Measurement hygiene (H7)** (`{rel(hy)}`): plugged in = {h['power_plugged']}, battery {h['battery_percent']}%, power scheme: `{h['power_scheme']}`, "
              f"FAISS threads = {h['faiss_omp_threads']}, CPU temperature: {h['cpu_temperature']}. Reported CPU MHz at repeat boundaries: min {min(mhz):.0f}, max {max(mhz):.0f}. {h['arm_order']}.", ""]
    sr = run / "stage_peak_rss_gb.json"
    if sr.exists():
        s = json.loads(sr.read_text(encoding="utf-8"))
        L += [f"Peak working set of the benchmark process after each stage (GB, cumulative; `{rel(sr)}`): " +
              ", ".join(f"{k}: {v:.2f}" for k, v in s.items() if k != "note"), ""]
    xml = run / "pytest_junit.xml"
    if xml.exists():
        r = ET.parse(xml).getroot()
        ts = r if r.tag == "testsuite" else r.find("testsuite")
        tot, fail, err, skip = (int(ts.get(x, 0)) for x in ("tests", "failures", "errors", "skipped"))
        L += [f"**pytest** (whole suite at Phase 2 exit): {tot} tests, {fail} failures, {err} errors, {skip} skipped (`{rel(xml)}`).", ""]
        idx.append(["P2-5", 2, f"pytest: {tot - fail - err - skip}/{tot} passed", rel(xml)])
    L += ["**Manuscript hook**: Section 9 (latency), Section 7 (classical baseline), Table T4.", ""]
    return "\n".join(L), idx
