"""embedder service: POST /embed -> L2-normalised MiniLM vectors (CPU). Model baked into the image (R6: no network)."""
from __future__ import annotations

import os
import time

import numpy as np
from contextlib import asynccontextmanager

from fastapi import FastAPI

from services.common import instrument, log, threads
from services.schemas import EmbedRequest, EmbedResponse

SERVICE = "embedder"


def default_encoder():
    import torch
    from sentence_transformers import SentenceTransformer

    torch.set_num_threads(threads())
    model = SentenceTransformer(os.environ.get("QRAG_EMBED_MODEL_PATH", "sentence-transformers/all-MiniLM-L6-v2"), device="cpu")

    def encode(texts: list[str]) -> np.ndarray:
        return model.encode(texts, batch_size=64, show_progress_bar=False, convert_to_numpy=True, normalize_embeddings=True).astype(np.float32)

    encode(["warm-up"])  # first request must not pay for lazy initialisation
    return encode


def create_app(encoder=None) -> FastAPI:
    state = {"encode": encoder}
    @asynccontextmanager
    async def lifespan(_app):
        _load()
        yield

    app = FastAPI(title=SERVICE, lifespan=lifespan)
    instrument(app, SERVICE, ready=lambda: state["encode"] is not None)

    def _load():
        if state["encode"] is None:
            t0 = time.perf_counter()
            state["encode"] = default_encoder()
            log(SERVICE, "model_loaded", seconds=round(time.perf_counter() - t0, 2), threads=threads())

    @app.post("/embed", response_model=EmbedResponse)
    def embed(req: EmbedRequest):
        t0 = time.perf_counter()
        vecs = state["encode"](req.texts)
        return EmbedResponse(dim=int(vecs.shape[1]), vectors=vecs.tolist(), compute_ms=(time.perf_counter() - t0) * 1e3)

    return app


app = create_app()
