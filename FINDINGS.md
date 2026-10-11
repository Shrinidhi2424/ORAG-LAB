# FINDINGS

Generated blocks are rewritten by `python scripts/report.py` from artifacts under `results/`.
Do not hand-type numbers inside generated blocks (R4).

## 0. Master Results Index
<!-- BEGIN:index -->
| ID | Phase | Key result | Artifact |
|---|---|---|---|
| P0-1 | 0 | SQuAD v1.1 downloaded and checksummed | results/phase0/phase0_20261011_202243/squad_checksums.json |
| P0-2 | 0 | Generator gate: chosen = qwen2.5:1.5b-instruct | results/phase0/phase0_20261011_202243/generator_bench_summary.json |
| P0-3 | 0 | pytest: 7/7 passed | results/phase0/phase0_20261011_202243/pytest_junit.xml |
| P1-1 | 1 | 20958 unique paragraphs; 300 eval questions on 275 gold paragraphs; ladder nested, gold in every rung | results/phase1/phase1_20261011_210325/corpus_stats.json |
| P1-2 | 1 | Embedded 20958 paragraphs in 864 s (24.3/s) | results/phase1/phase1_20261011_210325/embed_info.json |
| P1-3 | 1 | Exact-cosine ceiling Hit@1 = 72.0% (N=1000) to 49.0% (N=all) | results/phase1/phase1_20261011_210325/ceiling_by_N.csv |
| P1-4 | 1 | Sanity: norms in [1.0000, 1.0000], NaN=False, gold-cosine median 0.583 | results/phase1/phase1_20261011_210325/sanity.json |
| P1-5 | 1 | Model card mentions SQuAD: True (7 squad/wiki lines) | results/phase1/phase1_20261011_210325/contamination_check.json |
| P1-6 | 1 | pytest: 14/14 passed | results/phase1/phase1_20261011_210325/pytest_junit.xml |
<!-- END:index -->

## 1. Environment & Versions
<!-- BEGIN:env -->
Source: `results/phase0/phase0_20261011_202243/env.json`, `results/phase0/phase0_20261011_202243/run_manifest.json` (run `phase0_20261011_202243`).

| Item | Value |
|---|---|
| OS | Windows-11-10.0.26200-SP0 |
| CPU | 11th Gen Intel(R) Core(TM) i5-1135G7 @ 2.40GHz (4 cores / 8 threads) |
| RAM | 8.33 GB |
| GPU(s) | NVIDIA GeForce MX350; Intel(R) Iris(R) Xe Graphics - ignored (H3): torch CPU wheel, Ollama CPU-only |
| Disk free / total | 284.60 GB / 510.75 GB |
| Python | 3.12.6 |
| Git | git version 2.49.0.windows.1 |
| Ollama | ollama version is 0.40.3 |
| Docker CLI | Docker version 29.8.2, build 7fc2dff |
| Docker Compose | Docker Compose version v5.5.1 |
| Docker daemon at Phase 0 | NOT running |
| Git commit at run time | none (no commits yet) (dirty=True) |

Pinned packages (full list: `requirements.lock`):

| Package | Version |
|---|---|
| numpy | 2.5.4 |
| scipy | 1.18.1 |
| pandas | 3.0.6 |
| faiss-cpu | 1.15.1 |
| sentence-transformers | 6.1.0 |
| torch | 2.14.1+cpu |
| transformers | 5.19.0 |
| qiskit | 2.5.2 |
| qiskit-aer | 0.17.2 |
| fastapi | 0.143.0 |
| uvicorn | 0.54.0 |
| httpx | 0.28.1 |
| pydantic | 2.14.0 |
| pytest | 9.1.1 |
| matplotlib | 3.11.2 |
| pyyaml | 6.0.3 |
| datasets | 5.1.0 |
| ollama | 0.6.3 |
| psutil | 7.2.2 |
<!-- END:env -->

## 2. Phase Reports

### Phase 0 - Setup, environment, scaffolding
<!-- BEGIN:phase0 -->
Run `phase0_20261011_202243` - manifest: `results/phase0/phase0_20261011_202243/run_manifest.json`.

**SQuAD v1.1** (official JSON; checksums also in `data/squad_v1.1.checksums.json`, raw files in git-ignored `data/raw/`)

