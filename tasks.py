"""Cross-platform task runner (no `make` needed on Windows).

Usage: python tasks.py <task> [<task> ...]
Tasks: setup | env | data | bench | embed | test | report | phase0 .. phase10
"""
from __future__ import annotations

import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENV_PY = ROOT / ".venv" / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
CURRENT_RUN = ROOT / "results" / "phase0" / ".current_run"


def run(*args: str) -> None:
    print("$", " ".join(args), flush=True)
    subprocess.run(list(args), cwd=ROOT, check=True)


def py() -> str:
    return str(VENV_PY if VENV_PY.exists() else sys.executable)


def run_id() -> str:
    """Phase-0 run id: reuse the current one if set, else create a new one."""
    if CURRENT_RUN.exists():
        return CURRENT_RUN.read_text(encoding="utf-8").strip()
    rid = "phase0_" + datetime.now().strftime("%Y%m%d_%H%M%S")
    CURRENT_RUN.parent.mkdir(parents=True, exist_ok=True)
    CURRENT_RUN.write_text(rid, encoding="utf-8")
    return rid


def setup() -> None:
    if not VENV_PY.exists():
        run(sys.executable, "-m", "venv", ".venv")
    run(py(), "-m", "pip", "install", "--upgrade", "pip")
    run(py(), "-m", "pip", "install", "-r", "requirements.lock")
    run(py(), "-m", "pip", "check")


def env() -> None:
    run(py(), "scripts/env_report.py", "--run-id", run_id())


def data() -> None:
    run(py(), "scripts/download_squad.py", "--run-id", run_id())


def bench() -> None:
    run(py(), "scripts/bench_generator.py", "--run-id", run_id())


def test() -> None:
    run(py(), "-m", "pytest", "-q", f"--junitxml=results/phase0/{run_id()}/pytest_junit.xml")


def report() -> None:
    run(py(), "scripts/report.py")


def embed() -> None:
    raise SystemExit("embed is implemented in Phase 1 (not yet available)")


def not_yet(name: str):
    def _f() -> None:
        raise SystemExit(f"{name} is not implemented yet (later phase)")
    return _f


def phase0() -> None:
    for f in (env, data, bench, test, report):
        f()


TASKS = {"setup": setup, "env": env, "data": data, "bench": bench, "test": test, "report": report, "embed": embed,
         "phase0": phase0}
for _i in range(1, 11):
    TASKS[f"phase{_i}"] = not_yet(f"phase{_i}")


def main(argv: list[str]) -> None:
    if not argv or any(a not in TASKS for a in argv):
        raise SystemExit(__doc__)
    for a in argv:
        TASKS[a]()


if __name__ == "__main__":
    main(sys.argv[1:])
