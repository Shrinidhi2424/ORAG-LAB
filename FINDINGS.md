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
| P2-1 | 2 | Flat (FAISS) N=all: Hit@3 0.680, MRR@10 0.590 | results/phase2/phase2_20261011_212701/quality.csv |
| P2-2 | 2 | Flat search median 0.058 ms (N=1000) to 1.986 ms (N=all), k=50 | results/phase2/phase2_20261011_212701/latency_summary.csv |
| P2-3 | 2 | Query embedding median 13.0 ms (batch 1, CPU) | results/phase2/phase2_20261011_212701/query_embed_summary.json |
| P2-4 | 2 | Flat index 32191533 bytes at N=all | results/phase2/phase2_20261011_212701/build.csv |
| P2-5 | 2 | pytest: 19/19 passed | results/phase2/phase2_20261011_212701/pytest_junit.xml |
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

### Phase 2 - Classical baseline (FAISS)
<!-- BEGIN:phase2 -->
Run `phase2_20261011_212701` - manifest: `results/phase2/phase2_20261011_212701/run_manifest.json`. FAISS single-threaded, in-process; quality on 300 queries (bootstrap 95% CI, 10k resamples); latency: batch-1 queries, 10 warm-up discarded, 100 timed, 5 repeats, conditions shuffled per repeat.

**Classical Flat (exact) retrieval quality via FAISS IndexFlatIP** (`results/phase2/phase2_20261011_212701/quality.csv`)

| N | Hit@1 | Hit@3 | Hit@5 | Hit@10 | MRR@10 | nDCG@10 | P@3 | P@10 |
|---|---|---|---|---|---|---|---|---|
| 1000 | 0.720 [0.670, 0.770] | 0.860 [0.820, 0.897] | 0.900 [0.863, 0.933] | 0.940 [0.913, 0.967] | 0.796 [0.757, 0.834] | 0.831 [0.797, 0.864] | 0.287 | 0.094 |
| 2000 | 0.690 [0.637, 0.740] | 0.827 [0.783, 0.870] | 0.873 [0.833, 0.910] | 0.917 [0.883, 0.947] | 0.766 [0.724, 0.806] | 0.802 [0.765, 0.838] | 0.276 | 0.092 |
| 5000 | 0.623 [0.570, 0.680] | 0.777 [0.730, 0.823] | 0.817 [0.773, 0.860] | 0.880 [0.843, 0.917] | 0.708 [0.664, 0.752] | 0.749 [0.709, 0.790] | 0.259 | 0.088 |
| 10000 | 0.573 [0.517, 0.630] | 0.747 [0.697, 0.793] | 0.783 [0.737, 0.830] | 0.833 [0.790, 0.873] | 0.662 [0.616, 0.709] | 0.703 [0.660, 0.746] | 0.249 | 0.083 |
| all | 0.490 [0.433, 0.547] | 0.680 [0.627, 0.733] | 0.733 [0.683, 0.783] | 0.783 [0.737, 0.830] | 0.590 [0.542, 0.638] | 0.637 [0.592, 0.682] | 0.227 | 0.078 |

FAISS Flat vs numpy brute force (`results/phase2/phase2_20261011_212701/flat_vs_numpy_check.json`): fraction of queries with identical top-50 list / identical top-10 set: N=1000: 1.000 / 1.000; N=2000: 1.000 / 1.000; N=5000: 1.000 / 1.000; N=10000: 1.000 / 1.000; N=all: 1.000 / 1.000

**IVFFlat nprobe sweep** (nlist = round(sqrt N); k-means seed 42; Overlap@10 = recall of exact top-10; latency k=50, ms)

