"""Regenerate the machine-written blocks of FINDINGS.md from artifacts under results/ (R4).

Blocks are delimited by <!-- BEGIN:name --> / <!-- END:name -->. Everything outside the
blocks (deviations, failures, open questions: prose without numbers) is preserved.
"""
from __future__ import annotations

import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

FINDINGS = ROOT / "FINDINGS.md"

TEMPLATE = """# FINDINGS

Generated blocks are rewritten by `python scripts/report.py` from artifacts under `results/`.
Do not hand-type numbers inside generated blocks (R4).

## 0. Master Results Index
<!-- BEGIN:index -->
<!-- END:index -->

## 1. Environment & Versions
<!-- BEGIN:env -->
<!-- END:env -->

## 2. Phase Reports

### Phase 0 - Setup, environment, scaffolding
<!-- BEGIN:phase0 -->
<!-- END:phase0 -->

## 3. Headline Findings
(Filled in Phase 9.)

## 4. Deviations from Plan
<!-- BEGIN:deviations -->
<!-- END:deviations -->

## 5. Failures, Limitations, Threats to Validity
<!-- BEGIN:failures -->
<!-- END:failures -->

## 6. Reproduction Commands
```
python tasks.py setup          # venv + pinned requirements.lock
python tasks.py env data bench # Phase 0 artifacts under results/phase0/<run_id>/
python tasks.py test report    # pytest + regenerate FINDINGS.md blocks
```

## 7. Open Questions for Human
<!-- BEGIN:open -->
<!-- END:open -->

## 8. Manuscript Numbers Sheet
(Generated in Phase 10.)
"""

