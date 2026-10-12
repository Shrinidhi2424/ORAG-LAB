"""generator-gateway service: POST /generate -> Ollama on the HOST (not in a container), with the shared answer cache.

Used only for the end-to-end smoke test (plan H6): Ollama must be stopped during latency measurements."""
from __future__ import annotations

import os
import time
from pathlib import Path

from fastapi import FastAPI

from services.common import instrument
from services.schemas import GenerateRequest, GenerateResponse

SERVICE = "generator-gateway"


def create_app(generator=None) -> FastAPI:
    state = {"gen": generator}
    app = FastAPI(title=SERVICE)
    instrument(app, SERVICE)

    def gen():
        if state["gen"] is None:
            from qrag.generate import OllamaGenerator

            state["gen"] = OllamaGenerator(cache_dir=Path(os.environ.get("LLM_CACHE_DIR", "/cache/llm")), keep_alive="2m")
        return state["gen"]

    @app.post("/generate", response_model=GenerateResponse)
    def generate(req: GenerateRequest):
        t0 = time.perf_counter()
        g = gen().generate(req.messages)
        return GenerateResponse(text=g["text"], cached=bool(g["cached"]), model=g["model"], wall_s=float(g["wall_s"]),
                                compute_ms=(time.perf_counter() - t0) * 1e3)

    return app


app = create_app()
