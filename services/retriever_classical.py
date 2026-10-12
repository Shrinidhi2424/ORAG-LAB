"""retriever-classical service: POST /retrieve/classical -> exact top-k by FAISS IndexFlatIP over a ladder rung."""
from __future__ import annotations

import time

import numpy as np
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException

from services.common import RUNGS, instrument, load_embeddings, load_ladder, log, threads
from services.schemas import RetrieveRequest, RetrieveResponse

SERVICE = "retriever-classical"


class RungStore:
    """Lazily builds one Flat index per ladder rung from the mounted embeddings (index volume)."""

    def __init__(self, embeddings: np.ndarray | None = None, ladder: dict[str, np.ndarray] | None = None):
        self.emb = load_embeddings() if embeddings is None else embeddings
        self.ladder = load_ladder() if ladder is None else ladder
        self._idx: dict[str, tuple] = {}

    def get(self, n: str):
        if n not in self.ladder:
            raise HTTPException(status_code=422, detail=f"unknown N={n!r}; choose from {list(self.ladder)}")
        if n not in self._idx:
            from qrag.index_classical import build_flat

            members = self.ladder[n]
            corpus = np.ascontiguousarray(self.emb[members])
            self._idx[n] = (members, corpus, build_flat(corpus))
        return self._idx[n]


def create_app(store: RungStore | None = None, preload: tuple[str, ...] = ()) -> FastAPI:
    import faiss

    faiss.omp_set_num_threads(threads())
    state = {"store": store}
    @asynccontextmanager
    async def lifespan(_app):
        _load()
        yield

    app = FastAPI(title=SERVICE, lifespan=lifespan)
    instrument(app, SERVICE, ready=lambda: state["store"] is not None)

    def _load():
        if state["store"] is None:
            t0 = time.perf_counter()
            state["store"] = RungStore()
            for n in preload or RUNGS:
                state["store"].get(n)
            log(SERVICE, "index_loaded", seconds=round(time.perf_counter() - t0, 2), rungs=list(preload or RUNGS))

    @app.post("/retrieve/classical", response_model=RetrieveResponse)
    def retrieve(req: RetrieveRequest):
        t0 = time.perf_counter()
        members, _, index = state["store"].get(req.N)
        q = np.asarray(req.vector, dtype=np.float32)[None, :]
        t1 = time.perf_counter()
        scores, pos = index.search(q, req.k)
        t2 = time.perf_counter()
        return RetrieveResponse(service=SERVICE, arm="classical", N=req.N, k=req.k, ids=[int(members[i]) for i in pos[0]],
                                scores=[float(s) for s in scores[0]], compute_ms=(time.perf_counter() - t0) * 1e3,
                                stages={"prepare_ms": (t1 - t0) * 1e3, "search_ms": (t2 - t1) * 1e3})

    return app


app = create_app()
