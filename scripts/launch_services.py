"""No-container fallback (plan D14): run the five FastAPI services as uvicorn processes on localhost, with CPU limits
approximated by psutil cpu_affinity (memory limits cannot be enforced on Windows without containers: reduced rigor).

Usage (library): ProcessStack(profile).up() / .down().   CLI: python scripts/launch_services.py small
"""
from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

import psutil

ROOT = Path(__file__).resolve().parent.parent
PROFILES = {"small": {"cpus": 1, "mem_mb": 1536}, "medium": {"cpus": 2, "mem_mb": 2048}, "large": {"cpus": 4, "mem_mb": 3072}}
SERVICES = {  # name -> (module, port, compute?)
    "embedder": ("services.embedder", 8001, True),
    "retriever-classical": ("services.retriever_classical", 8002, True),
    "retriever-quantum-sim": ("services.retriever_quantum", 8003, True),
    "generator-gateway": ("services.generator_gateway", 8004, False),
    "orchestrator": ("services.orchestrator", 8000, False),
}


class ProcessStack:
    def __init__(self, profile: str, python: str | None = None):
        self.profile, self.cfg = profile, PROFILES[profile]
        self.python = python or sys.executable
        self.procs: dict[str, subprocess.Popen] = {}

    def up(self) -> None:
        for name, (module, port, compute) in SERVICES.items():
            cpus = self.cfg["cpus"] if compute else 1
            env = {**os.environ, "QRAG_THREADS": str(cpus), "OMP_NUM_THREADS": str(cpus), "OPENBLAS_NUM_THREADS": str(cpus),
                   "DATA_DIR": str(ROOT / "data"), "PYTHONPATH": str(ROOT), "LLM_CACHE_DIR": str(ROOT / "cache" / "llm"),
                   "QRAG_EMBED_MODEL_PATH": str(ROOT / "models" / "minilm"), "HF_HUB_OFFLINE": "1"}
            self.procs[name] = subprocess.Popen([self.python, "-m", "uvicorn", f"{module}:app", "--port", str(port), "--log-level", "warning"],
                                                cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            try:  # limit the process to the first `cpus` logical CPUs (compute services) / one CPU (glue)
                psutil.Process(self.procs[name].pid).cpu_affinity(list(range(cpus)))
            except (psutil.Error, AttributeError):
                pass

    def rss_mb(self) -> dict[str, float]:
        out = {}
        for name, p in self.procs.items():
            try:
                out[name] = psutil.Process(p.pid).memory_info().rss / 1e6
            except psutil.Error:
                out[name] = float("nan")
        return out

    def down(self) -> None:
        for p in self.procs.values():
            p.terminate()
        for p in self.procs.values():
            try:
                p.wait(timeout=15)
            except subprocess.TimeoutExpired:
                p.kill()
        self.procs.clear()


if __name__ == "__main__":
    stack = ProcessStack(sys.argv[1] if len(sys.argv) > 1 else "small")
    stack.up()
    print("services starting on ports 8000-8004; Ctrl+C to stop")
    try:
        while True:
            time.sleep(5)
    except KeyboardInterrupt:
        stack.down()
