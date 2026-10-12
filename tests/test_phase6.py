"""Phase 6 integration tests (plan 6.7): the whole service graph runs in-process over ASGI transports - no Docker, no network."""
import asyncio

import httpx
import numpy as np
import pytest

from services import embedder, generator_gateway, orchestrator, retriever_classical, retriever_quantum
from services.retriever_classical import RungStore
from services.schemas import RetrieveResponse

DIM, N = 24, 400


@pytest.fixture(scope="module")
def world():
    rng = np.random.default_rng(0)
    emb = rng.normal(size=(N, DIM)).astype(np.float32)
    emb /= np.linalg.norm(emb, axis=1, keepdims=True)
    ladder = {"100": np.arange(100), "all": np.arange(N)}
    texts = {i: f"paragraph number {i}" for i in range(N)}
    return emb, ladder, texts


def fake_encode(texts):
    out = []
    for t in texts:
        i = int(t.split()[-1]) % N
        out.append(WORLD_EMB[i])
    return np.stack(out).astype(np.float32)


class FakeGen:
    model = "fake-model"

    def __init__(self):
        self.calls = []

    def generate(self, messages):
        self.calls.append(messages)
        return {"text": "stub answer", "cached": False, "model": self.model, "wall_s": 0.0}


def build_stack(world):
    global WORLD_EMB
    emb, ladder, texts = world
    WORLD_EMB = emb
    store = RungStore(emb, ladder)
    apps = {"embedder": embedder.create_app(fake_encode), "classical": retriever_classical.create_app(store),
            "quantum": retriever_quantum.create_app(store), "generator": generator_gateway.create_app(FakeGen())}
    clients = {k: httpx.AsyncClient(transport=httpx.ASGITransport(app=a), base_url="http://svc") for k, a in apps.items()}
    return orchestrator.create_app(clients=clients, texts=texts), apps, clients


def run(coro):
    return asyncio.run(coro)


def test_health_endpoints(world):
    orch, apps, _ = build_stack(world)

    async def go():
        for name, a in {"orchestrator": orch, **apps}.items():
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=a), base_url="http://x") as c:
                r = await c.get("/health")
                assert r.status_code == 200 and r.json()["status"] == "ok" and r.json()["service"]

    run(go())


def test_classical_and_quantum_return_same_schema(world):
    _, apps, _ = build_stack(world)
    q = world[0][3].tolist()

    async def go():
        out = {}
        for arm, path in (("classical", "/retrieve/classical"), ("quantum", "/retrieve/quantum")):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=apps[arm]), base_url="http://x") as c:
                r = await c.post(path, json={"vector": q, "k": 5, "N": "all", "M": 40, "shots": 4096, "seed": 1})
                assert r.status_code == 200
                out[arm] = RetrieveResponse(**r.json())
        return out

    out = run(go())
    assert set(out["classical"].model_dump()) == set(out["quantum"].model_dump())
    assert out["classical"].arm == "classical" and out["quantum"].arm == "quantum"
    assert len(out["classical"].ids) == len(out["quantum"].ids) == 5
    assert out["classical"].ids[0] == 3  # the query is paragraph 3's own vector


def test_quantum_is_seeded_and_high_shots_matches_classical(world):
    _, apps, _ = build_stack(world)
    q = world[0][7].tolist()

    async def go(shots, seed):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=apps["quantum"]), base_url="http://x") as c:
            return (await c.post("/retrieve/quantum", json={"vector": q, "k": 5, "N": "all", "M": 50, "shots": shots, "seed": seed})).json()

    a, b, c = run(go(64, 0)), run(go(64, 0)), run(go(64, 1))
    assert a["ids"] == b["ids"] and a["scores"] == b["scores"]
    assert a["scores"] != c["scores"]
    assert run(go(1 << 20, 0))["ids"][0] == 7


def test_rag_end_to_end_returns_answer_contexts_timings(world):
    orch, _, _ = build_stack(world)

    async def go():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=orch), base_url="http://x") as c:
            return await c.post("/rag", json={"question": "paragraph number 11", "arm": "classical", "k": 3, "N": "all"})

    r = run(go())
    body = r.json()
    assert r.status_code == 200 and body["mode"] == "full" and body["answer"] == "stub answer"
    assert len(body["contexts"]) == 3 and body["contexts"][0]["idx"] == 11 and body["contexts"][0]["text"] == "paragraph number 11"
    for key in ("embedder_hop_ms", "embedder_compute_ms", "classical_hop_ms", "classical_compute_ms", "generator_hop_ms", "prompt_build_ms", "orchestrator_total_ms"):
        assert key in body["timings"] and body["timings"][key] >= 0
    assert "X-Stage-Timings" in r.headers or "x-stage-timings" in r.headers


def test_retrieval_only_mode_skips_generation_and_texts(world):
    orch, _, _ = build_stack(world)

    async def go(arm):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=orch), base_url="http://x") as c:
            return (await c.post("/rag/retrieval-only", json={"question": "paragraph number 5", "arm": arm, "k": 3, "N": "100"})).json()

    for arm in ("classical", "quantum"):
        body = go(arm)
        body = run(body)
        assert body["mode"] == "retrieval_only" and body["answer"] is None and body["contexts"][0]["text"] is None
        assert "generator_hop_ms" not in body["timings"] and f"{arm}_compute_ms" in body["timings"]


def test_bad_rung_and_downstream_error_are_reported(world):
    orch, _, _ = build_stack(world)

    async def go():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=orch), base_url="http://x") as c:
            return await c.post("/rag/retrieval-only", json={"question": "paragraph number 5", "arm": "classical", "k": 3, "N": "7777"})

    assert run(go()).status_code == 502  # retriever answered 422; orchestrator reports a bad gateway with detail
