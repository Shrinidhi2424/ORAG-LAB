"""Phase 5 tests: answer normalisation, abstention, taxonomy rules, prompt/cache determinism, pipeline arms."""
import json
from pathlib import Path

import pytest

from qrag import judge as J
from qrag.generate import OPTIONS, build_messages, cache_key
from qrag.pipeline import Arm, PrecomputedRetrieval

ROOT = Path(__file__).resolve().parent.parent


def test_squad_normalisation_and_containment():
    assert J.normalize_answer("The  Eiffel-Tower!") == "eiffeltower"
    assert J.contains_gold("It was built in 1889.", ["1889"])
    assert J.contains_gold("the Denver Broncos won", ["Denver Broncos", "Broncos"])
    assert not J.contains_gold("I cannot find the answer in the provided context.", ["Paris"])


def test_abstention_regex():
    assert J.is_abstain("I cannot find the answer in the provided context.")
    assert J.is_abstain("I don't know.")
    assert not J.is_abstain("Paris")


@pytest.mark.parametrize("c,a,f,g,expected", [
    (True, True, True, True, "abstained"), (True, False, True, True, "correct_grounded"),
    (True, False, False, False, "correct_ungrounded"), (False, False, None, True, "misread"),
    (False, False, True, False, "hallucinated")])
def test_outcome_taxonomy(c, a, f, g, expected):
    assert J.outcome(c, a, f, g) == expected


def test_prompt_template_and_cache_key_deterministic():
    m = build_messages("Who?", ["ctx one", "ctx two"])
    assert m[0]["content"].endswith("I cannot find the answer in the provided context.")
    assert m[1]["content"].startswith("Context:\n[1] ctx one\n[2] ctx two\n\nQuestion: Who?")
    assert build_messages("Who?", None)[1]["content"].startswith("Question: Who?")
    k1 = cache_key("m", "d", m, OPTIONS)
    assert k1 == cache_key("m", "d", build_messages("Who?", ["ctx one", "ctx two"]), OPTIONS)
    assert k1 != cache_key("m", "d", build_messages("Who?", ["ctx two", "ctx one"]), OPTIONS)


def test_arm_names_unique():
    names = [Arm("classical", N="all").name, Arm("quantum", N="all", S=256).name, Arm("quantum", N="all", S=256, seed=1).name, Arm("oracle").name]
    assert len(set(names)) == len(names)


@pytest.mark.skipif(not (ROOT / "results/phase3/.current_run").exists(), reason="needs Phase 1/3 artifacts")
def test_precomputed_contexts_match_earlier_phases():
    ev = json.loads((ROOT / "data/eval_set.json").read_text(encoding="utf-8"))
    prov = PrecomputedRetrieval(ev, 20958)
    assert prov.contexts(Arm("oracle"), 0) == [ev[0]["gold_idx"]]
    assert prov.contexts(Arm("closed_book"), 0) is None
    r = prov.contexts(Arm("random", seed=42), 3)
    assert len(set(r)) == 3 and ev[3]["gold_idx"] not in r and r == prov.contexts(Arm("random", seed=42), 3)
    assert len(prov.contexts(Arm("classical", N="all"), 0)) == 3
    assert prov.contexts(Arm("quantum", N="all", S=0), 0) == prov.contexts(Arm("classical", N="all"), 0)  # infinite-shot limit
