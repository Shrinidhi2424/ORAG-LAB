"""Task 0.4 / H2: generator benchmark gate. CPU-only Ollama, 10 fixed RAG-style prompts.

Writes results/phase0/<run_id>/generator_bench.csv (per-prompt rows),
generator_bench_summary.json (per-model summary + decision) and run_manifest.json.
"""
from __future__ import annotations

import argparse
import csv
import json
import random
import re
import statistics
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import ollama  # noqa: E402
import psutil  # noqa: E402

from qrag.manifest import write_run_manifest  # noqa: E402
from qrag.seed import set_global_seed  # noqa: E402

CANDIDATES = ["qwen2.5:1.5b-instruct", "llama3.2:1b", "llama3.2:3b"]
SIZE_ORDER = {"llama3.2:1b": 1, "qwen2.5:1.5b-instruct": 2, "llama3.2:3b": 3}  # H2 order: larger preferred
SYSTEM = ("You answer questions using ONLY the provided context. If the context does not contain the answer, "
          "reply exactly: I cannot find the answer in the provided context.")
ABSTAIN = re.compile(r"cannot find the answer", re.I)
OPTIONS = {"temperature": 0, "seed": 42, "num_ctx": 2048, "num_predict": 48, "num_gpu": 0}
N_PROMPTS, N_NO_GOLD = 10, 3


def normalize(s: str) -> str:
    s = re.sub(r"\b(a|an|the)\b", " ", re.sub(r"[^\w\s]", "", s.lower()))
    return " ".join(s.split())


def build_prompts(seed: int = 42) -> list[dict]:
    rng = random.Random(seed)
    dev = json.loads((ROOT / "data/raw/squad_v1.1/dev-v1.1.json").read_text(encoding="utf-8"))
    paras = [p for a in dev["data"] for p in a["paragraphs"]]
    prompts = []
    for i, p in enumerate(rng.sample(paras, N_PROMPTS)):
        qa = rng.choice(p["qas"])
        gold_in_ctx = i >= N_NO_GOLD
        pool = [q for q in paras if q is not p]
        ctx = [p["context"]] if gold_in_ctx else []
        ctx += [q["context"] for q in rng.sample(pool, 3 - len(ctx))]
        rng.shuffle(ctx)
        user = ("Context:\n" + "\n".join(f"[{j + 1}] {c}" for j, c in enumerate(ctx))
                + f"\n\nQuestion: {qa['question']}\nAnswer concisely (a few words or one sentence).")
        prompts.append({"id": i, "gold_in_context": gold_in_ctx, "question": qa["question"],
                        "answers": [a["text"] for a in qa["answers"]], "user": user})
    return prompts


class RamSampler(threading.Thread):
    """Samples summed RSS of all ollama processes and system memory/swap every 0.25 s."""

    def __init__(self):
        super().__init__(daemon=True)
        self.stop_evt = threading.Event()
        self.peak_rss = 0
        self.avail0 = self.min_avail = psutil.virtual_memory().available
        self.swap0 = psutil.swap_memory().used
        self.peak_swap = self.swap0

    def run(self):
        while not self.stop_evt.is_set():
            rss = 0
            for p in psutil.process_iter(["name", "memory_info"]):
                try:
                    if "ollama" in (p.info["name"] or "").lower():
                        mi = p.info["memory_info"]
                        rss += getattr(mi, "wset", mi.rss)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            self.peak_rss = max(self.peak_rss, rss)
            self.min_avail = min(self.min_avail, psutil.virtual_memory().available)
            self.peak_swap = max(self.peak_swap, psutil.swap_memory().used)
            self.stop_evt.wait(0.25)