# Hand-authored prose (no numbers) seeded once; edited in place afterwards.
DEVIATIONS = """- **D-0.1 max_tokens**: plan says 48 in D9/H2 but 64 in Appendix A.5. Phase 0 benchmark uses 48 (H2). To be settled before Phase 5; default = 48 for every arm.
- **D-0.2 Docker daemon**: Docker CLI/Compose are installed but the Docker Desktop engine was not running during Phase 0 (not started, to save RAM). Required only from Phase 6 (see H6).
- **D-0.3 Gate criterion (b)**: "peak RAM with VS Code open and no swapping" is approximated by the maximum of Ollama process working set, system free-RAM drop during the run, and the model size reported by `ollama ps`, sampled every 0.25 s; pagefile growth is reported separately.
- **D-0.4 Benchmark prompt mix**: 7 of 10 benchmark prompts contain the gold paragraph, 3 do not (to exercise abstention). "Clean" = non-empty, finished (done_reason=stop), and either the abstain phrase or at most 30 words. Correctness is recorded for information only.
- **D-0.5 locust** (optional in task 0.3) was not installed; add in Phase 6 if the concurrency test needs it.
- **D-0.6 CPU enforcement**: GPU use is disabled per request via Ollama option `num_gpu=0` (and torch is the CPU wheel); the Ollama server itself was not restarted with CUDA_VISIBLE_DEVICES=-1.
- **D-0.7 Invalidated first benchmark run**: the first run measured RAM as summed Ollama RSS, which under-reported mmap-ed weights (near-zero values). It was discarded (kept for transparency in `results/phase0/_superseded/`) and the run was repeated with system-level RAM metrics (see criterion (b) in D-0.3, now the maximum of process working set, system free-RAM drop and `ollama ps` size).
- **D-2.1 Power mode (H7)**: the Windows power scheme during Phase 2 latency runs was "Balanced", not "Best performance" as H7 asks (recorded in the Phase 2 `hygiene.json`). I cannot change the user's power plan from this session; set Best performance and re-run `python tasks.py phase2` if tighter latency is needed. Conditions were still interleaved and shuffled per repeat.
- **D-2.2 Silhouette check skipped**: the Song et al.-style Silhouette choice of nlist is a [P2] item and was not run; nlist = round(sqrt N) is used throughout.
- **D-2.3 Thread pinning**: FAISS was pinned to 1 thread for in-process latency (low noise, comparable with the single-threaded numpy emulator in Phase 3); multi-thread results are not reported.
- **D-2.4 Ground-truth ties**: the numpy ground truth breaks score ties by lower position; FAISS Flat reproduced all top-50 lists identically (see the Flat-vs-numpy check in the Phase 2 report).
- **D-3.1 Validation pair mix**: plan 3.3a asks for 500 random corpus pairs. Random paragraph pairs have low cosine (cos^2 near 0), which would only test one end of the range, so the 500 pairs are 250 random corpus pairs plus 250 query-to-exact-top-50 pairs (the retrieval-relevant range). Validation uses unclipped (unbiased) estimates; retrieval uses estimates clipped to [0, 1] (plan 3.1).
- **D-3.2 Tier A without per-call transpile**: Aer executes set_statevector, h and cswap natively; with the same seed the estimates are identical with and without transpile (Phase 3 `tierA_timing.json`), so runs skip transpile (lower cost). The SWAP test itself is still executed by the simulator.
- **D-3.3 Zardini estimator (3.6, [P1]) deferred**: plan Section 0 says to finish all P0 work first; it requires reading the original paper to implement the exact formulas. It is not implemented yet and will be marked "not implemented" if time runs out.
- **D-3.4 Rankings not committed**: per-configuration rankings (`results/phase3/<run>/rankings/*.npz`) are git-ignored; they are fully seeded and regenerate exactly with `python tasks.py phase3`. All summary CSV/JSON files are committed.
- **D-3.5 Shot-threshold rule**: the exit gate "Hit@k within CI" is operationalised two ways: (1) paired bootstrap 95% CI of (quantum - classical) contains 0 at that S and at every larger S in the grid; (2) quantum mean inside the classical 95% CI. Rule (1) is strict: a small but consistent loss on a few queries is flagged as a difference. The formal, pre-registered tests (McNemar / Holm) are Phase 4 (4.6).
- **D-4.1 Two sources of quantum-sim randomness**: quality results (T3, tests, failure analysis) use the seeded Phase 3 rankings (shared random stream per configuration). The latency experiment runs `qrag/rerank.py` (`QuantumSimRetriever`) with its own per-repeat random stream: same distribution, different draws, so no quality metric is taken from the latency run. Full-scan latency uses argpartition + sort of the top-k (equal-key ties at the cut may differ from the stable full sort used for quality).
- **D-4.2 Latency k**: Phase 4 times k=10 (what the pipeline needs) whereas Phase 2 timed k=50; Flat latency was re-measured here, so Phase 2 and Phase 4 Flat numbers are not directly comparable. Power plan was again "Balanced" (see D-2.1).
- **D-4.3 Primary test choice (4.6)**: the plan pre-lists Hit@3 and MRR classical vs quantum with McNemar/paired-bootstrap and Holm. Because the quantum arm has 5 seeds, the primary test is a paired bootstrap on the per-query difference between the seed-averaged quantum outcome and the classical outcome (Holm within each 15-test family). Wilcoxon and exact McNemar (seed 0 only) are reported as uncorrected secondary checks and are not used for conclusions.
- **D-4.4 Memory (4.2)**: "memory vs N" is accounted from serialised index bytes and array sizes (Phase 2 `build.csv`), not from per-process RSS.
- **D-5.1 Closed-book prompt**: Appendix A.5 only defines the context prompt, whose instruction makes a context-free model abstain by construction. The closed-book control therefore uses "Answer the question from your own knowledge. If you do not know the answer, reply exactly: I don't know." (`qrag/generate.py`); the abstention regex accepts both phrases.
- **D-5.2 max_tokens = 48** for every arm (H2/D9 value; A.5 says 64; see D-0.1). Truncated answers are counted in the Phase 5 report.
- **D-5.3 HHEM inputs**: premise = the k retrieved paragraphs joined by blank lines; hypothesis = 'The answer to the question "<q>" is <answer>' (a bare short span is hard to judge). HHEM-2.1-Open documents unlimited context and its `predict` does not truncate, so long premises (the flan-T5 tokenizer warns above 512 tokens) were scored in full. Abstained and closed-book answers are not HHEM-scored (the taxonomy does not need F for them).
- **D-5.4 Retrieval in the RAG runs is read from saved rankings**: classical contexts are the Phase 1 exact top-3, quantum contexts the seeded Phase 3 top-3 (seed 0 unless stated), via `qrag/pipeline.py` `PrecomputedRetrieval`; a live retriever with the same semantics exists for the services. Random-context control: 3 paragraphs drawn uniformly from the whole corpus with seed [42, question], gold excluded.
- **D-5.5 Run matrix**: all P0 and P1 rows of plan 5.3 were run (P1: S=4096 at N=5000/all; N=1000 classical + S 64/256/1024/4096; seeds 1-2 at S=256 for N=5000/all). P2 (k=5, SQuAD v2 probe) not run.
- **D-6.1 Profiles apply to the compute services**: small / medium / large (1 CPU 1.5 GB, 2 CPU 2 GB, 4 CPU 3 GB) limit the embedder and the two retrievers; orchestrator and generator-gateway have a fixed 0.5 CPU / 384 MB limit. Limits are cgroup caps on a 3 GB / 4-CPU WSL2 VM, not reservations.
- **D-6.2 Primary HTTP load generator is a container on the Docker network**: a first full run used a client on the Windows host through Docker Desktop's published port. A diagnostic (Phase 6 `network_diagnostic.json`) showed that on this machine keep-alive POSTs with a body pick up a constant extra delay on that path (not fixed by TCP_NODELAY, absent for new connections and for a client inside the network). That run is kept, clearly labelled, as the secondary layer (T4c-b); the primary tables use the in-network client. Both ran the same protocol and code (`scripts/http_bench.py`; the first run used an earlier driver revision that contained the same measurement code).
- **D-6.3 "Ollama stopped"**: for latency and concurrency the model was unloaded (`ollama ps` shows no model) but the idle Ollama server process stayed running (Windows tray app); the smoke test was run last, separately. A hard stop was not done to avoid interfering with the user's session.
- **D-6.4 Host environment**: `%UserProfile%/.wslconfig` (memory 3 GB, processors 4, swap 2 GB; H6) was created by this phase and WSL was shut down once to apply it. Three unrelated idle containers of another project were already running in the same Docker VM and were left untouched (listed in the hygiene file). Host free RAM at the start of the runs was low (see hygiene).
- **D-6.5 No-container fallback implemented but not used**: `scripts/launch_services.py` (uvicorn processes + cpu_affinity) exists, but Docker worked, so every reported number comes from containers.
- **D-6.6 P2 item 6.6 (free-tier cloud rerun) not done.**
- **D-6.7 Smoke test via the published port**: the end-to-end `/rag` smoke test (with generation) goes through the host port, which is fine because it is a functional test, not a latency measurement.
"""

