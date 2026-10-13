"""Phase 10 tests: handoff artifacts are complete and traceable."""
import csv
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


def run_dir() -> Path:
    cur = ROOT / "results" / "phase10" / ".current_run"
    if not cur.exists():
        pytest.skip("phase 10 not run")
    return ROOT / "results" / "phase10" / cur.read_text(encoding="utf-8").strip()


def rows(name):
    return list(csv.DictReader((run_dir() / name).open(encoding="utf-8")))


def test_numbers_sheet_traceable():
    nums = rows("numbers_sheet.csv")
    assert len(nums) > 100 and len({r["id"] for r in nums}) == len(nums)
    for r in nums:
        assert r["value"].strip() and (ROOT / r["artifact"]).exists(), r["id"]
    assert all((ROOT / r["artifact"]).exists() for r in rows("methods_facts.csv"))


def test_claims_have_both_sides_and_no_speedup_claim():
    c = rows("claims.csv")
    assert {r["status"] for r in c} == {"supported", "not_supported"}
    assert any("speedup" in r["claim"].lower() for r in c if r["status"] == "not_supported")
    assert not any("speedup" in r["claim"].lower() for r in c if r["status"] == "supported")


def test_figures_have_csv():
    fig = rows("figure_inventory.csv")
    assert len(fig) >= 10 and all(r["png_exists"] == "True" and r["csv_exists"] == "True" for r in fig)


def test_readme_and_docs_present_and_honest():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "No quantum speedup is claimed" in readme and "mermaid" in readme
    for p in ("docs/manuscript_source_notes.md", "docs/seminar_summary.md"):
        assert (ROOT / p).exists()
    assert len(list((ROOT / "docs" / "seminar").glob("*.png"))) >= 6


def test_archive_info():
    a = json.loads((run_dir() / "archive_info.json").read_text(encoding="utf-8"))
    assert a["files"] > 100 and a["bytes"] > 1e6
