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
"""

FAILURES = """- **Swap during benchmark**: the pagefile grew during every model's run (see the "Swap delta" column in the Phase 0 table), so the strict "no swapping" wording of H2(b) is not fully met on this 8 GB machine even for the chosen model; close browsers and other heavy apps during generation runs (H5/H10).
- **Embedder contamination (D7, Phase 1)**: the all-MiniLM-L6-v2 model card (`results/phase1/*/contamination_check.json`) lists SQuAD among its training datasets, with a pair count equal to the SQuAD v1.1 *train* question count (Phase 0 `squad_checksums.json`). So the embedder very probably saw SQuAD train question-paragraph pairs. Evaluation questions come from *dev*, which that count does not cover, but most corpus paragraphs are train paragraphs (see the T1a table); retrieval quality may be optimistic versus an unseen domain, and the same holds for both arms (R1). The card cannot prove dev was excluded. Discuss in the manuscript limitations.
- **Truncation (Phase 1)**: paragraphs longer than the embedder's max_seq_length are truncated before embedding (count and fraction in the Phase 1 embedding table); the gold answer may lie in the cut part for those paragraphs, lowering the classical ceiling equally for both arms.
- **3B model**: fails the latency criterion (a) and leaves little RAM headroom; not usable on this laptop.
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
    text = block(text, "index", md_table(["ID", "Phase", "Key result", "Artifact"], index_rows))
    text = seed_block(text, "deviations", DEVIATIONS)
    text = seed_block(text, "failures", FAILURES)
    text = seed_block(text, "open", "(None recorded yet.)\n")
    FINDINGS.write_text(text, encoding="utf-8", newline="\n")
    print(f"updated {FINDINGS}")


if __name__ == "__main__":
    main()