FAILURES = """- **Swap during benchmark**: the pagefile grew during every model's run (see the "Swap delta" column in the Phase 0 table), so the strict "no swapping" wording of H2(b) is not fully met on this 8 GB machine even for the chosen model; close browsers and other heavy apps during generation runs (H5/H10).
- **Embedder contamination (D7, Phase 1)**: the all-MiniLM-L6-v2 model card (`results/phase1/*/contamination_check.json`) lists SQuAD among its training datasets, with a pair count equal to the SQuAD v1.1 *train* question count (Phase 0 `squad_checksums.json`). So the embedder very probably saw SQuAD train question-paragraph pairs. Evaluation questions come from *dev*, which that count does not cover, but most corpus paragraphs are train paragraphs (see the T1a table); retrieval quality may be optimistic versus an unseen domain, and the same holds for both arms (R1). The card cannot prove dev was excluded. Discuss in the manuscript limitations.
- **Truncation (Phase 1)**: paragraphs longer than the embedder's max_seq_length are truncated before embedding (count and fraction in the Phase 1 embedding table); the gold answer may lie in the cut part for those paragraphs, lowering the classical ceiling equally for both arms.
- **3B model**: fails the latency criterion (a) and leaves little RAM headroom; not usable on this laptop.
- **Latency noise (Phase 2)**: for the larger indexes the repeat-to-repeat medians of Flat search differ noticeably (see the "run-to-run range" column of T4a), CPU temperature was not monitored and the power plan was Balanced, so small latency differences between arms at large N must be read against that range, not the pooled median alone. No repeat was discarded.
- **Tier A vs Tier B, repeated-estimate KS (Phase 3)**: on the repeated-estimates subset the pooled two-sample KS test of standardised errors gives p below 0.05 (uncorrected; exact value in the Phase 3 validation paragraph), while the single-estimate KS test, the bias, the variance-to-theory ratios and the log-log slopes all agree with equivalence. With the four KS tests in the validation, Holm correction would not reject; this is reported, not explained away. Pooled z-scores of a lattice-valued estimator (2k/S - 1) are not continuous, which the KS test assumes.
- **Sign loss in full scan (Phase 3)**: the SWAP test estimates cos^2, so in the full-scan protocol strongly negative paragraphs can outrank weak positive top-10 items even with infinite shots (counts per N in the negative-cosine audit). The shortlist protocol (M <= 100) contained no negative cosines.
- **Full-scan quality gap (Phase 3)**: for the larger corpora the full-scan quantum arm does not become statistically indistinguishable from classical on Hit@3 within the shot grid (see `shot_thresholds.csv`), so full-scan results are not used as the main arm.
- **Latency noise limits the scaling claims (Phase 4)**: the range of the 5 repeat medians is wide for the larger corpora (T4b, last column), the power plan was Balanced and temperature was not monitored. The log-log exponent confidence intervals are correspondingly wide and several overlap (Flat, shortlist, full scan); the data do not support ranking those three by scaling exponent. IVF has the lowest exponent estimate, but its interval also overlaps the others at its upper end.
- **No latency advantage for the quantum-sim arm (Phase 4)**: with the shortlist protocol the exact Flat search is executed first, so the arm's latency is the Flat search plus a small estimator cost (stage breakdown table); full scan costs more than Flat. This is emulated-estimator latency and says nothing about quantum hardware; modelled shot and gate counts are listed separately and are not wall-clock times.
- **Tier B emulator at low shot counts (Phase 4)**: quality at S=256 is far below classical at every N (Table T3); the shot budget needed to be statistically indistinguishable grows with N (Phase 3 threshold table), consistent with the 1/sqrt(S) noise vs a shrinking score margin among more distractors. This is an observation, not a tested mechanism.
- **Single small generator (Phase 5)**: all answers come from one 1.5B model (H2). It rarely abstains when the gold paragraph is missing (see the mediation table), so most retrieval misses turn into confident wrong answers; a larger or better-calibrated model may abstain more. Absolute rates are specific to this model; the claim is only about differences between retrieval arms with the generator held fixed (R1).
- **Hallucination measurement limits (Phase 5)**: correctness is SQuAD-style string containment (misses paraphrases, accepts answers that merely mention the span); faithfulness is one automatic judge (HHEM) without human validation until the audit sheet is labelled; T-c covers only seed 0. Generation ran under heavy memory pressure (free RAM fell to the low hundreds of MB, see the generation session file); this affects generation time only, not outputs (deterministic decoding, cached).
- **Generation is not bit-reproducible (Phase 5)**: with temperature 0 and a fixed seed, re-running the same prompts on this CPU without the cache sometimes yields different wording (and rarely different content), even for an immediate repeat of the same request (counts in the regeneration check). Correctness and abstention labels were unchanged in every sampled case, so the reported outcome rates are not sensitive to this in the sample, but R6's "exact reruns" holds only through the answer cache (`cache/llm`, git-ignored; the committed `generations.jsonl` carries every answer text and cache key). Prompts with identical contexts share one cached answer across arms, so arm comparisons are exactly paired where contexts coincide. Likely cause (not tested): non-deterministic parallel floating-point reductions or KV-cache reuse in the CPU runner.
- **LLM contamination looks low (Phase 5)**: the closed-book control answers few questions correctly (Phase 5 table), so the generator's parametric knowledge of SQuAD dev explains little of the RAG accuracy. The embedder contamination (Phase 1) remains.
- **Docker Desktop published-port artefact (Phase 6)**: latency measured from the Windows host through the published port includes a large constant client-side delay that is neither service nor network cost in a cloud-like deployment (network diagnostic). Numbers from that path (T4c-b) must not be quoted as service overhead.
- **More CPU did not mean lower latency at low load (Phase 6)**: the embedder's per-request compute time was not lower under the large profile (4 threads) than under small or medium (1-2 threads) in the in-network run, and single-client throughput was lower for large; the cause was not investigated (candidates: thread oversubscription of a 4-core/8-thread laptop that also hosts the load generator, small-batch thread overhead). The profile comparison is therefore about this host, not about cloud instance types.
- **Shared-host measurement (Phase 6)**: the services, the load generator, Docker Desktop and Windows share one 8 GB laptop; power plan Balanced; temperature not monitored; host free RAM was low at the start of the runs. The embedding step (a transformer forward pass of ~15-25 ms) dominates the request in every profile and masks retrieval differences: classical and quantum-sim arms are indistinguishable at N <= 5000 over HTTP, and the arm and N effects at N=all are small compared with the run-to-run range.
- **Concurrency is a closed-loop test (Phase 6)**: N concurrent clients each wait for their response; there is no open-loop arrival process, so tail latencies at saturation are not queueing-theory estimates. Occasional multi-second p95 values in single runs (visible in the raw concurrency CSVs) were not investigated; medians over 3 runs are reported.
"""


