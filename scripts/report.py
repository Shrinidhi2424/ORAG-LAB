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
    text = block(text, "index", md_table(["ID", "Phase", "Key result", "Artifact"], index_rows))
    text = seed_block(text, "deviations", DEVIATIONS)
    text = seed_block(text, "failures", FAILURES)
    text = seed_block(text, "open", "(None recorded yet.)\n")
    FINDINGS.write_text(text, encoding="utf-8", newline="\n")
    print(f"updated {FINDINGS}")


if __name__ == "__main__":
    main()
