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


def run(*args: str) -> None:
    print("$", " ".join(args), flush=True)
    subprocess.run(list(args), cwd=ROOT, check=True)


def py() -> str:
    return str(VENV_PY if VENV_PY.exists() else sys.executable)


def run_id(phase: str = "phase0") -> str:
    """Run id of the current run of a phase: reuse if set, else create a new one."""
    cur = ROOT / "results" / phase / ".current_run"
    if cur.exists():
        return cur.read_text(encoding="utf-8").strip()
    rid = f"{phase}_" + datetime.now().strftime("%Y%m%d_%H%M%S")
    cur.parent.mkdir(parents=True, exist_ok=True)
    cur.write_text(rid, encoding="utf-8")
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
    run(py(), "-m", "pytest", "-q", f"--junitxml=results/phase2/{run_id('phase2')}/pytest_junit.xml" if (ROOT / "results/phase2/.current_run").exists() else f"--junitxml=results/phase1/{run_id('phase1')}/pytest_junit.xml" if (ROOT / "results/phase1/.current_run").exists() else f"--junitxml=results/phase0/{run_id()}/pytest_junit.xml")


def report() -> None:
    run(py(), "scripts/report.py")


def embed() -> None:
    """Phase 1: build corpus/ladder/eval set, embed (skips if embeddings exist), ground truth is a separate step."""
    run(py(), "scripts/run_phase1.py", "--run-id", run_id("phase1"), "--steps", "corpus", "embed")


def phase2() -> None:
    run(py(), "scripts/run_phase2.py", "--run-id", run_id("phase2"))
    test()
    report()


def phase1() -> None:
    run(py(), "scripts/run_phase1.py", "--run-id", run_id("phase1"))
    test()
    report()


def not_yet(name: str):
    def _f() -> None:
        raise SystemExit(f"{name} is not implemented yet (later phase)")
    return _f


def phase0() -> None:
    for f in (env, data, bench, test, report):
        f()


TASKS = {"setup": setup, "env": env, "data": data, "bench": bench, "test": test, "report": report, "embed": embed,
         "phase0": phase0, "phase1": phase1, "phase2": phase2}
for _i in range(3, 11):
    TASKS[f"phase{_i}"] = not_yet(f"phase{_i}")


def main(argv: list[str]) -> None:
    if not argv or any(a not in TASKS for a in argv):
        raise SystemExit(__doc__)
    for a in argv:
        TASKS[a]()


if __name__ == "__main__":
    main(sys.argv[1:])
