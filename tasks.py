"""Cross-platform task runner (no `make` needed on Windows).

Usage: python tasks.py <task> [<task> ...]
Tasks: setup | env | data | bench | embed | test | report | figures | phase0 .. phase10
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


def latest_phase() -> str:
    """Highest phase that has a current run (its run dir receives the pytest junit report)."""
    for i in range(10, -1, -1):
        if (ROOT / "results" / f"phase{i}" / ".current_run").exists():
            return f"phase{i}"
    return "phase0"


def test() -> None:
    ph = latest_phase()
    run(py(), "-m", "pytest", "-q", f"--junitxml=results/{ph}/{run_id(ph)}/pytest_junit.xml")


def figures() -> None:
    run(py(), "scripts/make_figures.py")


def phase3() -> None:
    run(py(), "scripts/run_phase3.py", "--run-id", run_id("phase3"))
    figures()
    test()
    report()


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
         "phase0": phase0, "phase1": phase1, "phase2": phase2, "phase3": phase3, "figures": figures}
for _i in range(4, 11):
    TASKS[f"phase{_i}"] = not_yet(f"phase{_i}")


def main(argv: list[str]) -> None:
    if not argv or any(a not in TASKS for a in argv):
        raise SystemExit(__doc__)
    for a in argv:
        TASKS[a]()


if __name__ == "__main__":
    main(sys.argv[1:])