def block(text: str, name: str, body: str) -> str:
    pat = re.compile(rf"(<!-- BEGIN:{name} -->\n).*?(<!-- END:{name} -->)", re.S)
    return pat.sub(lambda m: m.group(1) + body.rstrip("\n") + "\n" + m.group(2), text)


def seed_block(text: str, name: str, body: str) -> str:
    """Fill a hand-authored block only if it is still empty."""
    m = re.search(rf"<!-- BEGIN:{name} -->\n(.*?)<!-- END:{name} -->", text, re.S)
    return text if (m and m.group(1).strip()) else block(text, name, body)


def latest_run(phase: str) -> Path | None:
    cur = ROOT / "results" / phase / ".current_run"
    if cur.exists():
        d = ROOT / "results" / phase / cur.read_text(encoding="utf-8").strip()
        if d.exists():
            return d
    runs = sorted(p for p in (ROOT / "results" / phase).glob(f"{phase}_*") if p.is_dir())
    return runs[-1] if runs else None


def rel(p: Path) -> str:
    return p.relative_to(ROOT).as_posix()


def gb(x: float) -> str:
    return f"{x / 1e9:.2f} GB"


def md_table(header: list[str], rows: list[list]) -> str:
    out = ["| " + " | ".join(header) + " |", "|" + "|".join("---" for _ in header) + "|"]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


