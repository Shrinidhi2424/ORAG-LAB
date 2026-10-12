"""Network-path diagnostic for the HTTP latency layer: where does the client<->orchestrator overhead come from?

Compares, for the same /rag/retrieval-only request, (A) httpx keep-alive, (B) a tiny GET /health, (C) keep-alive with TCP_NODELAY,
(D) a new connection per request - from the Windows host through Docker Desktop's published port and from a container on the
stack's Docker network. Needs the stack up (small profile). Writes results/phase6/<run_id>/network_diagnostic.json.

Usage: python scripts/net_diagnostic.py --run-id <id>        (host + container modes are driven automatically)
       python scripts/net_diagnostic.py --probe --base URL --data DIR   (internal: one side, prints JSON)
"""
from __future__ import annotations

import argparse
import json
import socket
import statistics
import subprocess
import sys
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent


def probe(base: str, data: Path, n: int = 60, warm: int = 10) -> dict:
    qs = [q["question"] for q in json.loads((data / "eval_set.json").read_text(encoding="utf-8"))[: n + warm]]
    body = lambda q: {"question": q, "arm": "classical", "k": 3, "N": "all"}  # noqa: E731

    def run(client: httpx.Client, health: bool = False) -> dict:
        for q in qs[:warm]:
            client.get("/health") if health else client.post("/rag/retrieval-only", json=body(q))
        e2e, orch = [], []
        for q in qs[warm : warm + n]:
            t0 = time.perf_counter()
            r = client.get("/health") if health else client.post("/rag/retrieval-only", json=body(q))
            e2e.append((time.perf_counter() - t0) * 1e3)
            if not health:
                orch.append(r.json()["timings"]["orchestrator_total_ms"])
        out = {"n": n, "client_median_ms": statistics.median(e2e)}
        if orch:
            out.update({"orchestrator_total_median_ms": statistics.median(orch), "client_minus_orchestrator_ms": statistics.median(e2e) - statistics.median(orch)})
        return out

    nodelay = httpx.HTTPTransport(socket_options=[(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)])
    return {"A_keepalive_post": run(httpx.Client(base_url=base, timeout=60)),
            "B_tiny_get_health": run(httpx.Client(base_url=base, timeout=60), health=True),
            "C_keepalive_post_tcp_nodelay": run(httpx.Client(base_url=base, timeout=60, transport=nodelay)),
            "D_new_connection_per_request": run(httpx.Client(base_url=base, timeout=60, limits=httpx.Limits(max_keepalive_connections=0)))}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id")
    ap.add_argument("--probe", action="store_true")
    ap.add_argument("--base", default="http://localhost:8000")
    ap.add_argument("--data", default=str(ROOT / "data"))
    args = ap.parse_args()
    if args.probe:
        print(json.dumps(probe(args.base, Path(args.data))))
        return
    out = ROOT / "results" / "phase6" / args.run_id
    out.mkdir(parents=True, exist_ok=True)
    host = probe("http://localhost:8000", ROOT / "data")
    cmd = ["docker", "run", "--rm", "--network", "qraglab_default", "-v", f"{ROOT}:/repo:ro", "-w", "/repo", "qrag-light:latest", "python",
           "scripts/net_diagnostic.py", "--probe", "--base", "http://orchestrator:8000", "--data", "/repo/data"]
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=900)
    if r.returncode != 0:
        sys.exit(f"container probe failed: {r.stderr[-500:]}")
    inner = json.loads(r.stdout.strip().splitlines()[-1])
    (out / "network_diagnostic.json").write_text(json.dumps({"profile": "small", "requests_per_variant": 60, "warmup": 10, "host_to_published_port": host,
                                                              "container_on_docker_network": inner}, indent=2), encoding="utf-8")
    print(json.dumps({"host": host, "in_network": inner}, indent=2))


if __name__ == "__main__":
    main()
