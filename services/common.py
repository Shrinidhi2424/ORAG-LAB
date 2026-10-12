"""Shared service plumbing: data loading, JSON logs, per-request timing headers, health endpoint."""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import numpy as np
import psutil
from fastapi import FastAPI, Request

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.environ.get("DATA_DIR", ROOT / "data"))
RUNGS = ("1000", "2000", "5000", "10000", "all")


def load_ladder() -> dict[str, np.ndarray]:
    ladder = json.loads((DATA_DIR / "ladder_N.json").read_text(encoding="utf-8"))
    return {k: np.asarray(v, dtype=np.int64) for k, v in ladder["rungs"].items()}


def load_embeddings() -> np.ndarray:
    return np.load(DATA_DIR / "emb_paragraphs.npy")


def threads() -> int:
    return max(1, int(os.environ.get("QRAG_THREADS", "1")))


def log(service: str, event: str, **kw) -> None:
    """One JSON object per line on stdout (structured logs, plan 6.1)."""
    print(json.dumps({"ts": round(time.time(), 3), "service": service, "event": event, **kw}), file=sys.stdout, flush=True)


def instrument(app: FastAPI, service: str, ready=lambda: True) -> None:
    """Adds /health and a middleware that logs each request and sets a Server-Timing header."""

    @app.get("/health")
    def health():
        return {"status": "ok" if ready() else "starting", "service": service, "ready": bool(ready()),
                "rss_mb": round(psutil.Process().memory_info().rss / 1e6, 1), "threads": threads()}

    @app.middleware("http")
    async def timing(request: Request, call_next):
        t0 = time.perf_counter()
        response = await call_next(request)
        ms = (time.perf_counter() - t0) * 1e3
        response.headers["Server-Timing"] = f"total;dur={ms:.3f}"
        response.headers["X-Service"] = service
        if request.url.path != "/health":
            log(service, "request", path=request.url.path, status=response.status_code, ms=round(ms, 3))
        return response
