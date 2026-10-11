"""Phase 1 tests: corpus/ladder invariants, exact retrieval, metrics, embeddings sanity."""
import json
from pathlib import Path

import numpy as np
import pytest

from qrag.corpus import build_eval_set, build_ladder, extract_paragraphs, paragraph_id
from qrag.index_classical import exact_topk, gold_ranks
from qrag.metrics import hit_at_k, mrr_at_k, ndcg_at_k, precision_at_k

ROOT = Path(__file__).resolve().parent.parent
needs_squad = pytest.mark.skipif(not (ROOT / "data/raw/squad_v1.1/dev-v1.1.json").exists(), reason="run `python tasks.py data`")
needs_emb = pytest.mark.skipif(not (ROOT / "data/emb_paragraphs.npy").exists(), reason="run `python tasks.py embed`")


def test_paragraph_id_stable():
    assert paragraph_id("abc") == paragraph_id("abc") != paragraph_id("abd")


def test_exact_topk_matches_numpy():
    rng = np.random.default_rng(0)
    c = rng.normal(size=(500, 16)).astype(np.float32)
    c /= np.linalg.norm(c, axis=1, keepdims=True)
    q = c[:7] + 0.05 * rng.normal(size=(7, 16)).astype(np.float32)
    q /= np.linalg.norm(q, axis=1, keepdims=True)
    ids, sc = exact_topk(q, c, k=10, chunk=3)
    ref = np.argsort(-(q @ c.T), axis=1, kind="stable")[:, :10]
    assert (ids == ref).all()
    assert (np.diff(sc, axis=1) <= 1e-7).all()


def test_gold_ranks_consistent_with_topk():
    rng = np.random.default_rng(1)
    c = rng.normal(size=(200, 8)).astype(np.float32)
    q = rng.normal(size=(5, 8)).astype(np.float32)
    ids, _ = exact_topk(q, c, k=200)
    gold = np.array([3, 50, 199, 0, 77])
    ranks = gold_ranks(q, c, gold)
    for j, g in enumerate(gold):
        assert ids[j, ranks[j] - 1] == g


def test_metrics_single_gold():
    r = np.array([1, 2, 4, 11])
    assert hit_at_k(r, 1) == 0.25 and hit_at_k(r, 10) == 0.75
    assert precision_at_k(r, 5) == pytest.approx(0.75 / 5)
    assert mrr_at_k(r, 10) == pytest.approx((1 + 0.5 + 0.25) / 4)
    assert ndcg_at_k(r, 10) == pytest.approx((1 + 1 / np.log2(3) + 1 / np.log2(5)) / 4)


@needs_squad
def test_corpus_ladder_invariants():
    paragraphs, stats = extract_paragraphs()
    assert len({p["id"] for p in paragraphs}) == len(paragraphs) == stats["unique_paragraphs"]
    ev, _ = build_eval_set(paragraphs)
    ev2, _ = build_eval_set(paragraphs)
    assert ev == ev2 and len(ev) == 300
    rungs, _ = build_ladder(paragraphs, ev)
    gold = {q["gold_idx"] for q in ev}
    names = list(rungs)
    for a, b in zip(names[:-1], names[1:]):
        assert set(rungs[a]) <= set(rungs[b])
    for name, members in rungs.items():
        assert gold <= set(members) and len(set(members)) == len(members)
        if name != "all":
            assert len(members) == int(name)
    assert rungs["all"] == list(range(len(paragraphs)))


@needs_emb
def test_embeddings_normalised_and_padded():
    pv = np.load(ROOT / "data/emb_paragraphs.npy")
    pv512 = np.load(ROOT / "data/emb_paragraphs_512.npy")
    assert pv.dtype == np.float32 and pv.shape[1] == 384 and pv512.shape[1] == 512
    assert not np.isnan(pv).any()
    assert np.allclose(np.linalg.norm(pv, axis=1), 1.0, atol=1e-4)
    assert (pv512[:, 384:] == 0).all() and np.array_equal(pv512[:, :384], pv)


@needs_emb
def test_ground_truth_files_exist_for_every_rung():
    cur = (ROOT / "results/phase1/.current_run").read_text(encoding="utf-8").strip()
    ladder = json.loads((ROOT / "data/ladder_N.json").read_text(encoding="utf-8"))
    for name in ladder["rungs"]:
        gt = np.load(ROOT / f"results/phase1/{cur}/ground_truth_N{name}.npz")
        assert gt["paragraph_idx"].shape == (300, 50)
        assert (np.diff(gt["scores"], axis=1) <= 1e-6).all()