def bench_model(model: str, prompts: list[dict]) -> tuple[list[dict], dict]:
    client = ollama.Client()
    meta = client.show(model)
    digest = next((m.digest for m in client.list().models if m.model == model), None)
    msgs = lambda u: [{"role": "system", "content": SYSTEM}, {"role": "user", "content": u}]  # noqa: E731
    sampler = RamSampler()
    sampler.start()
    t0 = time.perf_counter()
    client.chat(model=model, messages=msgs(prompts[0]["user"]), options=OPTIONS, keep_alive="10m")
    warmup_s = time.perf_counter() - t0  # discarded from stats; includes model load
    ps_view = [{"name": m.model, "size": m.size, "size_vram": m.size_vram} for m in client.ps().models]
    rows = []
    for pr in prompts:
        t0 = time.perf_counter()
        r = client.chat(model=model, messages=msgs(pr["user"]), options=OPTIONS, keep_alive="10m")
        wall = time.perf_counter() - t0
        out = r.message.content.strip()
        abstained = bool(ABSTAIN.search(out))
        clean = bool(out) and (abstained or len(out.split()) <= 30) and r.done_reason == "stop"
        correct = any(normalize(a) in normalize(out) for a in pr["answers"] if normalize(a))
        rows.append({
            "model": model, "prompt_id": pr["id"], "gold_in_context": pr["gold_in_context"],
            "wall_s": round(wall, 3), "prompt_tokens": r.prompt_eval_count, "gen_tokens": r.eval_count,
            "prompt_eval_s": round(r.prompt_eval_duration / 1e9, 3), "eval_s": round(r.eval_duration / 1e9, 3),
            "tokens_per_s": round(r.eval_count / (r.eval_duration / 1e9), 2) if r.eval_duration else None,
            "done_reason": r.done_reason, "abstained": abstained, "clean": clean, "correct": correct,
            "output": out.replace("\n", " "),
        })
    sampler.stop_evt.set()
    sampler.join()
    client.generate(model=model, prompt="", keep_alive=0)  # unload (H5)
    walls = [r["wall_s"] for r in rows]
    summ = {
        "model": model, "digest": digest, "ollama_details": str(meta.details),
        "warmup_incl_load_s": round(warmup_s, 2),
        "median_wall_s": round(statistics.median(walls), 3),
        "p95_wall_s": round(sorted(walls)[int(0.95 * (len(walls) - 1))], 3),
        "median_tokens_per_s": round(statistics.median(r["tokens_per_s"] for r in rows if r["tokens_per_s"]), 2),
        "median_prompt_tokens": statistics.median(r["prompt_tokens"] for r in rows),
        "median_prompt_eval_s": round(statistics.median(r["prompt_eval_s"] for r in rows), 3),
        "peak_ollama_rss_gb": round(sampler.peak_rss / 1e9, 3),
        "system_ram_delta_gb": round((sampler.avail0 - sampler.min_avail) / 1e9, 3),
        "ollama_ps_size_gb": round(max((m["size"] for m in ps_view), default=0) / 1e9, 3),
        "min_system_available_gb": round(sampler.min_avail / 1e9, 3),
        "swap_used_delta_mb": round((sampler.peak_swap - sampler.swap0) / 1e6, 1),
        "clean_count": sum(r["clean"] for r in rows), "correct_count_info": sum(r["correct"] for r in rows),
        "ps_after_warmup": ps_view,
    }
    summ["pass_a_median_le_10s"] = summ["median_wall_s"] <= 10
    # RSS under-reports mmap-ed weights, so (b) uses the largest of: process working set,
    # system free-RAM drop during the run, and the model size Ollama reports in `ps`.
    summ["ram_metric_gb"] = max(summ["peak_ollama_rss_gb"], summ["system_ram_delta_gb"], summ["ollama_ps_size_gb"])
    summ["pass_b_ram_le_2.5gb"] = summ["ram_metric_gb"] <= 2.5
    summ["pass_c_clean_ge_8"] = summ["clean_count"] >= 8
    summ["passes_gate"] = all(summ[k] for k in ("pass_a_median_le_10s", "pass_b_ram_le_2.5gb", "pass_c_clean_ge_8"))
    return rows, summ


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--models", nargs="*", default=CANDIDATES)
    args = ap.parse_args()
    set_global_seed(42)
    out_dir = ROOT / "results" / "phase0" / args.run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    prompts = build_prompts()
    all_rows, summaries = [], []
    for model in args.models:
        print(f"== benchmarking {model}", flush=True)
        rows, summ = bench_model(model, prompts)
        all_rows += rows
        summaries.append(summ)
        print(json.dumps({k: v for k, v in summ.items() if k != "ps_after_warmup"}), flush=True)
    passing = [s for s in summaries if s["passes_gate"]]
    chosen = max(passing, key=lambda s: SIZE_ORDER[s["model"]])["model"] if passing else None
    with (out_dir / "generator_bench.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(all_rows[0]))
        w.writeheader()
        w.writerows(all_rows)
    (out_dir / "generator_bench_summary.json").write_text(
        json.dumps({"options": OPTIONS,
                    "decision_rule": "largest passing (a) median<=10s (b) peak RAM<=2.5GB (c) >=8/10 clean",
                    "chosen": chosen, "models": summaries}, indent=2), encoding="utf-8")
    write_run_manifest(out_dir, "phase0", args.run_id, seeds={"global": 42, "prompts": 42, "ollama": 42},
                       config={"task": "bench_generator", "options": OPTIONS, "models": args.models})
    print("CHOSEN:", chosen)


if __name__ == "__main__":
    main()
