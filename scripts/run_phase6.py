"""Phase 6: cloud-native deployment measurements (HTTP latency layer, concurrency, memory, end-to-end smoke test).

Usage: python scripts/run_phase6.py --run-id <id> [--client in_network|host_port] [--backend auto|docker|process]
                                    [--profiles small medium large] [--steps bench smoke]
Client modes (decided after a diagnostic, see FINDINGS Deviations):
  in_network : the load generator runs in a container on the stack's Docker network (cloud-like service-to-service path) [primary]
  host_port  : the load generator runs on the Windows host and goes through Docker Desktop's published port
               (on this machine this path adds an artefactual ~45 ms to keep-alive POSTs with a body)
Backends: docker compose (primary) or uvicorn processes with cpu_affinity (documented fallback; host_port client only).
The LLM (Ollama) must be idle/unloaded for the benchmark; the smoke test runs last, separately (H6).
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path

import httpx
import psutil

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import http_bench as HB  # noqa: E402
from launch_services import PROFILES, ProcessStack  # noqa: E402

from qrag.manifest import write_run_manifest  # noqa: E402
from qrag.seed import set_global_seed  # noqa: E402

ORCH = "http://localhost:8000"
HEALTH = {"embedder": 8001, "retriever-classical": 8002, "retriever-quantum-sim": 8003, "orchestrator": 8000}
PROJECT = "qraglab"
NETWORK = f"{PROJECT}_default"


def jdump(p: Path, o) -> None:
    p.write_text(json.dumps(o, indent=2, ensure_ascii=False), encoding="utf-8")


def read_csv(p: Path) -> list[dict]:
    with p.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for r in rows:  # restore numeric types for re-summarising
        for k, v in r.items():
            if k in ("status", "repeat", "query_i"):
                r[k] = int(v)
            elif k not in ("profile", "client", "arm", "N", "clients") and v not in ("",):
                try:
                    r[k] = float(v)
                except ValueError:
                    pass
    return rows


def sh(cmd: list[str], timeout: int = 600) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=timeout, encoding="utf-8", errors="replace")


# ----------------------------------------------------------------------------------------------------------- stacks

def parse_mem(s: str) -> float:
    m = re.match(r"([\d.]+)\s*([KMG]i?B)", s.strip())
    return float("nan") if not m else float(m.group(1)) * {"KiB": 1 / 1024, "KB": 1 / 1000, "MiB": 1, "MB": 1, "GiB": 1024, "GB": 1000}[m.group(2)]


class DockerStack:
    kind = "docker"

    def __init__(self, profile: str):
        self.profile = profile
        self.base = ["docker", "compose", "-p", PROJECT, "--env-file", f"configs/profiles/{profile}.env"]

    def up(self) -> None:
        r = sh(self.base + ["up", "-d", "--wait", "--force-recreate", "--timeout", "300"], timeout=900)
        if r.returncode != 0:
            raise RuntimeError(f"docker compose up failed: {r.stderr[-800:]}")

    def down(self) -> None:
        sh(self.base + ["down", "--timeout", "30"], timeout=300)

    def mem(self) -> dict[str, tuple[float, float]]:
        r = sh(["docker", "stats", "--no-stream", "--format", "{{.Name}}|{{.MemUsage}}"], timeout=60)
        out = {}
        for line in r.stdout.splitlines():
            name, usage = line.split("|", 1)
            if name.startswith(PROJECT + "-"):
                used, limit = usage.split("/")
                out[name[len(PROJECT) + 1 : -2]] = (parse_mem(used), parse_mem(limit))
        return out

    def logs_sample(self) -> str:
        return sh(self.base + ["logs", "--no-color", "--tail", "6"], timeout=60).stdout


class ProcStack(ProcessStack):
    kind = "process"

    def mem(self) -> dict[str, tuple[float, float]]:
        return {k: (v, float("nan")) for k, v in self.rss_mb().items()}

    def logs_sample(self) -> str:
        return "(process backend: service stdout is discarded)"


def wait_ready(timeout: float = 300.0) -> float:
    t0 = time.perf_counter()
    with httpx.Client(timeout=5.0) as c:
        while time.perf_counter() - t0 < timeout:
            try:
                if all(c.get(f"http://localhost:{p}/health").json().get("ready") for p in HEALTH.values()):
                    return time.perf_counter() - t0
            except (httpx.HTTPError, ValueError):
                pass
            time.sleep(1.0)
    raise TimeoutError("stack did not become ready")


def docker_ok() -> bool:
    try:
        return sh(["docker", "info", "--format", "{{.ServerVersion}}"], timeout=30).returncode == 0
    except Exception:  # noqa: BLE001
        return False


class MemSampler(threading.Thread):
    def __init__(self, stack):
        super().__init__(daemon=True)
        self.stack, self.stop_evt, self.peak = stack, threading.Event(), {}

    def run(self):
        while not self.stop_evt.is_set():
            for k, (used, _) in self.stack.mem().items():
                self.peak[k] = max(self.peak.get(k, 0.0), used)
            self.stop_evt.wait(0.5)


def hygiene(backend: str, client: str) -> dict:
    bat = psutil.sensors_battery()
    h = {"backend": backend, "client": client, "power_plugged": None if bat is None else bool(bat.power_plugged), "battery_percent": None if bat is None else bat.percent,
         "power_scheme": sh(["powercfg", "/getactivescheme"], 15).stdout.strip(), "host_free_ram_gb_at_start": psutil.virtual_memory().available / 1e9,
         "cpu_temperature": "not monitored; cpu_freq at repeat boundaries logged (not available inside containers)",
         "load_generator": "container on the stack's Docker network" if client == "in_network" else "Windows host through the published port",
         "interleaving": "arm x N conditions shuffled per repeat (seeded)", "warmup_requests_discarded_per_condition": HB.N_WARMUP,
         "timed_requests_per_condition_per_repeat": HB.N_TIMED, "repeats": HB.N_REPEATS}
    if backend == "docker":
        h["docker_server"] = sh(["docker", "info", "--format", "{{.ServerVersion}}"], 30).stdout.strip()
        h["docker_vm_mem_gb"] = float(sh(["docker", "info", "--format", "{{.MemTotal}}"], 30).stdout.strip() or 0) / 1e9
        h["other_running_containers_untouched"] = [x for x in sh(["docker", "ps", "--format", "{{.Names}}|{{.Image}}"], 30).stdout.split() if not x.startswith(PROJECT)]
        wc = Path.home() / ".wslconfig"
        h["wslconfig"] = wc.read_text(encoding="utf-8") if wc.exists() else None
    ollama = shutil.which("ollama") or str(Path.home() / "AppData/Local/Programs/Ollama/ollama.exe")
    try:
        h["ollama_loaded_models"] = sh([ollama, "ps"], 15).stdout.strip()
    except Exception as e:  # noqa: BLE001
        h["ollama_loaded_models"] = f"unavailable: {e}"
    return h


# ----------------------------------------------------------------------------------------------------------- benchmark

def bench_profile(out: Path, backend: str, client: str, profile: str, stack) -> tuple[list[dict], list[dict], list[dict], list[dict]]:
    idle = stack.mem()
    sampler = MemSampler(stack)
    sampler.start()
    try:
        if client == "host_port":
            qs = HB.questions(ROOT / "data", HB.N_WARMUP + HB.N_TIMED)
            raw, freq = HB.run_latency(ORCH, profile, client, qs)
            conc = HB.run_concurrency(ORCH, profile, client, qs)
        else:
            tmp = out / f"_tmp_{profile}"
            tmp.mkdir(exist_ok=True)
            cmd = ["docker", "run", "--rm", "--network", NETWORK, "-v", f"{ROOT}:/repo:ro", "-v", f"{tmp}:/out", "-w", "/repo", "qrag-light:latest", "python",
                   "scripts/http_bench.py", "--base", "http://orchestrator:8000", "--profile", profile, "--client", client, "--out", "/out", "--data", "/repo/data"]
            print("running client container:", " ".join(cmd[:8]), "...", flush=True)
            p = subprocess.Popen(cmd, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
            for line in p.stdout:
                print(line.rstrip(), flush=True)
            if p.wait() != 0:
                raise RuntimeError("client container failed")
            raw, freq, conc = read_csv(tmp / "latency_raw.csv"), json.loads((tmp / "cpu_freq_per_repeat.json").read_text(encoding="utf-8")), read_csv(tmp / "concurrency.csv")
            shutil.rmtree(tmp)
    finally:
        sampler.stop_evt.set()
        sampler.join()
    mem = [{"profile": profile, "client": client, "backend": backend, "service": svc, "idle_mb": used, "peak_during_load_mb": sampler.peak.get(svc, float("nan")), "limit_mb": limit}
           for svc, (used, limit) in idle.items()]
    return raw, freq, conc, mem


def step_smoke(out: Path, backend: str) -> dict:
    ev = json.loads((ROOT / "data" / "eval_set.json").read_text(encoding="utf-8"))
    run5 = ROOT / "results" / "phase5" / (ROOT / "results/phase5/.current_run").read_text(encoding="utf-8").strip()
    stored = {(g["arm"], g["qi"]): g["text"] for g in map(json.loads, (run5 / "generations.jsonl").open(encoding="utf-8"))}
    try:
        ollama_up = httpx.get("http://localhost:11434/api/tags", timeout=5).status_code == 200
    except httpx.HTTPError:
        ollama_up = False
    cases = [("classical_N5000_parity", 0, {"arm": "classical", "N": "5000"}), ("classical_N5000_parity", 1, {"arm": "classical", "N": "5000"}),
             ("classical_N5000_parity", 2, {"arm": "classical", "N": "5000"}),
             ("quantum_N5000_S1024", 0, {"arm": "quantum", "N": "5000", "M": 50, "shots": 1024, "seed": 0}),
             ("novel_question_classical_all", None, {"arm": "classical", "N": "all"})]
    results = []
    with httpx.Client(base_url=ORCH, timeout=300.0) as c:
        for name, qi, extra in cases:
            q = ev[qi]["question"] if qi is not None else "What is the capital city of the Indian state of Karnataka?"
            t0 = time.perf_counter()
            r = c.post("/rag", json={"question": q, "k": 3, **extra})
            wall = time.perf_counter() - t0
            row = {"case": name, "qi": qi, "status": r.status_code, "wall_s": wall, "question": q}
            if r.status_code == 200:
                b = r.json()
                row.update({"answer": b["answer"], "answer_cached": b["answer_cached"], "n_contexts": len(b["contexts"]), "context_idx": [x["idx"] for x in b["contexts"]], "timings": b["timings"]})
                if name.startswith("classical_N5000_parity"):
                    row["equals_phase5_stored_answer"] = b["answer"] == stored.get(("classical_N5000_k3", qi))
            else:
                row["detail"] = r.text[:300]
            results.append(row)
            print(f"smoke {name}: {r.status_code} cached={row.get('answer_cached')} {wall:.1f}s", flush=True)
    summ = {"backend": backend, "ollama_reachable_on_host": ollama_up, "cases": results, "all_ok": all(x["status"] == 200 for x in results),
            "parity_cases_equal": [x.get("equals_phase5_stored_answer") for x in results if "equals_phase5_stored_answer" in x]}
    jdump(out / "smoke_test.json", summ)
    return summ


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--client", default="in_network", choices=["in_network", "host_port"])
    ap.add_argument("--backend", default="auto", choices=["auto", "docker", "process"])
    ap.add_argument("--profiles", nargs="+", default=["small", "medium", "large"])
    ap.add_argument("--steps", nargs="+", default=["bench"], choices=["bench", "smoke", "images"])
    args = ap.parse_args()
    set_global_seed(42)
    out = ROOT / "results" / "phase6" / args.run_id
    out.mkdir(parents=True, exist_ok=True)
    backend = args.backend if args.backend != "auto" else ("docker" if docker_ok() else "process")
    client = args.client if backend == "docker" else "host_port"
    print("backend:", backend, "client:", client, flush=True)
    jdump(out / "hygiene.json", hygiene(backend, client))
    raw_all, freq_all, conc_all, mem_all, startup = [], [], [], [], []
    for profile in args.profiles if "bench" in args.steps else []:
        stack = DockerStack(profile) if backend == "docker" else ProcStack(profile)
        t0 = time.perf_counter()
        stack.up()
        ready_s = wait_ready()
        startup.append({"profile": profile, "backend": backend, "compose_up_s": time.perf_counter() - t0 - ready_s, "extra_wait_until_all_ready_s": ready_s})
        print(f"[{profile}] stack up in {time.perf_counter() - t0:.1f} s (ready after {ready_s:.1f} s)", flush=True)
        (out / f"stack_logs_sample_{profile}.txt").write_text(stack.logs_sample(), encoding="utf-8")
        try:
            raw, freq, conc, mem = bench_profile(out, backend, client, profile, stack)
            raw_all += raw
            freq_all += freq
            conc_all += conc
            mem_all += mem
        finally:
            stack.down()
    if startup:
        HB.write_csv(out / "startup.csv", startup)
    if backend == "docker":
        imgs = sh(["docker", "images", "--filter", "reference=qrag-*", "--format", "{{.Repository}}:{{.Tag}}|{{.Size}}"], 30).stdout.split()
        jdump(out / "docker_images.json", dict(x.split("|") for x in imgs))
    if raw_all:
        HB.write_csv(out / "latency_raw.csv", raw_all)
        HB.write_csv(out / "latency_summary.csv", HB.summarize_latency(raw_all))
        jdump(out / "cpu_freq_per_repeat.json", freq_all)
        HB.write_csv(out / "concurrency.csv", conc_all)
        HB.write_csv(out / "memory.csv", mem_all)
    if "smoke" in args.steps:
        stack = DockerStack("medium") if backend == "docker" else ProcStack("medium")
        stack.up()
        wait_ready()
        try:
            step_smoke(out, backend)
        finally:
            stack.down()
    write_run_manifest(out, "phase6", args.run_id, seeds={"global": 42, "repeat_order": "42+repeat", "quantum_service": "per (seed, query vector)"},
                       config={"backend": backend, "client": client, "profiles": args.profiles, "steps": args.steps, "Ns": list(HB.NS), "arms": HB.ARMS, "repeats": HB.N_REPEATS,
                               "warmup": HB.N_WARMUP, "timed": HB.N_TIMED, "concurrency_levels": list(HB.CONC_LEVELS), "concurrency_requests": HB.CONC_REQUESTS,
                               "profiles_cfg": PROFILES})


if __name__ == "__main__":
    main()