def env_block(run: Path) -> str:
    env = json.loads((run / "env.json").read_text(encoding="utf-8"))
    man = json.loads((run / "run_manifest.json").read_text(encoding="utf-8"))
    h, t = env["host"], env["tools"]
    dd = env["docker_daemon"]
    lines = [
        f"Source: `{rel(run / 'env.json')}`, `{rel(run / 'run_manifest.json')}` (run `{run.name}`).", "",
        md_table(["Item", "Value"], [
            ["OS", h["os"]],
            ["CPU", f"{env['cpu_model']} ({h['cpu_physical_cores']} cores / {h['cpu_logical_cores']} threads)"],
            ["RAM", gb(h["ram_total_bytes"])],
            ["GPU(s)", "; ".join(env["gpus"]) + f" - {env['gpu_policy']}"],
            ["Disk free / total", f"{gb(env['disk_free_bytes'])} / {gb(env['disk_total_bytes'])}"],
            ["Python", t["python"]],
            ["Git", t["git"]],
            ["Ollama", t["ollama"]],
            ["Docker CLI", t["docker_cli"]],
            ["Docker Compose", t["docker_compose"]],
            ["Docker daemon at Phase 0", f"running (server {dd['stdout']})" if dd["ok"] else "NOT running"],
            ["Git commit at run time", f"{man['git']['commit'] or 'none (no commits yet)'} (dirty={man['git']['dirty']})"],
        ]), "",
        "Pinned packages (full list: `requirements.lock`):", "",
        md_table(["Package", "Version"], [[k, v] for k, v in env["packages"].items()]),
    ]
    return "\n".join(lines)