| N | nlist | nprobe | Overlap@10 vs exact | Hit@3 | Hit@10 | MRR@10 | median ms | p95 ms |
|---|---|---|---|---|---|---|---|---|
| 1000 | 32 | 1 | 0.574 | 0.650 [0.597, 0.703] | 0.700 [0.647, 0.750] | 0.600 | 0.010 | 0.013 |
| 1000 | 32 | 2 | 0.744 | 0.753 [0.703, 0.800] | 0.810 [0.767, 0.853] | 0.696 | 0.014 | 0.030 |
| 1000 | 32 | 4 | 0.854 | 0.823 [0.780, 0.867] | 0.897 [0.860, 0.930] | 0.764 | 0.020 | 0.039 |
| 1000 | 32 | 8 | 0.935 | 0.843 [0.800, 0.883] | 0.917 [0.883, 0.947] | 0.780 | 0.026 | 0.040 |
| 1000 | 32 | 16 | 0.986 | 0.860 [0.820, 0.897] | 0.943 [0.917, 0.967] | 0.797 | 0.038 | 0.064 |
| 1000 | 32 | 32 | 1.000 | 0.860 [0.820, 0.897] | 0.940 [0.913, 0.967] | 0.796 | 0.061 | 0.090 |
| 2000 | 45 | 1 | 0.584 | 0.620 [0.563, 0.673] | 0.667 [0.613, 0.720] | 0.578 | 0.013 | 0.019 |
| 2000 | 45 | 2 | 0.723 | 0.737 [0.687, 0.787] | 0.797 [0.750, 0.840] | 0.685 | 0.018 | 0.040 |
| 2000 | 45 | 4 | 0.835 | 0.787 [0.740, 0.830] | 0.857 [0.817, 0.893] | 0.729 | 0.023 | 0.037 |
| 2000 | 45 | 8 | 0.915 | 0.817 [0.773, 0.860] | 0.900 [0.863, 0.933] | 0.757 | 0.032 | 0.051 |
| 2000 | 45 | 16 | 0.973 | 0.823 [0.780, 0.867] | 0.913 [0.880, 0.943] | 0.762 | 0.052 | 0.070 |
| 2000 | 45 | 32 | 0.998 | 0.827 [0.783, 0.870] | 0.917 [0.883, 0.947] | 0.766 | 0.090 | 0.168 |
| 5000 | 71 | 1 | 0.573 | 0.507 [0.450, 0.563] | 0.540 [0.483, 0.597] | 0.468 | 0.018 | 0.032 |
| 5000 | 71 | 2 | 0.730 | 0.653 [0.600, 0.707] | 0.727 [0.677, 0.777] | 0.608 | 0.025 | 0.034 |
| 5000 | 71 | 4 | 0.836 | 0.720 [0.670, 0.770] | 0.810 [0.767, 0.853] | 0.666 | 0.039 | 0.076 |
| 5000 | 71 | 8 | 0.905 | 0.750 [0.700, 0.797] | 0.850 [0.810, 0.890] | 0.689 | 0.061 | 0.119 |
| 5000 | 71 | 16 | 0.958 | 0.770 [0.720, 0.817] | 0.867 [0.827, 0.903] | 0.703 | 0.101 | 0.154 |
| 5000 | 71 | 32 | 0.988 | 0.773 [0.727, 0.820] | 0.877 [0.840, 0.913] | 0.707 | 0.191 | 0.397 |
| 10000 | 100 | 1 | 0.596 | 0.480 [0.423, 0.537] | 0.530 [0.473, 0.587] | 0.422 | 0.024 | 0.051 |
| 10000 | 100 | 2 | 0.735 | 0.580 [0.523, 0.637] | 0.653 [0.600, 0.707] | 0.523 | 0.033 | 0.048 |
| 10000 | 100 | 4 | 0.847 | 0.687 [0.633, 0.737] | 0.760 [0.710, 0.807] | 0.617 | 0.057 | 0.108 |
| 10000 | 100 | 8 | 0.920 | 0.723 [0.673, 0.773] | 0.803 [0.757, 0.847] | 0.642 | 0.102 | 0.230 |
| 10000 | 100 | 16 | 0.965 | 0.727 [0.677, 0.777] | 0.807 [0.760, 0.850] | 0.645 | 0.180 | 0.274 |
| 10000 | 100 | 32 | 0.985 | 0.740 [0.690, 0.790] | 0.820 [0.777, 0.863] | 0.656 | 0.377 | 0.737 |
| all | 145 | 1 | 0.572 | 0.453 [0.400, 0.510] | 0.500 [0.443, 0.557] | 0.394 | 0.030 | 0.044 |
| all | 145 | 2 | 0.718 | 0.543 [0.487, 0.600] | 0.620 [0.563, 0.673] | 0.476 | 0.045 | 0.058 |
| all | 145 | 4 | 0.824 | 0.580 [0.527, 0.633] | 0.663 [0.610, 0.717] | 0.500 | 0.077 | 0.110 |
| all | 145 | 8 | 0.900 | 0.643 [0.590, 0.697] | 0.737 [0.687, 0.787] | 0.555 | 0.134 | 0.231 |
| all | 145 | 16 | 0.953 | 0.660 [0.607, 0.713] | 0.760 [0.710, 0.807] | 0.572 | 0.238 | 0.376 |
| all | 145 | 32 | 0.981 | 0.673 [0.620, 0.727] | 0.780 [0.733, 0.827] | 0.585 | 0.497 | 0.915 |

