"""Run manifest writer (R2): git hash, seeds, versions, host, time."""
from __future__ import annotations

import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path

import psutil

ROOT = Path(__file__).resolve().parent.parent
TRACKED_PACKAGES = [
    "numpy", "scipy", "pandas", "faiss-cpu", "sentence-transformers", "torch",
    "transformers", "qiskit", "qiskit-aer", "fastapi", "uvicorn", "httpx",
    "pydantic", "pytest", "matplotlib", "pyyaml", "datasets", "ollama", "psutil",
]


def git_info() -> dict:
    def run(*args: str) -> str:
        try:
            return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
        except (subprocess.CalledProcessError, FileNotFoundError):
            return ""

    return {
        "commit": run("rev-parse", "HEAD") or None,
        "dirty": bool(run("status", "--porcelain")),
    }


def package_versions(names=TRACKED_PACKAGES) -> dict:
    out = {}
    for n in names:
        try:
            out[n] = metadata.version(n)
        except metadata.PackageNotFoundError:
            out[n] = None
    return out


def host_info() -> dict:
    return {
        "os": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "cpu_physical_cores": psutil.cpu_count(logical=False),
        "cpu_logical_cores": psutil.cpu_count(logical=True),
        "ram_total_bytes": psutil.virtual_memory().total,
        "python": sys.version.split()[0],
    }


def build_manifest(phase: str, run_id: str, seeds: dict | None = None, config: dict | None = None) -> dict:
    return {
        "phase": phase,
        "run_id": run_id,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "git": git_info(),
        "seeds": seeds or {},
        "config": config or {},
        "host": host_info(),
        "packages": package_versions(),
    }


def write_run_manifest(run_dir: Path, phase: str, run_id: str, seeds: dict | None = None, config: dict | None = None) -> Path:
    run_dir = Path(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    path = run_dir / "run_manifest.json"
    path.write_text(json.dumps(build_manifest(phase, run_id, seeds, config), indent=2), encoding="utf-8")
    return path