def phase0_block(run: Path) -> tuple[str, list[list]]:
    index_rows: list[list] = []
    lines = [f"Run `{run.name}` - manifest: `{rel(run / 'run_manifest.json')}`.", ""]

    sq = run / "squad_checksums.json"
    if sq.exists():
        d = json.loads(sq.read_text(encoding="utf-8"))
        lines += ["**SQuAD v1.1** (official JSON; checksums also in `data/squad_v1.1.checksums.json`, raw files in git-ignored `data/raw/`)", "",
                  md_table(["File", "Bytes", "Articles", "Paragraphs", "Questions", "SHA-256"],
                           [[k, v["bytes"], v["articles"], v["paragraphs"], v["questions"], f"`{v['sha256']}`"] for k, v in d.items()]), ""]
        index_rows.append(["P0-1", 0, "SQuAD v1.1 downloaded and checksummed", rel(sq)])

    gb_path = run / "generator_bench_summary.json"
    if gb_path.exists():
        s = json.loads(gb_path.read_text(encoding="utf-8"))
        rows = []
        for m in s["models"]:
            rows.append([m["model"], m["median_wall_s"], m["p95_wall_s"], m["median_tokens_per_s"], m["median_prompt_tokens"],
                         m["median_prompt_eval_s"], m["peak_ollama_rss_gb"], m["system_ram_delta_gb"], m["ollama_ps_size_gb"], m["ram_metric_gb"], m["min_system_available_gb"], m["swap_used_delta_mb"],
                         f"{m['clean_count']}/10", m["warmup_incl_load_s"],
                         "PASS" if m["passes_gate"] else "FAIL (" + ", ".join(
                             k.split("_")[1] for k in ("pass_a_median_le_10s", "pass_b_ram_le_2.5gb", "pass_c_clean_ge_8") if not m[k]) + ")"])
        lines += [f"**Generator benchmark gate (H2)** - CPU-only, options `{json.dumps(s['options'])}`, 10 fixed RAG-style prompts, 1 discarded warm-up.",
                  f"Decision rule: {s['decision_rule']}. Source: `{rel(gb_path)}`, per-prompt rows `{rel(run / 'generator_bench.csv')}`.", "",
                  md_table(["Model", "Median s/query", "p95 s", "Median tok/s", "Median prompt tok", "Median prompt-eval s",
                            "Ollama working set (GB)", "System RAM drop (GB)", "ollama ps size (GB)", "RAM metric used for (b) (GB)", "Min free RAM (GB)", "Swap delta (MB)", "Clean", "Warm-up+load s", "Gate"], rows), "",
                  f"**Chosen generator: `{s['chosen']}`**" if s["chosen"] else "**No candidate passed the gate - see Fallback B/C in plan H2.**", ""]
        for m in s["models"]:
            lines.append(f"- `{m['model']}` digest `{m['digest']}`; Ollama `ps` after warm-up: `{json.dumps(m['ps_after_warmup'])}`")
        lines.append("")
        index_rows.append(["P0-2", 0, f"Generator gate: chosen = {s['chosen']}", rel(gb_path)])

    xml = run / "pytest_junit.xml"
    if xml.exists():
        r = ET.parse(xml).getroot()
        ts = r if r.tag == "testsuite" else r.find("testsuite")
        tot, fail, err, skip = (int(ts.get(k, 0)) for k in ("tests", "failures", "errors", "skipped"))
        lines += [f"**pytest**: {tot} tests, {fail} failures, {err} errors, {skip} skipped (`{rel(xml)}`).", ""]
        index_rows.append(["P0-3", 0, f"pytest: {tot - fail - err - skip}/{tot} passed", rel(xml)])
    lines += ["**Manuscript hook**: Section 5 (Experimental setup: LLM, hardware) and Table T2.", ""]
    return "\n".join(lines), index_rows


