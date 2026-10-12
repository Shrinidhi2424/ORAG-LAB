"""Phase 6 block of FINDINGS.md, generated from results/phase6/<run_id>/ artifacts (used by report.py)."""
from __future__ import annotations

import csv
import json
import xml.etree.ElementTree as ET
from pathlib import Path

from report import latest_run, md_table, rel

PROFILES = ("small", "medium", "large")
PROFILE_DESC = {"small": "1 CPU / 1.5 GB", "medium": "2 CPU / 2 GB", "large": "4 CPU / 3 GB"}
NORDER = ["1000", "5000", "all"]


def rd(p: Path) -> list[dict]:
    return list(csv.DictReader(p.open(encoding="utf-8")))


def f(x, d=2) -> str:
    return "-" if x in ("", None) else f"{float(x):.{d}f}"


def host_port_run() -> Path | None:
    ptr = Path(__file__).resolve().parent.parent / "results" / "phase6" / ".host_port_run"
    if ptr.exists():
        d = ptr.parent / ptr.read_text(encoding="utf-8").strip()
        return d if (d / "latency_summary.csv").exists() else None
    return None


def agg_conc(rows: list[dict]) -> list[list]:
    out = []
    for key in dict.fromkeys((r["profile"], r["arm"], r["clients"]) for r in rows):
        sel = [r for r in rows if (r["profile"], r["arm"], r["clients"]) == key]
        tp = sorted(float(r["throughput_rps"]) for r in sel)
        out.append([f"{key[0]} ({PROFILE_DESC[key[0]]})", key[1], key[2], f(tp[len(tp) // 2], 1), f"{f(tp[0], 1)}-{f(tp[-1], 1)}",
                    f(sorted(float(r["median_ms"]) for r in sel)[len(sel) // 2], 1), f(sorted(float(r["p95_ms"]) for r in sel)[len(sel) // 2], 1),
                    sum(int(float(r["errors"])) for r in sel), sum(int(float(r["requests"])) for r in sel)])
    return out


def inprocess_baseline() -> dict:
    """In-process (Phase 2 query embedding + Phase 4 retrieval-only) medians for comparison; None if missing."""
    out = {}
    p2, p4 = latest_run("phase2"), latest_run("phase4")
    if p2 and (p2 / "query_embed_summary.json").exists() and p4 and (p4 / "latency_summary.csv").exists():
        embed = float(json.loads((p2 / "query_embed_summary.json").read_text(encoding="utf-8"))["median_ms"])
        lat = rd(p4 / "latency_summary.csv")
        for n in NORDER:
            fl = next(r for r in lat if (r["arm"], r["N"]) == ("flat", n))
            qs = next(r for r in lat if (r["arm"], r["N"], r["M"], r["S"]) == ("qsim", n, "50", "1024"))
            out[("classical", n)] = (embed, float(fl["median_ms"]))
            out[("quantum", n)] = (embed, float(qs["median_ms"]))
    return out


def phase6_block(run: Path) -> tuple[str, list[list]]:
    idx: list[list] = []
    hrun = host_port_run()
    hy = json.loads((run / "hygiene.json").read_text(encoding="utf-8"))
    L = [f"Run `{run.name}` - manifest: `{rel(run / 'run_manifest.json')}`. Backend: **{hy['backend']}**; primary HTTP load generator: **{hy.get('client', 'host_port')}** ({hy.get('load_generator', 'Windows host through the published port')}). Services: embedder, retriever-classical, retriever-quantum-sim, generator-gateway, "
         "orchestrator (FastAPI + pydantic, `/health`, JSON logs on stdout, per-stage timings in body and `Server-Timing`/`X-Stage-Timings` headers). Cloud-native architecture "
         "EMULATED on commodity hardware: no claim about real cloud performance.", ""]
    if hy["backend"] == "docker":
        L += [f"Docker server {hy['docker_server']}; WSL2 VM memory visible to Docker {hy['docker_vm_mem_gb']:.2f} GB (`.wslconfig`: `{hy['wslconfig'].strip().replace(chr(10), '; ') if hy.get('wslconfig') else 'none'}`). "
              f"Other containers on the host left untouched: {hy['other_running_containers_untouched']}. Ollama loaded models at start: `{hy['ollama_loaded_models'] or 'none'}`. "
              "Profiles apply to the three compute services; orchestrator and generator-gateway have a fixed 0.5 CPU / 384 MB limit.", ""]
        di = run / "docker_images.json"
        if di.exists():
            L += ["Image sizes (`" + rel(di) + "`): " + ", ".join(f"`{k}` {v}" for k, v in json.loads(di.read_text(encoding="utf-8")).items()) + ".", ""]
    else:
        L += ["**No-container fallback in use** (reduced rigor): CPU limits approximated by `cpu_affinity`, memory limits not enforced (see Deviations).", ""]
    su = run / "startup.csv"
    if su.exists():
        L += ["Stack start-up (`" + rel(su) + "`): " + "; ".join(f"{r['profile']}: compose up {float(r['compose_up_s']):.1f} s (+{float(r['extra_wait_until_all_ready_s']):.1f} s until all /health ready)" for r in rd(su)) + ".", ""]

    ls = run / "latency_summary.csv"
    if ls.exists():
        lat = rd(ls)
        base = inprocess_baseline()
        body = []
        for prof in PROFILES:
            for arm in ("classical", "quantum"):
                for n in NORDER:
                    r = next((x for x in lat if (x["profile"], x["arm"], x["N"]) == (prof, arm, n)), None)
                    if r:
                        body.append([f"{prof} ({PROFILE_DESC[prof]})", arm, n, f(r["e2e_median_ms"]), f(r["e2e_p95_ms"]), f"{f(r['repeat_median_min_ms'])}-{f(r['repeat_median_max_ms'])}",
                                     f(r["embed_compute_median_ms"]), f(r["embed_service_overhead_median_ms"]), f(r["retrieve_compute_median_ms"]),
                                     f(r["retrieve_service_overhead_median_ms"]), f(r["client_to_orchestrator_overhead_median_ms"]), r["errors"]])
        L += [f"**T4c HTTP latency per request, retrieval-only mode (6.3)** (`{rel(ls)}`; raw `{rel(run / 'latency_raw.csv')}`). Client -> orchestrator -> embedder -> retriever; k=3; quantum-sim M=50, S=1024 "
              "(emulated estimator); 10 warm-up discarded, 100 timed requests, 5 repeats, arm x N conditions shuffled per repeat; the load generator runs on the same laptop. Medians in ms; "
              "'overhead' = hop wall time minus the service's own compute time (network, serialisation, framework); 'client<->orchestrator' = client wall time minus orchestrator total.", "",
              md_table(["Profile", "Arm", "N", "E2E median", "E2E p95", "Repeat medians range", "Embed compute", "Embed svc overhead", "Retrieve compute", "Retrieve svc overhead", "Client<->orch overhead", "Errors"], body), ""]
        if base:
            cmp_rows = []
            for prof in PROFILES:
                for arm in ("classical", "quantum"):
                    for n in NORDER:
                        r = next((x for x in lat if (x["profile"], x["arm"], x["N"]) == (prof, arm, n)), None)
                        if r and (arm, n) in base:
                            e, s_ = base[(arm, n)]
                            cmp_rows.append([prof, arm, n, f(e), f(s_, 3), f(e + s_), f(r["e2e_median_ms"]), f(float(r["e2e_median_ms"]) - e - s_), f"{float(r['e2e_median_ms']) / (e + s_):.2f}x"])
            L += ["**Service overhead vs the in-process baseline (6.3)**: in-process = Phase 2 query-embedding median (batch 1, 4 torch threads) + Phase 4 retrieval-only median "
                  "(Flat k=10 / quantum-sim shortlist M=50 S=1024, 1 thread). Different protocol and thread counts, so the difference is indicative, not a pure network cost.", "",
                  md_table(["Profile", "Arm", "N", "In-process embed", "In-process retrieve", "In-process total", "HTTP E2E median", "Difference", "Ratio"], cmp_rows), "",
                  "**F5b HTTP vs in-process latency**: ![F5b](results/figures/F5b_http_vs_inprocess.png) (data `results/figures/F5b_http_vs_inprocess.csv`).", ""]
        e = next(x for x in lat if (x["profile"], x["arm"], x["N"]) == ("medium", "classical", "all")) if any(x["profile"] == "medium" for x in lat) else lat[0]
        idx.append(["P6-1", 6, f"HTTP E2E median, {e['profile']} profile, classical N=all: {float(e['e2e_median_ms']):.1f} ms (p95 {float(e['e2e_p95_ms']):.1f})", rel(ls)])

    cc = run / "concurrency.csv"
    if cc.exists():
        rows = rd(cc)
        agg = agg_conc(rows)
        L += [f"**T4d Concurrency (6.4) [P1]** (`{rel(cc)}`): N=all, retrieval-only through the orchestrator, 1 / 4 / 16 concurrent clients (asyncio + httpx), 300 requests per run after a 20-request warm-up, "
              "3 repeats; throughput = requests / wall time; latencies are per request; the load generator shares the laptop.", "",
              md_table(["Profile", "Arm", "Clients", "Throughput rps (median of runs)", "Throughput range", "Median latency ms", "p95 ms", "Errors", "Requests"], agg), "",
              "**F10 concurrency**: ![F10](results/figures/F10_concurrency.png) (data `results/figures/F10_concurrency.csv`).", ""]
        t = [r for r in rows if r["profile"] == "medium" and r["arm"] == "classical"] or rows
        top = max(t, key=lambda r: float(r["throughput_rps"]))
        idx.append(["P6-2", 6, f"Peak throughput ({top['profile']}, {top['arm']}): {float(top['throughput_rps']):.1f} req/s at {top['clients']} clients; total errors {sum(int(float(r["errors"])) for r in rows)}", rel(cc)])

    mm = run / "memory.csv"
    if mm.exists():
        mem = rd(mm)
        L += [f"**Memory footprint (6.5) [P1]** (`{rel(mm)}`; `docker stats` per container: idle after start-up and peak sampled every ~0.5 s during the whole load test (latency + concurrency); limit as configured). "
              "Each retriever holds all five ladder rungs in memory.", "",
              md_table(["Profile", "Service", "Idle MB", "Peak during load tests MB", "Limit MB"], [[r["profile"], r["service"], f(r["idle_mb"], 1), f(r.get("peak_during_load_mb", r.get("peak_during_concurrency_mb")), 1), f(r["limit_mb"], 0)] for r in mem]), ""]
        p2 = latest_run("phase2")
        if p2 and (p2 / "build.csv").exists():
            b = [r for r in rd(p2 / "build.csv") if r["arm"] == "flat"]
            L += ["Index size on disk / serialised, per N (Phase 2 `build.csv`): " + ", ".join(f"N={r['N']}: {int(r['index_bytes']) / 1e6:.2f} MB" for r in b) + ".", ""]

    nd = run / "network_diagnostic.json"
    if nd.exists():
        d = json.loads(nd.read_text(encoding="utf-8"))
        names = {"A_keepalive_post": "A: keep-alive POST (the benchmark's pattern)", "B_tiny_get_health": "B: tiny GET /health", "C_keepalive_post_tcp_nodelay": "C: keep-alive POST + TCP_NODELAY",
                 "D_new_connection_per_request": "D: new connection per request"}
        body = []
        for k, label in names.items():
            h, c_ = d["host_to_published_port"][k], d["container_on_docker_network"][k]
            body.append([label, f(h["client_median_ms"], 1), f(h.get("client_minus_orchestrator_ms"), 1), f(c_["client_median_ms"], 1), f(c_.get("client_minus_orchestrator_ms"), 1)])
        L += [f"**Network-path diagnostic** (`{rel(nd)}`; small profile, {d['requests_per_variant']} requests per variant after {d['warmup']} warm-up): the same request from the Windows host through Docker Desktop's "
              "published port versus from a container on the stack's Docker network. Medians in ms; 'overhead' = client time minus the orchestrator's own total.", "",
              md_table(["Variant", "Host -> published port: client", "overhead", "Container on Docker network: client", "overhead"], body), ""]
    if hrun:
        hl = rd(hrun / "latency_summary.csv")
        body = [[x["profile"], x["arm"], x["N"], f(x["e2e_median_ms"]), f(x["e2e_p95_ms"]), f"{f(x['repeat_median_min_ms'])}-{f(x['repeat_median_max_ms'])}", f(x["orchestrator_total_median_ms"]),
                 f(x["client_to_orchestrator_overhead_median_ms"]), x["errors"]] for x in sorted(hl, key=lambda x: (PROFILES.index(x["profile"]), x["arm"], NORDER.index(x["N"])))]
        L += [f"**T4c-b Secondary layer: load generator on the Windows host through the published port** (run `{hrun.name}`, `{rel(hrun / 'latency_summary.csv')}`): same protocol, same stack, but the client is on the host. "
              "The 'client<->orchestrator overhead' column is the ~45 ms artefact of Docker Desktop's port proxy on keep-alive POSTs (see the diagnostic), not a property of the services; "
              "it is reported because it is what a developer on this machine experiences and because it must not be mistaken for service overhead.", "",
              md_table(["Profile", "Arm", "N", "E2E median", "E2E p95", "Repeat medians range", "Orchestrator total (median)", "Client<->orch overhead", "Errors"], body), ""]
        if (hrun / "concurrency.csv").exists():
            L += [f"Concurrency through the published port (`{rel(hrun / 'concurrency.csv')}`), same protocol as T4d:", "",
                  md_table(["Profile", "Arm", "Clients", "Throughput rps (median of runs)", "Throughput range", "Median latency ms", "p95 ms", "Errors", "Requests"], agg_conc(rd(hrun / "concurrency.csv"))), ""]
    hrun = host_port_run()
    sm = next((d / "smoke_test.json" for d in (run, hrun) if d and (d / "smoke_test.json").exists()), run / "smoke_test.json")
    if sm.exists():
        s = json.loads(sm.read_text(encoding="utf-8"))
        L += [f"**End-to-end smoke test, `/rag` with generation (separate run, Ollama on the host; 6.7)** (`{rel(sm)}`): Ollama reachable from the stack: {s['ollama_reachable_on_host']}; all calls OK: **{s['all_ok']}**; "
              f"classical N=5000 answers equal the Phase 5 stored answers (parity of live retrieval + prompt + cache with the offline pipeline): {s['parity_cases_equal']}.", "",
              md_table(["Case", "Status", "Cached", "Wall s", "Contexts", "Answer"],
                       [[c["case"], c["status"], c.get("answer_cached", "-"), f(c["wall_s"], 1), c.get("n_contexts", "-"), (c.get("answer") or c.get("detail") or "")[:70].replace("|", "/")] for c in s["cases"]]), ""]
        idx.append(["P6-3", 6, f"Smoke test /rag: all ok = {s['all_ok']}; Phase 5 parity {s['parity_cases_equal']}", rel(sm)])
    cf = run / "cpu_freq_per_repeat.json"
    if cf.exists():
        fr = json.loads(cf.read_text(encoding="utf-8"))
        mhz = [x for r in fr for x in (r["cpu_mhz_start"], r["cpu_mhz_end"])]
        L += [f"**Measurement hygiene (H7)** (`{rel(run / 'hygiene.json')}`): plugged in = {hy['power_plugged']}, battery {hy['battery_percent']}%, power scheme `{hy['power_scheme']}`, host free RAM at start {hy['host_free_ram_gb_at_start']:.2f} GB, "
              f"CPU temperature: {hy['cpu_temperature']}. CPU MHz at repeat boundaries: min {min(mhz):.0f}, max {max(mhz):.0f}. {hy['load_generator']}.", ""]
    xml = run / "pytest_junit.xml"
    if xml.exists():
        r = ET.parse(xml).getroot()
        ts = r if r.tag == "testsuite" else r.find("testsuite")
        tot, fail, err, skip = (int(ts.get(x, 0)) for x in ("tests", "failures", "errors", "skipped"))
        L += [f"**pytest** (whole suite at Phase 6 exit, includes the in-process service integration tests): {tot} tests, {fail} failures, {err} errors, {skip} skipped (`{rel(xml)}`).", ""]
        idx.append(["P6-4", 6, f"pytest: {tot - fail - err - skip}/{tot} passed", rel(xml)])
    L += ["**Manuscript hook**: Section 4 (system design: services, profiles; Figure F1), Section 9 (latency, cloud overheads, concurrency); Tables T4c, T4d; figures F5b, F10.", ""]
    return "\n".join(L), idx