| File | Bytes | Articles | Paragraphs | Questions | SHA-256 |
|---|---|---|---|---|---|
| train-v1.1.json | 30288272 | 442 | 18896 | 87599 | `3527663986b8295af4f7fcdff1ba1ff3f72d07d61a20f487cb238a6ef92fd955` |
| dev-v1.1.json | 4854279 | 48 | 2067 | 10570 | `95aa6a52d5d6a735563366753ca50492a658031da74f301ac5238b03966972c9` |

**Generator benchmark gate (H2)** - CPU-only, options `{"temperature": 0, "seed": 42, "num_ctx": 2048, "num_predict": 48, "num_gpu": 0}`, 10 fixed RAG-style prompts, 1 discarded warm-up.
Decision rule: largest passing (a) median<=10s (b) peak RAM<=2.5GB (c) >=8/10 clean. Source: `results/phase0/phase0_20261011_202243/generator_bench_summary.json`, per-prompt rows `results/phase0/phase0_20261011_202243/generator_bench.csv`.

| Model | Median s/query | p95 s | Median tok/s | Median prompt tok | Median prompt-eval s | Ollama working set (GB) | System RAM drop (GB) | ollama ps size (GB) | RAM metric used for (b) (GB) | Min free RAM (GB) | Swap delta (MB) | Clean | Warm-up+load s | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| qwen2.5:1.5b-instruct | 6.284 | 8.043 | 21.89 | 623.0 | 5.49 | 0.032 | 1.113 | 1.109 | 1.113 | 0.994 | 171.0 | 10/10 | 6.21 | PASS |
| llama3.2:1b | 9.201 | 11.536 | 18.81 | 615.5 | 8.463 | 0.033 | 1.469 | 1.45 | 1.469 | 0.845 | 41.7 | 10/10 | 10.77 | PASS |
| llama3.2:3b | 13.085 | 16.58 | 11.06 | 615.5 | 12.256 | 0.033 | 2.485 | 2.325 | 2.485 | 0.259 | 465.8 | 10/10 | 16.02 | FAIL (a) |

**Chosen generator: `qwen2.5:1.5b-instruct`**

- `qwen2.5:1.5b-instruct` digest `65ec06548149b04c096a120e4a6da9d4017ea809c91734ea5631e89f96ddc57b`; Ollama `ps` after warm-up: `[{"name": "qwen2.5:1.5b-instruct", "size": 1109162720, "size_vram": 0}]`
- `llama3.2:1b` digest `baf6a787fdffd633537aa2eb51cfd54cb93ff08e28040095462bb63daf552878`; Ollama `ps` after warm-up: `[{"name": "llama3.2:1b", "size": 1450086235, "size_vram": 0}]`
- `llama3.2:3b` digest `a80c4f17acd55265feec403c7aef86be0c25983ab279d83f3bcd3abbcb5b8b72`; Ollama `ps` after warm-up: `[{"name": "llama3.2:3b", "size": 2324546189, "size_vram": 0}]`

**pytest**: 7 tests, 0 failures, 0 errors, 0 skipped (`results/phase0/phase0_20261011_202243/pytest_junit.xml`).

**Manuscript hook**: Section 5 (Experimental setup: LLM, hardware) and Table T2.
<!-- END:phase0 -->

### Phase 1 - Corpus, embeddings, eval set, ground truth
<!-- BEGIN:phase1 -->
Run `phase1_20261011_210325` - manifest: `results/phase1/phase1_20261011_210325/run_manifest.json`; config: seeds 42, eval n=300, ladder 1k/2k/5k/10k/all, ground-truth k=50.

**T1a corpus / eval set** (`results/phase1/phase1_20261011_210325/corpus_stats.json`)

| Quantity | Value |
|---|---|
| Raw paragraphs train / dev | 18896 / 2067 |
| Exact duplicates dropped | 5 |
| Unique paragraphs | 20958 |
| Dev questions with gold paragraph in corpus | 10570 |
| Eval questions (seed 42) | 300 |
| Distinct gold paragraphs among eval questions | 275 |
| Words per paragraph mean / median / p95 / max | 117.2 / 108 / 210 / 653 |
| Ladder nested | True |
| Gold in every rung | True |

**T1b corpus ladder** (`data/ladder_N.json`)

| Rung | Paragraphs | Gold included | Distractors |
|---|---|---|---|
| 1000 | 1000 | 275 | 725 |
| 2000 | 2000 | 275 | 1725 |
| 5000 | 5000 | 275 | 4725 |
| 10000 | 10000 | 275 | 9725 |
| all | 20958 | 275 | 20683 |