def main() -> None:
    text = FINDINGS.read_text(encoding="utf-8") if FINDINGS.exists() else TEMPLATE
    index_rows: list[list] = []
    run = latest_run("phase0")
    if run and (run / "env.json").exists():
        text = block(text, "env", env_block(run))
    if run:
        body, index_rows = phase0_block(run)
        text = block(text, "phase0", body)
    run1 = latest_run("phase1")
    if run1 and (run1 / "corpus_stats.json").exists():
        from report_phase1 import phase1_block

        if "<!-- BEGIN:phase1 -->" not in text:
            text = text.replace("## 3. Headline Findings", "### Phase 1 - Corpus, embeddings, eval set, ground truth\n"
                                "<!-- BEGIN:phase1 -->\n<!-- END:phase1 -->\n\n## 3. Headline Findings", 1)
        body1, rows1 = phase1_block(run1)
        text = block(text, "phase1", body1)
        index_rows += rows1
    run2 = latest_run("phase2")
    if run2 and (run2 / "quality.csv").exists():
        from report_phase2 import phase2_block

        if "<!-- BEGIN:phase2 -->" not in text:
            text = text.replace("## 3. Headline Findings", "### Phase 2 - Classical baseline (FAISS)\n"
                                "<!-- BEGIN:phase2 -->\n<!-- END:phase2 -->\n\n## 3. Headline Findings", 1)
        body2, rows2 = phase2_block(run2)
        text = block(text, "phase2", body2)
        index_rows += rows2
    run3 = latest_run("phase3")
    if run3 and (run3 / "tierA_timing.json").exists():
        from report_phase3 import phase3_block

        if "<!-- BEGIN:phase3 -->" not in text:
            text = text.replace("## 3. Headline Findings", "### Phase 3 - Quantum-inspired retrieval arm + validation\n"
                                "<!-- BEGIN:phase3 -->\n<!-- END:phase3 -->\n\n## 3. Headline Findings", 1)
        body3, rows3 = phase3_block(run3)
        text = block(text, "phase3", body3)
        index_rows += rows3
    run4 = latest_run("phase4")
    if run4 and (run4 / "main_table.csv").exists() and (run4 / "tests.csv").exists():
        from report_phase4 import phase4_block

        if "<!-- BEGIN:phase4 -->" not in text:
            text = text.replace("## 3. Headline Findings", "### Phase 4 - Retrieval-only experiments\n"
                                "<!-- BEGIN:phase4 -->\n<!-- END:phase4 -->\n\n## 3. Headline Findings", 1)
        body4, rows4 = phase4_block(run4)
        text = block(text, "phase4", body4)
        index_rows += rows4
    run5 = latest_run("phase5")
    if run5 and (run5 / "build_info.json").exists():
        from report_phase5 import phase5_block

        if "<!-- BEGIN:phase5 -->" not in text:
            text = text.replace("## 3. Headline Findings", "### Phase 5 - RAG pipeline + hallucination experiments\n"
                                "<!-- BEGIN:phase5 -->\n<!-- END:phase5 -->\n\n## 3. Headline Findings", 1)
        body5, rows5 = phase5_block(run5)
        text = block(text, "phase5", body5)
        index_rows += rows5
    run6 = latest_run("phase6")
    if run6 and (run6 / "hygiene.json").exists() and ((run6 / "latency_summary.csv").exists() or (run6 / "smoke_test.json").exists()):
        from report_phase6 import phase6_block

        if "<!-- BEGIN:phase6 -->" not in text:
            text = text.replace("## 3. Headline Findings", "### Phase 6 - Cloud-native deployment\n"
                                "<!-- BEGIN:phase6 -->\n<!-- END:phase6 -->\n\n## 3. Headline Findings", 1)
        body6, rows6 = phase6_block(run6)
        text = block(text, "phase6", body6)
        index_rows += rows6
    text = block(text, "index", md_table(["ID", "Phase", "Key result", "Artifact"], index_rows))
    text = seed_block(text, "deviations", DEVIATIONS)
    text = seed_block(text, "failures", FAILURES)
    text = seed_block(text, "open", "(None recorded yet.)\n")
    FINDINGS.write_text(text, encoding="utf-8", newline="\n")
    print(f"updated {FINDINGS}")


if __name__ == "__main__":
    main()
