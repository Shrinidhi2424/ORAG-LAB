"""Phase 9.1: clean-room reproduction from a fresh clone of the committed repository.

Usage: python scripts/clean_room.py --run-id <phase9 run id> [--dest DIR] [--keep]
Writes: results/phase9/<run_id>/clean_room.csv (one row per compared artifact) and clean_room_summary.json.

What it does, in a `git clone` of HEAD (uncommitted work is NOT part of the clean room):
  0. report.py on the committed artifacts must reproduce the committed FINDINGS.md byte for byte.
  1. SQuAD raw files are copied from this working tree (no network, R6) and verified against the committed sha256.
  2. Phase 1 corpus / eval set / ladder rebuilt from SQuAD and compared with the committed files.
  3. Embedding "small config": the 300 queries and the 1000-paragraph rung are re-embedded and compared with the stored
     embeddings; the full stored embeddings are then copied in (a full re-embed takes ~15 min on this CPU).
  4. Phase 1 ground truth, Phase 2 quality, Phase 3 validation + retrieval + summary + Tier A end-to-end, Phase 4 main /
     failures / tests, Phase 5 prompt reconstruction + relabelling + analysis, Phase 7 synthesis and Phase 8
     (all steps except the NLI judge) are re-run into new run directories and compared with the committed artifacts.
Excluded by design (non-deterministic or too expensive here): latency/throughput measurements (Phases 2, 4, 6), LLM
generation (answers are compared through their cache keys instead), HHEM/NLI scoring (scores re-used from the artifacts).
Comparison rules: CSV/JSON cells compared numerically (rel 1e-9, abs 1e-12) or as strings; timing/memory fields and
run-id-bearing fields are ignored; NPZ arrays must be identical (float arrays: allclose at 1e-6); text files by sha256.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
PY = sys.executable
TIMING = re.compile(r"(second|_s$|_ms$|_ms_|wall|time|rss|brute_force|per_s|peak|timestamp)", re.I)


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def same(a, b) -> bool:
    fa, fb = num(a), num(b)
    if fa is not None and fb is not None:
        if math.isnan(fa) and math.isnan(fb):
            return True
        return math.isclose(fa, fb, rel_tol=1e-9, abs_tol=1e-12)
    return str(a) == str(b)


def flatten(o, pre=""):
    if isinstance(o, dict):
        for k, v in o.items():
            yield from flatten(v, f"{pre}.{k}" if pre else str(k))
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from flatten(v, f"{pre}[{i}]")
    else:
        yield pre, o


def compare(ref: Path, new: Path, ignore: str | None = None) -> tuple[str, str]:
    """Returns (status, detail). status in {identical, equal_ignoring_timing, equal_ignoring_line_endings, DIFFERENT, MISSING}."""
    if not new.exists() or not ref.exists():
        return "MISSING", f"ref exists={ref.exists()}, new exists={new.exists()}"
    ig = re.compile(ignore) if ignore else None
    skip = lambda k: bool(TIMING.search(k)) or bool(ig and ig.search(k))  # noqa: E731
    if sha(ref) == sha(new):
        return "identical", f"sha256 {sha(new)[:16]}"
    suf = ref.suffix
    if suf == ".csv":
        a, b = list(csv.DictReader(ref.open(encoding="utf-8"))), list(csv.DictReader(new.open(encoding="utf-8")))
        if len(a) != len(b):
            return "DIFFERENT", f"rows {len(a)} vs {len(b)}"
        cols = [c for c in a[0] if not skip(c)] if a else []
        bad = [(i, c) for i, (x, y) in enumerate(zip(a, b)) for c in cols if not same(x.get(c), y.get(c))]
        ignored = [c for c in (a[0] if a else {}) if skip(c)]
        return ("equal_ignoring_timing", f"{len(a)} rows; ignored columns {ignored}") if not bad else ("DIFFERENT", f"{len(bad)} cells differ, first {bad[:3]}")
    if suf == ".json":
        fa = dict(flatten(json.loads(ref.read_text(encoding="utf-8"))))
        fb = dict(flatten(json.loads(new.read_text(encoding="utf-8"))))
        keys = [k for k in fa if not skip(k)]
        bad = [k for k in keys if k not in fb or not same(fa[k], fb[k])]
        return ("equal_ignoring_timing", f"{len(keys)} fields; {len(fa) - len(keys)} ignored") if not bad else ("DIFFERENT", f"{len(bad)} fields differ, first {bad[:3]}")
    if suf == ".npz":
        za, zb = np.load(ref), np.load(new)
        if set(za.files) != set(zb.files):
            return "DIFFERENT", f"keys {sorted(za.files)} vs {sorted(zb.files)}"
        for k in za.files:
            x, y = za[k], zb[k]
            ok = x.shape == y.shape and (np.allclose(x, y, rtol=1e-6, atol=1e-7) if x.dtype.kind == "f" else np.array_equal(x, y))
            if not ok:
                return "DIFFERENT", f"array {k} differs"
        return "equal_ignoring_timing", f"{len(za.files)} arrays equal (float allclose 1e-6)"
    if suf in (".md", ".txt", ".jsonl"):
        crlf, lf = bytes([13, 10]), bytes([10])
        ra, rb = ref.read_bytes().replace(crlf, lf), new.read_bytes().replace(crlf, lf)
        if ra == rb:
            return "equal_ignoring_line_endings", "identical after CRLF -> LF (git checkout with text=auto on Windows)"
    return "DIFFERENT", "bytes differ"


class Room:
    def __init__(self, dest: Path, out: Path):
        self.dest, self.out, self.rows, self.durations = dest, out, [], {}
        self.env = {**os.environ, "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1", "PYTHONHASHSEED": "0", "PYTHONIOENCODING": "utf-8"}

    def run(self, stage: str, *args: str) -> None:
        t0 = time.perf_counter()
        r = subprocess.run([PY, *args], cwd=self.dest, env=self.env, capture_output=True, text=True, encoding="utf-8", errors="replace")
        self.durations[stage] = self.durations.get(stage, 0.0) + time.perf_counter() - t0
        (self.out / "logs").mkdir(exist_ok=True)
        with (self.out / "logs" / f"{stage}.log").open("a", encoding="utf-8") as f:
            f.write(f"$ python {' '.join(args)}\n{r.stdout[-20000:]}\n{r.stderr[-20000:]}\nexit {r.returncode}\n")
        if r.returncode != 0:
            raise RuntimeError(f"{stage}: {' '.join(args)} failed (exit {r.returncode}); see logs/{stage}.log")

    def add(self, stage: str, name: str, ref: Path, new: Path, ignore: str | None = None) -> None:
        st, det = compare(ref, new, ignore)
        self.rows.append({"stage": stage, "artifact": name, "status": st, "detail": det,
                          "sha256_committed": sha(ref)[:16] if ref.exists() else "", "sha256_regenerated": sha(new)[:16] if new.exists() else ""})
        print(f"[{stage}] {name}: {st} ({det[:100]})", flush=True)

    def check(self, stage: str, name: str, ok: bool, detail: str) -> None:
        self.rows.append({"stage": stage, "artifact": name, "status": "identical" if ok else "DIFFERENT", "detail": detail, "sha256_committed": "", "sha256_regenerated": ""})
        print(f"[{stage}] {name}: {'ok' if ok else 'DIFFERENT'} ({detail[:100]})", flush=True)


def cur(base: Path, phase: str) -> Path:
    return base / "results" / phase / (base / "results" / phase / ".current_run").read_text(encoding="utf-8").strip()


def set_cur(base: Path, phase: str, rid: str) -> None:
    (base / "results" / phase / ".current_run").write_text(rid, encoding="utf-8")


def env_check() -> dict:
    lock = {}
    for line in (ROOT / "requirements.lock").read_text(encoding="utf-8").splitlines():
        if "==" in line and not line.startswith("#"):
            k, v = line.split("==", 1)
            lock[k.strip().lower().replace("_", "-")] = v.strip()
    fr = subprocess.run([PY, "-m", "pip", "freeze"], capture_output=True, text=True).stdout.splitlines()
    have = {}
    for line in fr:
        if "==" in line:
            k, v = line.split("==", 1)
            have[k.strip().lower().replace("_", "-")] = v.strip()
    mism = {k: {"lock": v, "installed": have.get(k)} for k, v in lock.items() if have.get(k) != v}
    return {"interpreter": PY, "locked_packages": len(lock), "mismatches": mism, "extra_installed_not_in_lock": sorted(set(have) - set(lock))}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--dest", default=str(Path(tempfile.gettempdir()) / "qrag_cleanroom"))
    ap.add_argument("--keep", action="store_true")
    a = ap.parse_args()
    out = ROOT / "results" / "phase9" / a.run_id
    out.mkdir(parents=True, exist_ok=True)
    if (out / "logs").exists():
        shutil.rmtree(out / "logs")
    dest = Path(a.dest)
    if dest.exists():
        shutil.rmtree(dest)
    t_all = time.perf_counter()
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    subprocess.run(["git", "clone", "--quiet", "--no-hardlinks", str(ROOT), str(dest)], check=True)
    R = Room(dest, out)
    rid = "cleanroom_" + a.run_id

    # 0. FINDINGS.md regenerates byte-identically from the committed artifacts
    ref_findings = dest / "FINDINGS.committed.md"
    shutil.copyfile(dest / "FINDINGS.md", ref_findings)
    R.run("report", "scripts/report.py")
    R.add("report", "FINDINGS.md regenerated from committed artifacts", ref_findings, dest / "FINDINGS.md")

    # 1. raw data (copied, then verified against the committed checksums)
    shutil.copytree(ROOT / "data" / "raw", dest / "data" / "raw")
    sums = json.loads((dest / "data" / "squad_v1.1.checksums.json").read_text(encoding="utf-8"))
    for name, meta in sums.items():
        p = dest / "data" / "raw" / "squad_v1.1" / name
        R.check("data", f"SQuAD {name} sha256", sha(p) == meta["sha256"], f"expected {meta['sha256'][:16]}")

    # 2. Phase 1 corpus, eval set, ladder
    p1_ref = cur(dest, "phase1")
    R.run("phase1", "scripts/run_phase1.py", "--run-id", f"phase1_{rid}", "--steps", "corpus")
    p1_new = dest / "results" / "phase1" / f"phase1_{rid}"
    for f in ("eval_set.json", "ladder_N.json"):
        st = subprocess.run(["git", "diff", "--quiet", "--", f"data/{f}"], cwd=dest).returncode
        R.check("phase1", f"data/{f} rebuilt from SQuAD", st == 0, "git diff against committed file: " + ("no change" if st == 0 else "CHANGED"))
    R.check("phase1", "data/paragraphs.jsonl (git-ignored) rebuilt", sha(dest / "data" / "paragraphs.jsonl") == sha(ROOT / "data" / "paragraphs.jsonl"), "sha256 vs this working tree")
    R.add("phase1", "corpus_stats.json", p1_ref / "corpus_stats.json", p1_new / "corpus_stats.json")

    # 3. embeddings: small-config re-embed, then the stored full arrays
    code = ("import json,sys,numpy as np; sys.path.insert(0,'.'); from qrag import embed as E\n"
            "P=[json.loads(l) for l in open('data/paragraphs.jsonl',encoding='utf-8')]; L=json.load(open('data/ladder_N.json',encoding='utf-8'))['rungs']['1000']\n"
            "Q=json.load(open('data/eval_set.json',encoding='utf-8')); m=E.load_model()\n"
            "np.save('emb_check_q.npy',E.embed_texts(m,[q['question'] for q in Q])); np.save('emb_check_p.npy',E.embed_texts(m,[P[i]['text'] for i in L])); np.save('emb_check_idx.npy',np.array(L))\n")
    R.run("embed", "-c", code)
    qn, pn, idx = np.load(dest / "emb_check_q.npy"), np.load(dest / "emb_check_p.npy"), np.load(dest / "emb_check_idx.npy")
    qo, po = np.load(ROOT / "data" / "emb_queries.npy"), np.load(ROOT / "data" / "emb_paragraphs.npy")[idx]
    for nm, x, y in (("300 query embeddings", qn, qo), ("1000-rung paragraph embeddings", pn, po)):
        d = float(np.abs(x - y).max())
        cosmin = float((x * y).sum(1).min())
        R.check("embed", nm + " re-embedded vs stored", d < 1e-4 and cosmin > 0.99999, f"max abs diff {d:.2e}, min cosine {cosmin:.7f}")
    for f in ("emb_paragraphs.npy", "emb_queries.npy", "emb_paragraphs_512.npy", "emb_queries_512.npy"):
        shutil.copyfile(ROOT / "data" / f, dest / "data" / f)

    # 4a. Phase 1 ground truth + sanity
    R.run("phase1", "scripts/run_phase1.py", "--run-id", f"phase1_{rid}", "--steps", "groundtruth", "sanity")
    for n in ("1000", "2000", "5000", "10000", "all"):
        R.add("phase1", f"ground_truth_N{n}.npz", p1_ref / f"ground_truth_N{n}.npz", p1_new / f"ground_truth_N{n}.npz")
    for f in ("ceiling_by_N.csv", "sanity.json", "gold_cosine.csv"):
        R.add("phase1", f, p1_ref / f, p1_new / f)

    # 4b. Phase 2 quality (FAISS Flat + IVF, seeded k-means)
    p2_ref = cur(dest, "phase2")
    R.run("phase2", "scripts/run_phase2.py", "--run-id", f"phase2_{rid}", "--steps", "quality")
    p2_new = dest / "results" / "phase2" / f"phase2_{rid}"
    for f in ("quality.csv", "best_nprobe.json", "flat_vs_numpy_check.json"):
        R.add("phase2", f, p2_ref / f, p2_new / f)

    # 4c. Phase 3: Tier A validation, Tier B retrieval (all N, M, S, 5 seeds), summary, Tier A end-to-end
    p3_ref = cur(dest, "phase3")
    R.run("phase3", "scripts/run_phase3.py", "--run-id", f"phase3_{rid}", "--steps", "validate", "retrieval", "summarize", "tierA_e2e")
    p3_new = dest / "results" / "phase3" / f"phase3_{rid}"
    for f in ("validation.json", "validation_pairs.csv", "f2_error_vs_shots.csv", "negative_cosine_audit.json", "retrieval_metrics.csv", "shot_thresholds.csv", "tierA_e2e.csv", "tierA_e2e_summary.json"):
        R.add("phase3", f, p3_ref / f, p3_new / f)
    R.add("phase3", "validation_repeated.npz", p3_ref / "validation_repeated.npz", p3_new / "validation_repeated.npz")
    local_rk = cur(ROOT, "phase3") / "rankings"
    for f in sorted((p3_new / "rankings").glob("*.npz")):
        R.add("phase3", f"rankings/{f.name} (vs this working tree; git-ignored)", local_rk / f.name, f)
    # rankings are not committed, so later stages must use the regenerated Phase 3 run; the other arms of the chain
    # use committed upstream artifacts that were just shown to be identical
    for f in ("t6_resource_counts.json", "tierA_timing.json"):
        shutil.copyfile(p3_ref / f, p3_new / f)  # carried over (not re-run here: decomposition/timing), needed by readers
    set_cur(dest, "phase3", f"phase3_{rid}")

    # 4d. Phase 4 quality, failure analysis, pre-registered tests (latency excluded)
    p4_ref = cur(dest, "phase4")
    R.run("phase4", "scripts/run_phase4.py", "--run-id", f"phase4_{rid}", "--steps", "main", "failures", "tests")
    p4_new = dest / "results" / "phase4" / f"phase4_{rid}"
    for f in ("main_table.csv", "failure_summary.json", "failure_examples.csv", "tests.csv"):
        R.add("phase4", f, p4_ref / f, p4_new / f)

    # 4e. Phase 5: prompts rebuilt from regenerated rankings -> same cache keys -> same answers; relabel; re-analyse
    p5_ref = cur(dest, "phase5")
    code5 = ("import json,sys; sys.path.insert(0,'.'); sys.path.insert(0,'scripts')\n"
             "from run_phase5 import run_matrix, N_Q\nfrom qrag.pipeline import PrecomputedRetrieval, build_record, load_paragraph_texts\nfrom qrag.generate import cache_key, MODEL, OPTIONS\n"
             f"bi=json.load(open(r'{p5_ref / 'build_info.json'}',encoding='utf-8')); ev=json.load(open('data/eval_set.json',encoding='utf-8'))[:N_Q]; tx=load_paragraph_texts(); pr=PrecomputedRetrieval(ev,len(tx))\n"
             "with open('rebuilt_prompts.jsonl','w',encoding='utf-8',newline='\\n') as f:\n"
             "  for pri,arm in run_matrix():\n"
             "    for qi,q in enumerate(ev):\n"
             "      r=build_record(arm,qi,q,pr.contexts(arm,qi),tx); f.write(json.dumps({'arm':r['arm'],'qi':qi,'context_idx':r['context_idx'],'cache_key':cache_key(bi['model'],bi['digest'],r['messages'],bi['options'])})+'\\n')\n")
    R.run("phase5", "-c", code5)
    ref_p = {(r["arm"], r["qi"]): r for r in map(json.loads, (p5_ref / "prompts.jsonl").open(encoding="utf-8"))}
    new_p = [json.loads(x) for x in (dest / "rebuilt_prompts.jsonl").open(encoding="utf-8")]
    ctx_ok = sum(ref_p[(r["arm"], r["qi"])]["context_idx"] == r["context_idx"] for r in new_p)
    key_ok = sum(ref_p[(r["arm"], r["qi"])]["cache_key"] == r["cache_key"] for r in new_p)
    R.check("phase5", "prompt contexts rebuilt from regenerated rankings", ctx_ok == len(new_p) == len(ref_p), f"{ctx_ok}/{len(new_p)} identical (committed {len(ref_p)})")
    R.check("phase5", "LLM cache keys of rebuilt prompts", key_ok == len(new_p), f"{key_ok}/{len(new_p)} identical")
    gens = [json.loads(x) for x in (p5_ref / "generations.jsonl").open(encoding="utf-8")]
    g_ok = sum(g["cache_key"] == ref_p[(g["arm"], g["qi"])]["cache_key"] for g in gens)
    R.check("phase5", "every stored answer is keyed to its prompt", g_ok == len(gens) == len(ref_p), f"{g_ok}/{len(gens)}")
    sys.path.insert(0, str(dest))
    from qrag import judge as J  # noqa: E402  (clone's copy == committed code)
    judged = {(r["arm"], int(r["qi"])): r for r in csv.DictReader((p5_ref / "judged.csv").open(encoding="utf-8"))}
    lab_ok = sum((str(J.contains_gold(g["text"], ref_p[(g["arm"], g["qi"])]["answers"])) == judged[(g["arm"], g["qi"])]["correct"]) and
                 (str(J.is_abstain(g["text"])) == judged[(g["arm"], g["qi"])]["abstained"]) for g in gens)
    R.check("phase5", "correctness / abstention relabelled from stored answers", lab_ok == len(gens), f"{lab_ok}/{len(gens)} identical")
    p5_new = dest / "results" / "phase5" / f"phase5_{rid}"
    p5_new.mkdir(parents=True)
    for f in ("judged.csv", "prompts.jsonl"):
        shutil.copyfile(p5_ref / f, p5_new / f)  # inputs of the analysis step (judge scores are re-used, not re-scored)
    R.run("phase5", "scripts/run_phase5.py", "--run-id", f"phase5_{rid}", "--steps", "analyze")
    for f in ("outcomes_by_arm.csv", "threshold_sweep.csv", "paired_tests.csv", "mediation_by_gold_in_context.csv", "controls_check.json", "audit_template.csv"):
        R.add("phase5", f, p5_ref / f, p5_new / f)

    # 4f. Phase 7 synthesis (reads the regenerated Phase 3 run and the committed Phases 2, 4-6)
    p7_ref = cur(dest, "phase7")
    R.run("phase7", "scripts/run_phase7.py", "--run-id", f"phase7_{rid}")
    p7_new = dest / "results" / "phase7" / f"phase7_{rid}"
    for f in ("combined_table.csv", "pareto_hallucination.csv", "pareto_retrieval_miss.csv", "break_even_hallucination.csv", "break_even_retrieval.csv",
              "break_even_modelled_cost.csv", "sensitivity_shortlist_M.csv", "sensitivity_tie_breaking.csv"):
        R.add("phase7", f, p7_ref / f, p7_new / f)
    R.add("phase7", "synthesis_meta.json", p7_ref / "synthesis_meta.json", p7_new / "synthesis_meta.json", ignore=r"^sources")

    # 4g. Phase 8 (all steps except the NLI judge; its scores are re-used from the committed run)
    p8_ref = cur(dest, "phase8")
    R.run("phase8", "scripts/run_phase8.py", "--run-id", f"phase8_{rid}", "--steps", "seeds", "thresholds", "examples", "audit", "threats")
    p8_new = dest / "results" / "phase8" / f"phase8_{rid}"
    for f in ("seed_robustness_outcomes.csv", "seed_robustness_retrieval.csv", "threshold_sensitivity_tests.csv", "threshold_invariance.json",
              "qualitative_examples.csv", "qualitative_category_counts.json", "audit_agreement.json"):
        R.add("phase8", f, p8_ref / f, p8_new / f)
    R.add("phase8", "threats_matrix.csv", p8_ref / "threats_matrix.csv", p8_new / "threats_matrix.csv", ignore=r"^artifact$")

    rows = R.rows
    with (out / "clean_room.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    summ = {"clone_of_commit": head, "dest": str(dest), "comparisons": len(rows),
            "identical": sum(r["status"] == "identical" for r in rows), "equal_ignoring_timing": sum(r["status"] == "equal_ignoring_timing" for r in rows),
            "equal_ignoring_line_endings": sum(r["status"] == "equal_ignoring_line_endings" for r in rows),
            "different": sum(r["status"] == "DIFFERENT" for r in rows), "missing": sum(r["status"] == "MISSING" for r in rows),
            "stage_seconds": R.durations, "total_seconds": time.perf_counter() - t_all, "environment": env_check(),
            "small_config": "embedding check on 300 queries + 1000-paragraph rung; full stored embeddings re-used afterwards",
            "excluded": ["latency/throughput (Phases 2, 4, 6): non-deterministic by nature", "LLM generation: checked via cache keys of rebuilt prompts",
                         "HHEM / NLI scoring: scores re-used", "Phase 3 timing and T6 resource decomposition", "Phase 6 containers"]}
    (out / "clean_room_summary.json").write_text(json.dumps(summ, indent=2), encoding="utf-8")
    sys.path.insert(0, str(ROOT))
    from qrag.manifest import write_run_manifest
    write_run_manifest(out, "phase9", a.run_id, seeds={"note": "all seeds as in the reproduced phases"},
                       config={"clone_of_commit": head, "comparisons": len(rows), "excluded": summ["excluded"]})
    print(json.dumps({k: v for k, v in summ.items() if k != "environment"}, indent=2))
    if not a.keep:
        shutil.rmtree(dest, ignore_errors=True)


if __name__ == "__main__":
    main()
