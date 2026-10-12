"""orchestrator service: POST /rag and POST /rag/retrieval-only.

question -> embedder -> retriever (classical | quantum-sim) -> [prompt (A.5) -> generator-gateway]. Per-stage timings are
returned in the body and in a Server-Timing header: `*_hop_ms` is the client-side wall time of a service call (network +
serialisation + service compute), `*_compute_ms` is what the service itself reports, so hop - compute = service overhead."""
from __future__ import annotations

import json
import os
import time
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, HTTPException, Response

from services.common import DATA_DIR, instrument, log
from services.schemas import Context, RagRequest, RagResponse

SERVICE = "orchestrator"
URLS = {"embedder": "EMBEDDER_URL", "classical": "RETRIEVER_CLASSICAL_URL", "quantum": "RETRIEVER_QUANTUM_URL", "generator": "GENERATOR_URL"}
DEFAULTS = {"embedder": "http://localhost:8001", "classical": "http://localhost:8002", "quantum": "http://localhost:8003",
            "generator": "http://localhost:8004"}


def load_paragraph_texts() -> dict[int, str]:
    out = {}
    with (DATA_DIR / "paragraphs.jsonl").open(encoding="utf-8") as f:
        for line in f:
            p = json.loads(line)
            out[p["idx"]] = p["text"]
    return out


def create_app(clients: dict[str, httpx.AsyncClient] | None = None, texts: dict[int, str] | None = None) -> FastAPI:
    state = {"clients": clients, "texts": texts, "owns": clients is None}

    @asynccontextmanager
    async def lifespan(_app):
        if state["clients"] is None:
            limits = httpx.Limits(max_connections=64, max_keepalive_connections=32)
            state["clients"] = {k: httpx.AsyncClient(base_url=os.environ.get(env, DEFAULTS[k]), timeout=120.0, limits=limits) for k, env in URLS.items()}
        if state["texts"] is None:
            state["texts"] = load_paragraph_texts()
        log(SERVICE, "ready", paragraphs=len(state["texts"]))
        yield
        if state["owns"]:
            for c in state["clients"].values():
                await c.aclose()

    app = FastAPI(title=SERVICE, lifespan=lifespan)
    instrument(app, SERVICE, ready=lambda: state["clients"] is not None and state["texts"] is not None)

    async def call(name: str, path: str, payload: dict, timings: dict[str, float]) -> dict:
        t0 = time.perf_counter()
        try:
            r = await state["clients"][name].post(path, json=payload)
        except httpx.HTTPError as e:
            raise HTTPException(status_code=502, detail=f"{name} unreachable: {type(e).__name__}") from e
        timings[f"{name}_hop_ms"] = (time.perf_counter() - t0) * 1e3
        if r.status_code != 200:
            raise HTTPException(status_code=502, detail=f"{name} returned {r.status_code}: {r.text[:200]}")
        body = r.json()
        timings[f"{name}_compute_ms"] = float(body.get("compute_ms", 0.0))
        return body

    async def run(req: RagRequest, full: bool, response: Response) -> RagResponse:
        t_start = time.perf_counter()
        timings: dict[str, float] = {}
        emb = await call("embedder", "/embed", {"texts": [req.question]}, timings)
        arm_path = "/retrieve/classical" if req.arm == "classical" else "/retrieve/quantum"
        payload = {"vector": emb["vectors"][0], "k": req.k, "N": req.N, "M": req.M, "shots": req.shots, "seed": req.seed}
        ret = await call(req.arm, arm_path, payload, timings)
        for stage, ms in (ret.get("stages") or {}).items():
            timings[f"retrieve_{stage}"] = float(ms)
        contexts = [Context(idx=i, score=s, text=state["texts"][i] if full else None) for i, s in zip(ret["ids"], ret["scores"])]
        answer, cached = None, None
        if full:
            from qrag.generate import build_messages

            t0 = time.perf_counter()
            messages = build_messages(req.question, [c.text for c in contexts])
            timings["prompt_build_ms"] = (time.perf_counter() - t0) * 1e3
            gen = await call("generator", "/generate", {"messages": messages}, timings)
            answer, cached = gen["text"], bool(gen["cached"])
        timings["orchestrator_total_ms"] = (time.perf_counter() - t_start) * 1e3
        response.headers["X-Stage-Timings"] = json.dumps({k: round(v, 3) for k, v in timings.items()})
        return RagResponse(mode="full" if full else "retrieval_only", arm=req.arm, N=req.N, question=req.question, contexts=contexts,
                           answer=answer, answer_cached=cached, timings={k: round(v, 4) for k, v in timings.items()})

    @app.post("/rag/retrieval-only", response_model=RagResponse)
    async def rag_retrieval_only(req: RagRequest, response: Response):
        return await run(req, False, response)

    @app.post("/rag", response_model=RagResponse)
    async def rag(req: RagRequest, response: Response):
        return await run(req, True, response)

    return app


app = create_app()
