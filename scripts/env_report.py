"""Task 0.1: detect environment and write results/phase0/<run_id>/env.json (+ manifest)."""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import psutil  # noqa: E402

from qrag.manifest import host_info, package_versions, write_run_manifest  # noqa: E402


def run(cmd: list[str], timeout: int = 30) -> dict:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, encoding="utf-8", errors="replace")
        return {"ok": p.returncode == 0, "stdout": p.stdout.strip(), "stderr": p.stderr.strip()[:300]}
    except (OSError, subprocess.TimeoutExpired) as e:
        return {"ok": False, "stdout": "", "stderr": str(e)[:300]}


def ps(expr: str) -> str:
    return run(["powershell", "-NoProfile", "-Command", expr])["stdout"]


def ollama_exe() -> str:
    return (shutil.which("ollama") or str(Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Ollama" / "ollama.exe"))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", required=True)
    args = ap.parse_args()
    out_dir = ROOT / "results" / "phase0" / args.run_id

    gpus = [g for g in ps("(Get-CimInstance Win32_VideoController).Name").splitlines() if g.strip()]
    disk = shutil.disk_usage(ROOT)
    env = {
        "host": host_info(),
        "cpu_model": ps("(Get-CimInstance Win32_Processor).Name"),
        "gpus": gpus,
        "gpu_policy": "ignored (H3): torch CPU wheel, Ollama CPU-only",
        "disk_total_bytes": disk.total,
        "disk_free_bytes": disk.free,
        "tools": {
            "python": sys.version.split()[0],
            "git": run(["git", "--version"])["stdout"],
            "ollama": (lambda r: r["stdout"] or r["stderr"])(run([ollama_exe(), "--version"])),
            "docker_cli": run(["docker", "--version"])["stdout"],
            "docker_compose": run(["docker", "compose", "version"])["stdout"],
        },
        "docker_daemon": run(["docker", "info", "--format", "{{.ServerVersion}}"]),
        "swap_total_bytes": psutil.swap_memory().total,
        "packages": package_versions(),
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "env.json").write_text(json.dumps(env, indent=2), encoding="utf-8")
    write_run_manifest(out_dir, "phase0", args.run_id, seeds={"global": 42}, config={"task": "env_report"})
    print(f"wrote {out_dir / 'env.json'}")


if __name__ == "__main__":
    main()
