"""retriever-quantum-sim service: POST /retrieve/quantum -> two-stage shortlist + SWAP-test (Tier B emulator) re-score.

EMULATED estimator: its latency is classical simulation cost, never quantum latency. Draws are seeded per
(request seed, query vector), so a response is reproducible and independent of request order."""
from __future__ import annotations

import hashlib
import time

import numpy as np
from contextlib import asynccontextmanager

from fastapi import FastAPI

from services.common import RUNGS, instrument, load_embeddings, load_ladder, log, threads
from services.retriever_classical import RungStore
from services.schemas import RetrieveRequest, RetrieveResponse

SERVICE = "retriever-quantum-sim"


def query_rng(seed: int, q: np.ndarray) -> np.random.Generator:
    h = int.from_bytes(hashlib.blake2b(q.tobytes(), digest_size=8).digest(), "little")
    return np.random.default_rng(np.random.SeedSequence([seed, h]))


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
            state["store"] = RungStore(load_embeddings(), load_ladder())
            for n in preload or RUNGS:
                state["store"].get(n)
            log(SERVICE, "index_loaded", seconds=round(time.perf_counter() - t0, 2), rungs=list(preload or RUNGS))

    @app.post("/retrieve/quantum", response_model=RetrieveResponse)
    def retrieve(req: RetrieveRequest):
        from qrag.rerank import QuantumSimRetriever

        t0 = time.perf_counter()
        members, corpus, index = state["store"].get(req.N)
        q = np.asarray(req.vector, dtype=np.float32)[None, :]
        ret = QuantumSimRetriever(corpus, M=min(req.M, len(corpus)), shots=req.shots, seed=0, flat_index=index)
        ret.rng = query_rng(req.seed, q)
        st: dict = {}
        pos, c2 = ret.retrieve(q, req.k, st)
        return RetrieveResponse(service=SERVICE, arm="quantum", N=req.N, k=req.k, ids=[int(members[i]) for i in pos],
                                scores=[float(s) for s in c2], compute_ms=(time.perf_counter() - t0) * 1e3,
                                stages={k.replace("_s", "_ms"): v * 1e3 for k, v in st.items()})

    return app


app = create_app()