Best nprobe per N (smallest nprobe with mean Overlap@10 vs exact >= 0.95; else largest swept, `results/phase2/phase2_20261011_212701/best_nprobe.json`): N=1000: nprobe 16 (target met: True), N=2000: nprobe 16 (target met: True), N=5000: nprobe 16 (target met: True), N=10000: nprobe 16 (target met: True), N=all: nprobe 16 (target met: True)

**T4a Search latency per query, k=50** (`results/phase2/phase2_20261011_212701/latency_summary.csv`; raw samples `results/phase2/phase2_20261011_212701/latency_raw.csv`)

| N | Flat median ms | Flat p95 ms | Flat run-to-run range of repeat medians (ms) | IVF best nprobe | IVF median ms | IVF p95 ms |
|---|---|---|---|---|---|---|
| 1000 | 0.058 | 0.077 | 0.058-0.065 | 16 | 0.038 | 0.064 |
| 2000 | 0.104 | 0.169 | 0.104-0.105 | 16 | 0.052 | 0.070 |
| 5000 | 0.355 | 0.656 | 0.340-0.515 | 16 | 0.101 | 0.154 |
| 10000 | 0.937 | 2.010 | 0.896-1.785 | 16 | 0.180 | 0.274 |
| all | 1.986 | 4.308 | 1.729-3.793 | 16 | 0.238 | 0.376 |

Flat search median ms by k (shortlist sizes used in Phase 3):

| N | k=10 | k=50 | k=100 |
|---|---|---|---|
| 1000 | 0.050 | 0.058 | 0.073 |
| 2000 | 0.099 | 0.104 | 0.119 |
| 5000 | 0.377 | 0.355 | 0.430 |
| 10000 | 0.900 | 0.937 | 0.989 |
| all | 1.954 | 1.986 | 1.855 |

**Query embedding latency** (`results/phase2/phase2_20261011_212701/query_embed_summary.json`): median 13.02 ms, p95 22.23 ms, n=500, repeat medians 10.98-15.98 ms (batch size 1, CPU, torch threads 4, includes tokenisation).

Stage breakdown at N=all (median ms): embed query 13.02 + Flat search 1.986.

**Index build time and footprint** (`results/phase2/phase2_20261011_212701/build.csv`; median of 3 builds, IVF includes k-means training)

| Arm | N | nlist | Build s | Index bytes | Bytes/vector | Raw vectors bytes |
|---|---|---|---|---|---|---|
| flat | 1000 |  | 0.0005 | 1536045 | 1536.0 | 1536000 |
| ivf | 1000 | 32 | 0.0080 | 1593547 | 1593.5 | 1536000 |
| flat | 2000 |  | 0.0010 | 3072045 | 1536.0 | 3072000 |
| ivf | 2000 | 45 | 0.0163 | 3157619 | 1578.8 | 3072000 |
| flat | 5000 |  | 0.0022 | 7680045 | 1536.0 | 7680000 |
| ivf | 5000 | 71 | 0.0399 | 7829763 | 1566.0 | 7680000 |
| flat | 10000 |  | 0.0041 | 15360045 | 1536.0 | 15360000 |
| ivf | 10000 | 100 | 0.0530 | 15594539 | 1559.5 | 15360000 |
| flat | all |  | 0.0088 | 32191533 | 1536.0 | 32191488 |
| ivf | all | 145 | 0.0963 | 32583171 | 1554.7 | 32191488 |

