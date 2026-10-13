"""Phase 8 tests: kappa, hallucination indicator, artifact sanity (seed stability, examples, threats matrix, audit status)."""
import csv
import json
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import run_phase8 as P8  # noqa: E402


def test_kappa_known_values():
    a = np.array([1, 1, 0, 0, 1, 0], bool)
    assert P8.kappa(a, a) == pytest.approx(1.0)
    assert P8.kappa(a, ~a) == pytest.approx(-1.0)
    x = np.array([1, 1, 1, 0, 0, 0], bool)
    y = np.array([1, 1, 0, 0, 0, 1], bool)
    assert P8.kappa(x, y) == pytest.approx(1 / 3)


def test_hall_indicator():
    assert P8.hall({"correct": False, "abstained": False})
    assert not P8.hall({"correct": False, "abstained": True})
    assert not P8.hall({"correct": True, "abstained": False})


def phase8_dir() -> Path:
    cur = ROOT / "results" / "phase8" / ".current_run"
    if not cur.exists():
        pytest.skip("phase 8 not run")
    return ROOT / "results" / "phase8" / cur.read_text(encoding="utf-8").strip()


def rows(name: str) -> list[dict]:
    return list(csv.DictReader((phase8_dir() / name).open(encoding="utf-8")))


def test_seed_robustness_outcomes_are_proportions():
    for r in rows("seed_robustness_outcomes.csv"):
        for k in ("flip_rate_hall_indicator", "flip_rate_gold_in_context", "always_hall_all_seeds", "never_hall_any_seed", "hall_rate_seed0"):
            assert 0.0 <= float(r[k]) <= 1.0
        # always + never + flipping questions partition the 200 questions
        assert float(r["always_hall_all_seeds"]) + float(r["never_hall_any_seed"]) + float(r["flip_rate_hall_indicator"]) == pytest.approx(1.0)
        assert int(r["hall_flips_with_gold_in_context_flip"]) + int(r["hall_flips_with_gold_in_context_constant"]) == round(float(r["flip_rate_hall_indicator"]) * int(r["n_questions"]))


def test_qualitative_examples_cover_categories():
    ex = rows("qualitative_examples.csv")
    assert len(ex) == 20 and len({r["category"] for r in ex}) == 4
    for r in ex:
        assert len(r["classical_retrieved_idx"].split()) == 3 and len(r["quantum_S256_retrieved_idx"].split()) == 3


def test_threats_matrix_artifacts_exist():
    th = rows("threats_matrix.csv")
    assert len(th) >= 10
    for t in th:
        assert (ROOT / t["artifact"]).exists(), t["artifact"]
        assert t["evidence"].strip() and t["direction"].strip()


def test_audit_status_is_honest():
    a = json.loads((phase8_dir() / "audit_agreement.json").read_text(encoding="utf-8"))
    assert a["status"] in ("computed",) or a["status"].startswith("pending")
    if a["status"].startswith("pending"):
        assert a["rows_labelled"] < 10 and "correctness" not in a


def test_nli_scores_valid():
    p = phase8_dir() / "nli_scores.csv"
    if not p.exists():
        pytest.skip("nli step not run")
    for r in rows("nli_scores.csv"):
        assert 0.0 <= float(r["nli_entail_max_over_paragraphs"]) <= 1.0 and 0.0 <= float(r["hhem"]) <= 1.0
