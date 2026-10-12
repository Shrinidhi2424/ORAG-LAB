"""RAG pipeline (plan 5.1): query -> embed -> retrieve(arm) -> prompt (A.5) -> generate -> record.

Only the retrieval arm differs between conditions (R1). Two retrieval back-ends with identical semantics:
- PrecomputedRetrieval: reads the Phase 1 exact ground truth (classical Flat) and the seeded Phase 3 rankings
  (quantum-sim), i.e. exactly the lists already evaluated in Phases 2-4. Used for the experiments.
- LiveRetrieval: embeds the query and searches FAISS / QuantumSimRetriever at request time (services, Phase 6).
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"


@dataclass(frozen=True)
class Arm:
    kind: str  # classical | quantum | oracle | random | closed_book
    N: str = ""  # ladder rung ("5000", "all", ...)
    S: int = 0  # shots (quantum)
    seed: int = 0  # quantum seed / random-context seed
    M: int = 50  # shortlist (quantum)
    k: int = 3  # contexts in the prompt

    @property
    def name(self) -> str:
        if self.kind == "quantum":
            return f"quantum_N{self.N}_M{self.M}_S{self.S}_seed{self.seed}_k{self.k}"
        if self.kind == "classical":
            return f"classical_N{self.N}_k{self.k}"
        return self.kind

    def as_dict(self) -> dict:
        return {**asdict(self), "name": self.name}


def _current(phase: str) -> Path:
    return ROOT / "results" / phase / (ROOT / "results" / phase / ".current_run").read_text(encoding="utf-8").strip()


class PrecomputedRetrieval:
    def __init__(self, eval_set: list[dict], n_paragraphs: int):
        self.eval_set = eval_set
        self.n_paragraphs = n_paragraphs
        self._cache: dict = {}

    def _gt(self, n: str) -> np.ndarray:
        if ("gt", n) not in self._cache:
            self._cache[("gt", n)] = np.load(_current("phase1") / f"ground_truth_N{n}.npz")["paragraph_idx"]
        return self._cache[("gt", n)]

    def _q(self, n: str, m: int, s: int, seed: int) -> np.ndarray:
        key = ("q", n, m, s)
        if key not in self._cache:
            z = np.load(_current("phase3") / "rankings" / f"N{n}_M{m}_tieclassical.npz")
            self._cache[key] = (list(z["shots"]), z["top"])
        shots, top = self._cache[key]
        return top[shots.index(s), seed]

    def contexts(self, arm: Arm, qi: int) -> list[int] | None:
        """Global paragraph indices for question qi (rank order), or None for closed-book."""
        if arm.kind == "closed_book":
            return None
        if arm.kind == "oracle":
            return [self.eval_set[qi]["gold_idx"]]
        if arm.kind == "random":
            rng = np.random.default_rng([arm.seed, qi])
            gold = self.eval_set[qi]["gold_idx"]
            pick = []
            while len(pick) < arm.k:
                c = int(rng.integers(0, self.n_paragraphs))
                if c != gold and c not in pick:
                    pick.append(c)
            return pick
        if arm.kind == "classical":
            return [int(x) for x in self._gt(arm.N)[qi, : arm.k]]
        if arm.kind == "quantum":
            return [int(x) for x in self._q(arm.N, arm.M, arm.S, arm.seed)[qi, : arm.k]]
        raise ValueError(arm.kind)


class LiveRetrieval:
    """Request-time retrieval for the services: embed with MiniLM, then FAISS Flat or the quantum-sim reranker."""

    def __init__(self, corpus: np.ndarray, members: np.ndarray, model=None):
        from qrag.embed import load_model
        from qrag.index_classical import build_flat

        self.model = model or load_model()
        self.corpus, self.members = corpus, members
        self.flat = build_flat(corpus)

    def embed(self, question: str) -> np.ndarray:
        from qrag.embed import embed_texts

        return embed_texts(self.model, [question])

    def contexts(self, arm: Arm, question: str, rng_seed: int | None = None) -> list[int]:
        from qrag.rerank import QuantumSimRetriever

        q = self.embed(question)
        if arm.kind == "classical":
            _, ids = self.flat.search(q, arm.k)
            return [int(self.members[i]) for i in ids[0]]
        if arm.kind == "quantum":
            r = QuantumSimRetriever(self.corpus, arm.M, arm.S, seed=arm.seed if rng_seed is None else rng_seed, flat_index=self.flat)
            ids, _ = r.retrieve(q, arm.k)
            return [int(self.members[i]) for i in ids]
        raise ValueError(arm.kind)


def load_paragraph_texts() -> dict[int, str]:
    out = {}
    with (DATA / "paragraphs.jsonl").open(encoding="utf-8") as f:
        for line in f:
            p = json.loads(line)
            out[p["idx"]] = p["text"]
    return out


def build_record(arm: Arm, qi: int, q: dict, ctx_idx: list[int] | None, texts: dict[int, str]) -> dict:
    from qrag.generate import build_messages

    contexts = None if ctx_idx is None else [texts[i] for i in ctx_idx]
    return {"arm": arm.name, "arm_cfg": arm.as_dict(), "qi": qi, "qid": q["qid"], "question": q["question"], "answers": q["answers"],
            "gold_idx": q["gold_idx"], "context_idx": ctx_idx, "gold_in_context": bool(ctx_idx is not None and q["gold_idx"] in ctx_idx),
            "messages": build_messages(q["question"], contexts)}