**Measurement hygiene (H7)** (`results/phase2/phase2_20261011_212701/hygiene.json`): plugged in = True, battery 100%, power scheme: `Power Scheme GUID: 381b4222-f694-41f0-9685-ff5bb260df2e  (Balanced)`, FAISS threads = 1, CPU temperature: not monitored (no sensor tool on this host); cpu_freq per repeat logged as throttling proxy. Reported CPU MHz at repeat boundaries: min 2419, max 2419. conditions shuffled per repeat (seeded) so thermal drift hits all conditions alike (H7).

Peak working set of the benchmark process after each stage (GB, cumulative; `results/phase2/phase2_20261011_212701/stage_peak_rss_gb.json`): quality: 0.40, build: 0.49, latency: 0.49, qembed: 0.66

**pytest** (whole suite at Phase 2 exit): 19 tests, 0 failures, 0 errors, 0 skipped (`results/phase2/phase2_20261011_212701/pytest_junit.xml`).

**Manuscript hook**: Section 9 (latency), Section 7 (classical baseline), Table T4.
<!-- END:phase2 -->

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
- **D-2.1 Power mode (H7)**: the Windows power scheme during Phase 2 latency runs was "Balanced", not "Best performance" as H7 asks (recorded in the Phase 2 `hygiene.json`). I cannot change the user's power plan from this session; set Best performance and re-run `python tasks.py phase2` if tighter latency is needed. Conditions were still interleaved and shuffled per repeat.
- **D-2.2 Silhouette check skipped**: the Song et al.-style Silhouette choice of nlist is a [P2] item and was not run; nlist = round(sqrt N) is used throughout.
- **D-2.3 Thread pinning**: FAISS was pinned to 1 thread for in-process latency (low noise, comparable with the single-threaded numpy emulator in Phase 3); multi-thread results are not reported.
- **D-2.4 Ground-truth ties**: the numpy ground truth breaks score ties by lower position; FAISS Flat reproduced all top-50 lists identically (see the Flat-vs-numpy check in the Phase 2 report).
<!-- END:deviations -->

## 5. Failures, Limitations, Threats to Validity
<!-- BEGIN:failures -->
- **Swap during benchmark**: the pagefile grew during every model's run (see the "Swap delta" column in the Phase 0 table), so the strict "no swapping" wording of H2(b) is not fully met on this 8 GB machine even for the chosen model; close browsers and other heavy apps during generation runs (H5/H10).
- **Embedder contamination (D7, Phase 1)**: the all-MiniLM-L6-v2 model card (`results/phase1/*/contamination_check.json`) lists SQuAD among its training datasets, with a pair count equal to the SQuAD v1.1 *train* question count (Phase 0 `squad_checksums.json`). So the embedder very probably saw SQuAD train question-paragraph pairs. Evaluation questions come from *dev*, which that count does not cover, but most corpus paragraphs are train paragraphs (see the T1a table); retrieval quality may be optimistic versus an unseen domain, and the same holds for both arms (R1). The card cannot prove dev was excluded. Discuss in the manuscript limitations.
- **Truncation (Phase 1)**: paragraphs longer than the embedder's max_seq_length are truncated before embedding (count and fraction in the Phase 1 embedding table); the gold answer may lie in the cut part for those paragraphs, lowering the classical ceiling equally for both arms.
- **3B model**: fails the latency criterion (a) and leaves little RAM headroom; not usable on this laptop.
- **Latency noise (Phase 2)**: for the larger indexes the repeat-to-repeat medians of Flat search differ noticeably (see the "run-to-run range" column of T4a), CPU temperature was not monitored and the power plan was Balanced, so small latency differences between arms at large N must be read against that range, not the pooled median alone. No repeat was discarded.
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