**Embedding** (`results/phase1/phase1_20261011_210325/embed_info.json`)

| Item | Value |
|---|---|
| Model / revision | `sentence-transformers/all-MiniLM-L6-v2` @ `1110a243fdf4706b3f48f1d95db1a4f5529b4d41` |
| Device / torch threads / batch | cpu / 4 / 64 |
| Dim / padded dim | 384 / 512 |
| Paragraph embedding time | 864.0 s (24.3 paragraphs/s) |
| Query embedding time | 1.73 s (173.5 queries/s) |
| Process RSS after embedding | 0.54 GB |
| max_seq_length (tokens) | 256 |
| Paragraph tokens mean / median / max | 154.4 / 142 / 855 |
| Paragraphs truncated by max_seq_length | 1494 (7.1%) |

**Classical ceiling: exact cosine vs gold paragraph, 300 queries** (`results/phase1/phase1_20261011_210325/ceiling_by_N.csv`; top-50 ground truth in `results/phase1/phase1_20261011_210325/ground_truth_N*.npz`)

| N | Corpus size | Hit@1 | Hit@3 | Hit@5 | Hit@10 | P@1 | P@3 | P@5 | P@10 | MRR@10 | nDCG@10 | Median gold rank | Brute-force s (300 q) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1000 | 1000 | 0.720 | 0.860 | 0.900 | 0.940 | 0.720 | 0.287 | 0.180 | 0.094 | 0.796 | 0.831 | 1.0 | 0.024 |
| 2000 | 2000 | 0.690 | 0.827 | 0.873 | 0.917 | 0.690 | 0.276 | 0.175 | 0.092 | 0.766 | 0.802 | 1.0 | 0.044 |
| 5000 | 5000 | 0.623 | 0.777 | 0.817 | 0.880 | 0.623 | 0.259 | 0.163 | 0.088 | 0.708 | 0.749 | 1.0 | 0.099 |
| 10000 | 10000 | 0.573 | 0.747 | 0.783 | 0.833 | 0.573 | 0.249 | 0.157 | 0.083 | 0.662 | 0.703 | 1.0 | 0.233 |
| all | 20958 | 0.490 | 0.680 | 0.733 | 0.783 | 0.490 | 0.227 | 0.147 | 0.078 | 0.590 | 0.637 | 2.0 | 0.563 |

Note: P@k is upper-bounded by 1/k with a single gold paragraph (A.4).

**Data sanity** (`results/phase1/phase1_20261011_210325/sanity.json`, `results/phase1/phase1_20261011_210325/gold_cosine.csv`)

| Check | Result |
|---|---|
| NaNs in embeddings | False |
| Paragraph norm min / max | 1.000000 / 1.000000 |
| Query norm min / max | 1.000000 / 1.000000 |
| 512-d padded norm max abs deviation from 1 | 1.19e-07 |
| Gold cosine change from padding (max abs) | 0.00e+00 |
| Padding columns all zero | True |
| Question-gold cosine min / p5 / median / p95 / max | 0.006 / 0.259 / 0.583 / 0.759 / 0.833 |
| Negative cosines in exact top-10 (per rung) | 1000: 0, 2000: 0, 5000: 0, 10000: 0, all: 0 |
| Min top-10 cosine (per rung) | 1000: 0.182, 2000: 0.198, 5000: 0.219, 10000: 0.253, all: 0.272 |

**Embedder contamination check (D7)** - model card saved at `results/phase1/phase1_20261011_210325/model_card.md` (revision `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`, 175 lines). Card mentions SQuAD: **True**. Lines mentioning squad/wikipedia/wiki:

- line 23: `- wikihow`
- line 29: `- embedding-data/simple-wiki`
- line 33: `- embedding-data/WikiAnswers`
- line 145: `| [WikiAnswers](https://github.com/afader/oqa#wikianswers-corpus) Duplicate question pairs | [paper](https://doi.org/10.1145/2623330.2623677) | 77,427,422 |`
- line 168: `| [Wikihow](https://github.com/pvl/wikihow_pairs_dataset) | [paper](https://arxiv.org/abs/1810.09305) | 128,542 |`
- line 171: `| [Simple Wikipedia](https://cs.pomona.edu/~dkauchak/simplification/) | [paper](https://www.aclweb.org/anthology/P11-2117/) | 102,225 |`
- line 173: `| [SQuAD2.0](https://rajpurkar.github.io/SQuAD-explorer/) | [paper](https://aclanthology.org/P18-2124.pdf) | 87,599 |`

Interpretation: see Section 5. A model card cannot prove absence of overlap.

**pytest** (whole suite at Phase 1 exit): 14 tests, 0 failures, 0 errors, 0 skipped (`results/phase1/phase1_20261011_210325/pytest_junit.xml`).

**Manuscript hook**: Section 5 (corpus, ladder, embeddings), Table T1; contamination discussion in Section 11.
<!-- END:phase1 -->

## 3. Headline Findings
(Filled in Phase 9.)

## 4. Deviations from Plan
<!-- BEGIN:deviations -->
- **D-0.1 max_tokens**: plan says 48 in D9/H2 but 64 in Appendix A.5. Phase 0 benchmark uses 48 (H2). To be settled before Phase 5; default = 48 for every arm.
- **D-0.2 Docker daemon**: Docker CLI/Compose are installed but the Docker Desktop engine was not running during Phase 0 (not started, to save RAM). Required only from Phase 6 (see H6).
- **D-0.3 Gate criterion (b)**: "peak RAM with VS Code open and no swapping" is approximated by the maximum of Ollama process working set, system free-RAM drop during the run, and the model size reported by `ollama ps`, sampled every 0.25 s; pagefile growth is reported separately.
- **D-0.4 Benchmark prompt mix**: 7 of 10 benchmark prompts contain the gold paragraph, 3 do not (to exercise abstention). "Clean" = non-empty, finished (done_reason=stop), and either the abstain phrase or at most 30 words. Correctness is recorded for information only.
- **D-0.5 locust** (optional in task 0.3) was not installed; add in Phase 6 if the concurrency test needs it.
- **D-0.6 CPU enforcement**: GPU use is disabled per request via Ollama option `num_gpu=0` (and torch is the CPU wheel); the Ollama server itself was not restarted with CUDA_VISIBLE_DEVICES=-1.
- **D-0.7 Invalidated first benchmark run**: the first run measured RAM as summed Ollama RSS, which under-reported mmap-ed weights (near-zero values). It was discarded (kept for transparency in `results/phase0/_superseded/`) and the run was repeated with system-level RAM metrics (see criterion (b) in D-0.3, now the maximum of process working set, system free-RAM drop and `ollama ps` size).
<!-- END:deviations -->

## 5. Failures, Limitations, Threats to Validity
<!-- BEGIN:failures -->
- **Swap during benchmark**: the pagefile grew during every model's run (see the "Swap delta" column in the Phase 0 table), so the strict "no swapping" wording of H2(b) is not fully met on this 8 GB machine even for the chosen model; close browsers and other heavy apps during generation runs (H5/H10).
- **Embedder contamination (D7, Phase 1)**: the all-MiniLM-L6-v2 model card (`results/phase1/*/contamination_check.json`) lists SQuAD among its training datasets, with a pair count equal to the SQuAD v1.1 *train* question count (Phase 0 `squad_checksums.json`). So the embedder very probably saw SQuAD train question-paragraph pairs. Evaluation questions come from *dev*, which that count does not cover, but most corpus paragraphs are train paragraphs (see the T1a table); retrieval quality may be optimistic versus an unseen domain, and the same holds for both arms (R1). The card cannot prove dev was excluded. Discuss in the manuscript limitations.
- **Truncation (Phase 1)**: paragraphs longer than the embedder's max_seq_length are truncated before embedding (count and fraction in the Phase 1 embedding table); the gold answer may lie in the cut part for those paragraphs, lowering the classical ceiling equally for both arms.
- **3B model**: fails the latency criterion (a) and leaves little RAM headroom; not usable on this laptop.
<!-- END:failures -->

## 6. Reproduction Commands
```
python tasks.py setup          # venv + pinned requirements.lock
python tasks.py env data bench # Phase 0 artifacts under results/phase0/<run_id>/
python tasks.py test report    # pytest + regenerate FINDINGS.md blocks
```

## 7. Open Questions for Human
<!-- BEGIN:open -->
(None recorded yet.)
<!-- END:open -->

## 8. Manuscript Numbers Sheet
(Generated in Phase 10.)
