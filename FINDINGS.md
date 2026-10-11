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
| P3-1 | 3 | Tier A vs Tier B KS p = 0.258; RMSE slope B -0.499, A -0.483 (theory -0.5) | results/phase3/phase3_20261011_221127/validation.json |
| P3-2 | 3 | N=all, M=50: Hit@3 classical 0.680 vs quantum-sim S=64 0.415 | results/phase3/phase3_20261011_221127/retrieval_metrics.csv |
| P3-3 | 3 | Hit@3 shot threshold (M=50) per N: 1000: 2048, 2000: 4096, 5000: 4096, 10000: 8192, all: 16384 | results/phase3/phase3_20261011_221127/shot_thresholds.csv |
| P3-4 | 3 | Tier A end-to-end: 200 circuits, 0.110 s/circuit | results/phase3/phase3_20261011_221127/tierA_e2e_summary.json |
| P3-5 | 3 | T6: full circuit depth 1083, 1076 two-qubit gates | results/phase3/phase3_20261011_221127/t6_resource_counts.json |
| P3-6 | 3 | pytest: 29/29 passed | results/phase3/phase3_20261011_221127/pytest_junit.xml |
| P4-1 | 4 | N=all: Hit@3 Flat 0.680 vs Quantum-sim S=1024 0.626 | results/phase4/phase4_20261011_223158/main_table.csv |
| P4-2 | 4 | Latency exponent b: Flat 1.14, Quantum-sim shortlist M=50 0.88 | results/phase4/phase4_20261011_223158/latency_slopes.csv |
| P4-3 | 4 | Failure analysis N=all S=256: 42 dropped / 6 gained vs classical top-3 | results/phase4/phase4_20261011_223158/failure_summary.json |
| P4-4 | 4 | Pre-registered tests: 20/30 significant after Holm | results/phase4/phase4_20261011_223158/tests.csv |
| P4-5 | 4 | pytest: 37/37 passed | results/phase4/phase4_20261011_223158/pytest_junit.xml |
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

### Phase 3 - Quantum-inspired retrieval arm + validation
<!-- BEGIN:phase3 -->
Run `phase3_20261011_221127` - manifest: `results/phase3/phase3_20261011_221127/run_manifest.json`. Quantum-inspired arm = classical SIMULATION of the SWAP test (Appendix A.1); no speedup is claimed. Tier B latency is emulated-estimator latency, not quantum latency.

**Tier A circuit cost on this laptop (3.3, first step)** (`results/phase3/phase3_20261011_221127/tierA_timing.json`): 19 qubits, S=4096, median per pair 0.247 s with transpile, 0.129 s without; identical estimates in both modes: True. Tier B chunk (20 queries x 20958 candidates, S=1024, incl. ranking): 0.180 s. Decision: Tier A runs WITHOUT transpile (Aer executes set_statevector/h/cswap natively; same seed gives identical estimates) - per-pair cost below 2 s, no pair-count reduction needed.

**Validation (3.3a/b)** (`results/phase3/phase3_20261011_221127/validation.json`, per-pair `results/phase3/phase3_20261011_221127/validation_pairs.csv`): 500 pairs (250 random corpus pairs + 250 query-to-exact-top-50 pairs; cos range -0.160 to 0.821), S = 4096, unclipped estimates. Theory RMSE = 0.0155.

| Tier | Bias | MAE | RMSE | z sd (theory 1) | |z|<=2 | |z|<=3 | KS vs N(0,1) p |
|---|---|---|---|---|---|---|---|
| A (Aer circuit) | +0.00039 | 0.0127 | 0.0161 | 1.046 | 0.944 | 0.996 | 0.897 |
| B (emulator) | -0.00044 | 0.0121 | 0.0157 | 1.014 | 0.950 | 0.998 | 0.063 |

Two-sample KS on standardised errors, Tier A vs Tier B: D = 0.064, p = 0.258.

Repeated estimates (50 pairs x 20 repeats per tier, S=4096; `results/phase3/phase3_20261011_221127/validation_repeated.npz`): mean |difference of pair means| = 0.0038 (expected under equivalence ~0.0049 sd); variance ratio A/B median 0.994 (IQR 0.690-1.287); variance / theory: A 1.006, B 1.018; pooled two-sample KS D = 0.067, p = 0.022.

**F2 error vs shots (3.3c)**: ![F2](results/figures/F2_error_vs_shots.png) (data `results/figures/F2_error_vs_shots.csv`, source `results/phase3/phase3_20261011_221127/f2_error_vs_shots.csv`). Log-log slope of RMSE vs S: Tier B -0.499 (95% CI -0.502 to -0.497); Tier A -0.483 (95% CI -0.507 to -0.460); theory -0.5.

**Negative-cosine audit (3.3d)** (`results/phase3/phase3_20261011_221127/negative_cosine_audit.json`)

| N | cos<0 in exact top-10 | cos<0 in exact top-100 | Queries whose noise-free cos² full-scan top-10 differs from cos top-10 | Min cos in corpus |
|---|---|---|---|---|
| 1000 | 0 | 0 | 4 | -0.275 |
| 2000 | 0 | 0 | 4 | -0.279 |
| 5000 | 0 | 0 | 2 | -0.312 |
| 10000 | 0 | 0 | 0 | -0.318 |
| all | 0 | 0 | 0 | -0.321 |

The last-but-one column measures the sign loss of cos² (D1) in the full-scan protocol: strongly negative items square above weakly positive top-10 items. Shortlist protocols (M <= 100) contain no negative cosines, so they are unaffected.

**Quantum-sim retrieval, two-stage (M=50 shortlist from Flat, Tier B re-score, ties by classical score), 300 queries, 5 seeds** (`results/phase3/phase3_20261011_221127/retrieval_metrics.csv`; rankings `results/phase3/phase3_20261011_221127/rankings/`). Values: mean ± sd across seeds; [95% bootstrap CI over queries, seed-averaged]; diff = quantum - classical Hit@3 (paired bootstrap CI).

| N | Shots S | Hit@3 | Hit@3 CI | MRR@10 | Overlap@10 | RBO | Top-1 changed | Kendall tau (M items) | diff Hit@3 [CI] |
|---|---|---|---|---|---|---|---|---|---|
| 1000 | classical | 0.860 | [0.820, 0.897] | 0.796 | 1 | 1 | 0 | 1 | - |
| 1000 | 64 | 0.606 ± 0.014 | [0.565, 0.647] | 0.535 ± 0.013 | 0.447 | 0.433 | 0.533 | 0.205 | -0.254 [-0.291, -0.219] |
| 1000 | 256 | 0.761 ± 0.011 | [0.721, 0.801] | 0.703 ± 0.013 | 0.565 | 0.586 | 0.306 | 0.318 | -0.099 [-0.129, -0.071] |
| 1000 | 1024 | 0.836 ± 0.014 | [0.797, 0.873] | 0.769 ± 0.008 | 0.707 | 0.737 | 0.157 | 0.468 | -0.024 [-0.046, -0.003] |
| 1000 | 4096 | 0.857 ± 0.012 | [0.819, 0.894] | 0.794 ± 0.008 | 0.831 | 0.852 | 0.081 | 0.624 | -0.003 [-0.013, +0.007] |
| 1000 | 16384 | 0.857 ± 0.002 | [0.817, 0.894] | 0.796 ± 0.005 | 0.910 | 0.920 | 0.046 | 0.760 | -0.003 [-0.013, +0.006] |
| 1000 | inf | 0.860 ± 0.000 | [0.820, 0.897] | 0.796 ± 0.000 | 1.000 | 1.000 | 0.000 | 1.000 | +0.000 [+0.000, +0.000] |
| 2000 | classical | 0.827 | [0.783, 0.870] | 0.766 | 1 | 1 | 0 | 1 | - |
| 2000 | 64 | 0.561 ± 0.026 | [0.519, 0.603] | 0.504 ± 0.028 | 0.450 | 0.432 | 0.550 | 0.216 | -0.266 [-0.304, -0.228] |
| 2000 | 256 | 0.739 ± 0.010 | [0.697, 0.780] | 0.667 ± 0.010 | 0.578 | 0.592 | 0.311 | 0.339 | -0.087 [-0.115, -0.061] |
| 2000 | 1024 | 0.806 ± 0.006 | [0.765, 0.846] | 0.732 ± 0.008 | 0.719 | 0.742 | 0.171 | 0.490 | -0.021 [-0.041, +0.000] |
| 2000 | 4096 | 0.813 ± 0.008 | [0.770, 0.853] | 0.755 ± 0.003 | 0.836 | 0.852 | 0.102 | 0.645 | -0.014 [-0.029, +0.001] |
| 2000 | 16384 | 0.821 ± 0.006 | [0.779, 0.861] | 0.761 ± 0.003 | 0.911 | 0.921 | 0.055 | 0.777 | -0.005 [-0.020, +0.009] |
| 2000 | inf | 0.827 ± 0.000 | [0.783, 0.870] | 0.766 ± 0.000 | 1.000 | 1.000 | 0.000 | 1.000 | +0.000 [+0.000, +0.000] |
| 5000 | classical | 0.777 | [0.730, 0.823] | 0.708 | 1 | 1 | 0 | 1 | - |
| 5000 | 64 | 0.521 ± 0.034 | [0.479, 0.563] | 0.459 ± 0.029 | 0.452 | 0.423 | 0.600 | 0.221 | -0.256 [-0.294, -0.219] |
| 5000 | 256 | 0.685 ± 0.013 | [0.640, 0.729] | 0.618 ± 0.011 | 0.586 | 0.588 | 0.368 | 0.361 | -0.092 [-0.121, -0.064] |
| 5000 | 1024 | 0.737 ± 0.012 | [0.690, 0.781] | 0.682 ± 0.011 | 0.731 | 0.742 | 0.198 | 0.517 | -0.040 [-0.062, -0.019] |
| 5000 | 4096 | 0.759 ± 0.005 | [0.713, 0.804] | 0.696 ± 0.007 | 0.848 | 0.856 | 0.103 | 0.675 | -0.017 [-0.035, +0.000] |
| 5000 | 16384 | 0.775 ± 0.005 | [0.729, 0.820] | 0.710 ± 0.004 | 0.920 | 0.924 | 0.050 | 0.802 | -0.001 [-0.014, +0.011] |
| 5000 | inf | 0.777 ± 0.000 | [0.730, 0.823] | 0.708 ± 0.000 | 1.000 | 1.000 | 0.000 | 1.000 | +0.000 [+0.000, +0.000] |
| 10000 | classical | 0.747 | [0.697, 0.793] | 0.662 | 1 | 1 | 0 | 1 | - |
| 10000 | 64 | 0.467 ± 0.027 | [0.427, 0.507] | 0.401 ± 0.016 | 0.443 | 0.404 | 0.630 | 0.222 | -0.280 [-0.319, -0.242] |
| 10000 | 256 | 0.612 ± 0.015 | [0.565, 0.659] | 0.551 ± 0.007 | 0.574 | 0.563 | 0.425 | 0.364 | -0.135 [-0.167, -0.103] |
| 10000 | 1024 | 0.695 ± 0.014 | [0.648, 0.743] | 0.627 ± 0.016 | 0.731 | 0.733 | 0.231 | 0.535 | -0.051 [-0.073, -0.031] |
| 10000 | 4096 | 0.728 ± 0.009 | [0.681, 0.775] | 0.651 ± 0.003 | 0.846 | 0.850 | 0.127 | 0.690 | -0.019 [-0.033, -0.005] |
| 10000 | 16384 | 0.740 ± 0.005 | [0.691, 0.787] | 0.656 ± 0.005 | 0.911 | 0.917 | 0.074 | 0.816 | -0.007 [-0.016, +0.003] |
| 10000 | inf | 0.747 ± 0.000 | [0.697, 0.793] | 0.662 ± 0.000 | 1.000 | 1.000 | 0.000 | 1.000 | +0.000 [+0.000, +0.000] |
| all | classical | 0.680 | [0.627, 0.733] | 0.590 | 1 | 1 | 0 | 1 | - |
| all | 64 | 0.415 ± 0.022 | [0.375, 0.457] | 0.357 ± 0.005 | 0.436 | 0.385 | 0.686 | 0.221 | -0.265 [-0.304, -0.225] |
| all | 256 | 0.552 ± 0.012 | [0.505, 0.600] | 0.489 ± 0.006 | 0.566 | 0.546 | 0.469 | 0.365 | -0.128 [-0.160, -0.097] |
| all | 1024 | 0.626 ± 0.015 | [0.577, 0.675] | 0.559 ± 0.008 | 0.722 | 0.713 | 0.299 | 0.537 | -0.054 [-0.078, -0.031] |
| all | 4096 | 0.661 ± 0.006 | [0.611, 0.711] | 0.583 ± 0.005 | 0.845 | 0.841 | 0.165 | 0.699 | -0.019 [-0.035, -0.004] |
| all | 16384 | 0.675 ± 0.004 | [0.623, 0.725] | 0.592 ± 0.003 | 0.918 | 0.915 | 0.093 | 0.823 | -0.005 [-0.016, +0.005] |
| all | inf | 0.680 ± 0.000 | [0.627, 0.733] | 0.590 ± 0.000 | 1.000 | 1.000 | 0.000 | 1.000 | +0.000 [+0.000, +0.000] |

**Full-scan ablation (all N candidates estimated, Tier B)**

| N | Shots S | Hit@3 | MRR@10 | Overlap@10 | Top-1 changed | diff Hit@3 [CI] |
|---|---|---|---|---|---|---|
| 1000 | 64 | 0.457 ± 0.016 | 0.405 ± 0.011 | 0.195 | 0.631 | -0.403 [-0.447, -0.361] |
| 1000 | 256 | 0.741 ± 0.010 | 0.681 ± 0.004 | 0.406 | 0.315 | -0.119 [-0.152, -0.089] |
| 1000 | 1024 | 0.836 ± 0.010 | 0.768 ± 0.007 | 0.657 | 0.168 | -0.024 [-0.042, -0.007] |
| 1000 | 4096 | 0.857 ± 0.004 | 0.790 ± 0.007 | 0.824 | 0.094 | -0.003 [-0.016, +0.011] |
| 1000 | 16384 | 0.863 ± 0.005 | 0.796 ± 0.003 | 0.909 | 0.050 | +0.003 [-0.008, +0.013] |
| 1000 | inf | 0.860 ± 0.000 | 0.796 ± 0.000 | 0.998 | 0.000 | +0.000 [+0.000, +0.000] |
| 2000 | 64 | 0.404 ± 0.031 | 0.362 ± 0.029 | 0.173 | 0.682 | -0.423 [-0.466, -0.378] |
| 2000 | 256 | 0.713 ± 0.016 | 0.645 ± 0.014 | 0.420 | 0.350 | -0.113 [-0.147, -0.080] |
| 2000 | 1024 | 0.797 ± 0.011 | 0.733 ± 0.011 | 0.683 | 0.180 | -0.030 [-0.050, -0.010] |
| 2000 | 4096 | 0.822 ± 0.010 | 0.754 ± 0.004 | 0.838 | 0.089 | -0.005 [-0.019, +0.010] |
| 2000 | 16384 | 0.827 ± 0.006 | 0.763 ± 0.005 | 0.913 | 0.057 | +0.001 [-0.009, +0.010] |
| 2000 | inf | 0.827 ± 0.000 | 0.766 ± 0.000 | 0.998 | 0.000 | +0.000 [+0.000, +0.000] |
| 5000 | 64 | 0.355 ± 0.023 | 0.315 ± 0.021 | 0.161 | 0.712 | -0.421 [-0.466, -0.376] |
| 5000 | 256 | 0.663 ± 0.019 | 0.593 ± 0.017 | 0.452 | 0.392 | -0.113 [-0.144, -0.083] |
| 5000 | 1024 | 0.746 ± 0.013 | 0.674 ± 0.005 | 0.706 | 0.186 | -0.031 [-0.050, -0.012] |
| 5000 | 4096 | 0.761 ± 0.005 | 0.695 ± 0.007 | 0.843 | 0.104 | -0.016 [-0.031, -0.002] |
| 5000 | 16384 | 0.770 ± 0.004 | 0.705 ± 0.004 | 0.920 | 0.055 | -0.007 [-0.018, +0.005] |
| 5000 | inf | 0.777 ± 0.000 | 0.708 ± 0.000 | 0.999 | 0.000 | +0.000 [+0.000, +0.000] |
| 10000 | 64 | 0.300 ± 0.021 | 0.262 ± 0.018 | 0.154 | 0.771 | -0.447 [-0.492, -0.401] |
| 10000 | 256 | 0.600 ± 0.011 | 0.537 ± 0.004 | 0.460 | 0.431 | -0.147 [-0.179, -0.115] |
| 10000 | 1024 | 0.704 ± 0.011 | 0.626 ± 0.005 | 0.713 | 0.233 | -0.043 [-0.065, -0.022] |
| 10000 | 4096 | 0.725 ± 0.006 | 0.651 ± 0.005 | 0.845 | 0.122 | -0.022 [-0.040, -0.005] |
| 10000 | 16384 | 0.734 ± 0.006 | 0.657 ± 0.006 | 0.915 | 0.067 | -0.013 [-0.023, -0.004] |
| 10000 | inf | 0.747 ± 0.000 | 0.662 ± 0.000 | 1.000 | 0.000 | +0.000 [+0.000, +0.000] |
| all | 64 | 0.245 ± 0.014 | 0.219 ± 0.024 | 0.151 | 0.794 | -0.435 [-0.481, -0.387] |
| all | 256 | 0.537 ± 0.021 | 0.474 ± 0.021 | 0.467 | 0.493 | -0.143 [-0.177, -0.112] |
| all | 1024 | 0.623 ± 0.005 | 0.557 ± 0.009 | 0.704 | 0.297 | -0.057 [-0.080, -0.034] |
| all | 4096 | 0.659 ± 0.003 | 0.580 ± 0.010 | 0.845 | 0.161 | -0.021 [-0.035, -0.008] |
| all | 16384 | 0.663 ± 0.009 | 0.592 ± 0.006 | 0.920 | 0.080 | -0.017 [-0.029, -0.006] |
| all | inf | 0.680 ± 0.000 | 0.590 ± 0.000 | 1.000 | 0.000 | +0.000 [+0.000, +0.000] |

**Tie-breaking effect at low S (M=50) [P1]**: default breaks equal estimates by the classical score (a design choice that injects exact information into ties); 'random' breaks them uniformly at random.

| N | Shots S | Hit@3 ties=classical | Hit@3 ties=random | Hit@1 ties=classical | Hit@1 ties=random |
|---|---|---|---|---|---|
| 1000 | 64 | 0.606 ± 0.014 | 0.581 ± 0.012 | 0.425 ± 0.018 | 0.399 ± 0.022 |
| 1000 | 128 | 0.690 ± 0.021 | 0.678 ± 0.024 | 0.538 ± 0.026 | 0.527 ± 0.029 |
| 1000 | 256 | 0.761 ± 0.011 | 0.755 ± 0.010 | 0.617 ± 0.021 | 0.608 ± 0.023 |
| 1000 | 1024 | 0.836 ± 0.014 | 0.836 ± 0.015 | 0.687 ± 0.009 | 0.685 ± 0.007 |
| 2000 | 64 | 0.561 ± 0.026 | 0.531 ± 0.039 | 0.400 ± 0.034 | 0.375 ± 0.024 |
| 2000 | 128 | 0.676 ± 0.025 | 0.662 ± 0.022 | 0.500 ± 0.011 | 0.485 ± 0.015 |
| 2000 | 256 | 0.739 ± 0.010 | 0.732 ± 0.012 | 0.573 ± 0.012 | 0.563 ± 0.007 |
| 2000 | 1024 | 0.806 ± 0.006 | 0.805 ± 0.009 | 0.641 ± 0.013 | 0.641 ± 0.012 |
| 5000 | 64 | 0.521 ± 0.034 | 0.489 ± 0.039 | 0.357 ± 0.035 | 0.331 ± 0.037 |
| 5000 | 128 | 0.607 ± 0.016 | 0.593 ± 0.013 | 0.444 ± 0.021 | 0.429 ± 0.016 |
| 5000 | 256 | 0.685 ± 0.013 | 0.679 ± 0.018 | 0.522 ± 0.012 | 0.513 ± 0.013 |
| 5000 | 1024 | 0.737 ± 0.012 | 0.737 ± 0.012 | 0.601 ± 0.021 | 0.600 ± 0.020 |
| 10000 | 64 | 0.467 ± 0.027 | 0.427 ± 0.018 | 0.295 ± 0.022 | 0.269 ± 0.022 |
| 10000 | 128 | 0.567 ± 0.013 | 0.553 ± 0.010 | 0.384 ± 0.026 | 0.373 ± 0.026 |
| 10000 | 256 | 0.612 ± 0.015 | 0.601 ± 0.013 | 0.458 ± 0.005 | 0.447 ± 0.009 |
| 10000 | 1024 | 0.695 ± 0.014 | 0.694 ± 0.014 | 0.533 ± 0.024 | 0.531 ± 0.024 |
| all | 64 | 0.415 ± 0.022 | 0.375 ± 0.014 | 0.254 ± 0.009 | 0.227 ± 0.010 |
| all | 128 | 0.476 ± 0.009 | 0.461 ± 0.013 | 0.322 ± 0.012 | 0.314 ± 0.013 |
| all | 256 | 0.552 ± 0.012 | 0.545 ± 0.011 | 0.392 ± 0.008 | 0.384 ± 0.005 |
| all | 1024 | 0.626 ± 0.015 | 0.625 ± 0.019 | 0.461 ± 0.007 | 0.460 ± 0.011 |

**Shot threshold (exit gate)** (`results/phase3/phase3_20261011_221127/shot_thresholds.csv`): smallest S such that for that S and every larger S in the grid the paired 95% CI of (quantum - classical) contains 0 ('indistinguishable'), and the plainer rule 'quantum mean inside the classical 95% CI'.

| N | M | Ties | Hit@3: indistinguishable | Hit@3: within classical CI | MRR@10: indistinguishable | MRR@10: within CI | Hit@1: indistinguishable |
|---|---|---|---|---|---|---|---|
| 1000 | 20 | classical | 2048 | 512 | 4096 | 1024 | 2048 |
| 1000 | 50 | classical | 2048 | 1024 | 4096 | 1024 | 2048 |
| 1000 | 50 | random | 2048 | 1024 | 4096 | 1024 | 2048 |
| 1000 | 100 | classical | 2048 | 512 | 4096 | 1024 | 2048 |
| 1000 | full | classical | 2048 | 1024 | 2048 | 1024 | 2048 |
| 2000 | 20 | classical | 2048 | 1024 | 8192 | 1024 | 8192 |
| 2000 | 50 | classical | 4096 | 1024 | 8192 | 1024 | 8192 |
| 2000 | 50 | random | 4096 | 1024 | 8192 | 1024 | 8192 |
| 2000 | 100 | classical | 2048 | 1024 | 8192 | 1024 | 4096 |
| 2000 | full | classical | 4096 | 1024 | 8192 | 1024 | 16384 |
| 5000 | 20 | classical | 8192 | 1024 | 8192 | 1024 | 4096 |
| 5000 | 50 | classical | 4096 | 1024 | 16384 | 1024 | 2048 |
| 5000 | 50 | random | 4096 | 1024 | 16384 | 1024 | 2048 |
| 5000 | 100 | classical | 8192 | 1024 | 4096 | 1024 | 4096 |
| 5000 | full | classical | 8192 | 1024 | 8192 | 1024 | 4096 |
| 10000 | 20 | classical | 8192 | 2048 | 8192 | 1024 | 2048 |
| 10000 | 50 | classical | 8192 | 2048 | 8192 | 1024 | 2048 |
| 10000 | 50 | random | 8192 | 2048 | 8192 | 1024 | 2048 |
| 10000 | 100 | classical | 16384 | 2048 | 8192 | 1024 | 4096 |
| 10000 | full | classical | absent | 1024 | 8192 | 1024 | 4096 |
| all | 20 | classical | 16384 | 1024 | 2048 | 512 | 2048 |
| all | 50 | classical | 16384 | 2048 | 4096 | 1024 | 4096 |
| all | 50 | random | 16384 | 2048 | 4096 | 1024 | 4096 |
| all | 100 | classical | 16384 | 1024 | 4096 | 1024 | 2048 |
| all | full | classical | absent | 2048 | 4096 | 1024 | 2048 |

Tier B run cost (H8; `results/phase3/phase3_20261011_221127/tierB_run_timing.csv`): median seconds per (N, M, S, seed) run over all 300 queries, incl. ranking and metrics - N=1000 M=50: 0.092 s, N=1000 M=full: 0.051 s, N=2000 M=50: 0.086 s, N=2000 M=full: 0.086 s, N=5000 M=50: 0.084 s, N=5000 M=full: 0.232 s, N=10000 M=50: 0.086 s, N=10000 M=full: 0.553 s, N=all M=50: 0.084 s, N=all M=full: 1.405 s. (Proper latency per query is Phase 4.)

**Tier A end-to-end subset (3.5) [P1]** (`results/phase3/phase3_20261011_221127/tierA_e2e_summary.json`, `results/phase3/phase3_20261011_221127/tierA_e2e.csv`): 20 queries x M=10 (exact top-10 at N=all) x S=1024: 200 real Aer circuits in 22.0 s (0.110 s per circuit; classical simulation cost grows as 2^qubits).

| Ranking | Hit@1 | Hit@3 | Top-1 changed vs classical | Overlap@3 vs classical |
|---|---|---|---|---|
| A | 0.500 | 0.700 | 0.250 | 0.667 |
| B | 0.550 | 0.600 | 0.250 | 0.683 |
| classical | 0.550 | 0.700 | 0.000 | 1.000 |

With 20 queries these rates are illustrative only (no CI claimed).

**T6 resource counts (MODELLED, not executed)** (`results/phase3/phase3_20261011_221127/t6_resource_counts.json`; basis ['cx', 'u'], optimisation level 1, transpile took 0.7 s)

| Circuit | Qubits | Depth | 2-qubit gates | 1-qubit gates |
|---|---|---|---|---|
| swap_test_core | 19 | 78 | 72 | 74 |
| full_with_state_prep | 19 | 1083 | 1076 | 1096 |

Statevector memory for the 19-qubit simulation: 8388608 bytes (complex128). State preparation dominates the gate count; without QRAM-like loading there is no asymptotic advantage (Appendix A.3).

**Not done in Phase 3**: 3.6 Zardini-style estimator [P1] deferred until all P0 phases are complete (plan Section 0 priority rule); see Deviations.

**pytest** (whole suite at Phase 3 exit): 29 tests, 0 failures, 0 errors, 0 skipped (`results/phase3/phase3_20261011_221127/pytest_junit.xml`).

**Manuscript hook**: Section 6 (estimator validation, F2, shot budget), Table T6; Section 2 (SWAP test).
<!-- END:phase3 -->

### Phase 4 - Retrieval-only experiments
<!-- BEGIN:phase4 -->
Run `phase4_20261011_223158` - manifest: `results/phase4/phase4_20261011_223158/run_manifest.json`. Retrieval-only; inputs: Phase 1 ground truth, Phase 2 baselines, Phase 3 rankings (`results/phase3/phase3_20261011_221127`). Quantum-sim = SWAP-test simulation (M=50 shortlist unless stated). Latency of that arm is EMULATED-estimator latency, never quantum latency.

**T3 main retrieval comparison (4.1)** (`results/phase4/phase4_20261011_223158/main_table.csv`). Values with 95% bootstrap CI over the 300 queries (quantum: per-query mean over 5 seeds). Overlap@10 and RBO are versus the exact top-10; Flat is the reference (1 by construction).

| N | Arm | Hit@1 | Hit@3 | Hit@5 | Hit@10 | MRR@10 | nDCG@10 | Overlap@10 | RBO |
|---|---|---|---|---|---|---|---|---|---|
| 1000 | Flat | 0.720 [0.670, 0.770] | 0.860 [0.820, 0.897] | 0.900 [0.863, 0.933] | 0.940 [0.913, 0.967] | 0.796 [0.757, 0.834] | 0.831 [0.797, 0.864] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] |
| 1000 | IVF (nprobe 16) | 0.720 [0.670, 0.770] | 0.860 [0.820, 0.897] | 0.903 [0.867, 0.937] | 0.943 [0.917, 0.967] | 0.797 [0.758, 0.834] | 0.833 [0.799, 0.865] | 0.986 [0.980, 0.991] | 0.989 [0.984, 0.993] |
| 1000 | Quantum-sim S=256 | 0.617 [0.571, 0.662] | 0.761 [0.721, 0.801] | 0.811 [0.775, 0.847] | 0.877 [0.845, 0.906] | 0.703 [0.664, 0.741] | 0.745 [0.709, 0.780] | 0.565 [0.550, 0.581] | 0.586 [0.570, 0.603] |
| 1000 | Quantum-sim S=1024 | 0.687 [0.639, 0.733] | 0.836 [0.797, 0.873] | 0.879 [0.845, 0.911] | 0.913 [0.885, 0.941] | 0.769 [0.730, 0.806] | 0.804 [0.769, 0.837] | 0.707 [0.692, 0.722] | 0.737 [0.723, 0.751] |
| 1000 | Quantum-sim S=4096 | 0.717 [0.667, 0.765] | 0.857 [0.819, 0.894] | 0.892 [0.859, 0.923] | 0.935 [0.908, 0.960] | 0.794 [0.756, 0.831] | 0.829 [0.795, 0.861] | 0.831 [0.820, 0.842] | 0.852 [0.841, 0.862] |
| 1000 | Quantum-sim S=16384 | 0.717 [0.667, 0.767] | 0.857 [0.817, 0.894] | 0.901 [0.867, 0.932] | 0.943 [0.916, 0.967] | 0.796 [0.758, 0.833] | 0.832 [0.798, 0.864] | 0.910 [0.903, 0.918] | 0.920 [0.913, 0.926] |
| 2000 | Flat | 0.690 [0.637, 0.740] | 0.827 [0.783, 0.870] | 0.873 [0.833, 0.910] | 0.917 [0.883, 0.947] | 0.766 [0.724, 0.806] | 0.802 [0.765, 0.838] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] |
| 2000 | IVF (nprobe 16) | 0.687 [0.633, 0.740] | 0.823 [0.780, 0.867] | 0.870 [0.830, 0.907] | 0.913 [0.880, 0.943] | 0.762 [0.721, 0.804] | 0.799 [0.761, 0.835] | 0.973 [0.964, 0.981] | 0.979 [0.971, 0.986] |
| 2000 | Quantum-sim S=256 | 0.573 [0.527, 0.620] | 0.739 [0.697, 0.780] | 0.788 [0.749, 0.826] | 0.845 [0.811, 0.878] | 0.667 [0.626, 0.707] | 0.710 [0.672, 0.748] | 0.578 [0.564, 0.593] | 0.592 [0.576, 0.607] |
| 2000 | Quantum-sim S=1024 | 0.641 [0.593, 0.689] | 0.806 [0.765, 0.846] | 0.847 [0.810, 0.883] | 0.893 [0.861, 0.924] | 0.732 [0.692, 0.771] | 0.771 [0.734, 0.807] | 0.719 [0.704, 0.734] | 0.742 [0.727, 0.756] |
| 2000 | Quantum-sim S=4096 | 0.673 [0.623, 0.723] | 0.813 [0.770, 0.853] | 0.863 [0.825, 0.898] | 0.909 [0.878, 0.939] | 0.755 [0.714, 0.794] | 0.792 [0.756, 0.827] | 0.836 [0.825, 0.847] | 0.852 [0.842, 0.861] |
| 2000 | Quantum-sim S=16384 | 0.680 [0.629, 0.731] | 0.821 [0.779, 0.861] | 0.873 [0.836, 0.909] | 0.919 [0.887, 0.947] | 0.761 [0.719, 0.801] | 0.799 [0.762, 0.834] | 0.911 [0.904, 0.919] | 0.921 [0.915, 0.927] |
| 5000 | Flat | 0.623 [0.570, 0.680] | 0.777 [0.730, 0.823] | 0.817 [0.773, 0.860] | 0.880 [0.843, 0.917] | 0.708 [0.664, 0.752] | 0.749 [0.709, 0.790] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] |
| 5000 | IVF (nprobe 16) | 0.620 [0.567, 0.677] | 0.770 [0.720, 0.817] | 0.810 [0.763, 0.853] | 0.867 [0.827, 0.903] | 0.703 [0.658, 0.748] | 0.742 [0.701, 0.784] | 0.958 [0.948, 0.968] | 0.967 [0.959, 0.975] |
| 5000 | Quantum-sim S=256 | 0.522 [0.476, 0.570] | 0.685 [0.640, 0.729] | 0.747 [0.704, 0.789] | 0.816 [0.777, 0.852] | 0.618 [0.576, 0.660] | 0.665 [0.625, 0.705] | 0.586 [0.572, 0.600] | 0.588 [0.572, 0.603] |
| 5000 | Quantum-sim S=1024 | 0.601 [0.551, 0.652] | 0.737 [0.690, 0.781] | 0.785 [0.741, 0.827] | 0.849 [0.811, 0.884] | 0.682 [0.638, 0.726] | 0.722 [0.681, 0.762] | 0.731 [0.717, 0.745] | 0.742 [0.729, 0.756] |
| 5000 | Quantum-sim S=4096 | 0.612 [0.559, 0.665] | 0.759 [0.713, 0.804] | 0.803 [0.759, 0.845] | 0.869 [0.833, 0.905] | 0.696 [0.652, 0.740] | 0.738 [0.697, 0.778] | 0.848 [0.838, 0.858] | 0.856 [0.847, 0.865] |
| 5000 | Quantum-sim S=16384 | 0.627 [0.575, 0.681] | 0.775 [0.729, 0.820] | 0.810 [0.765, 0.853] | 0.881 [0.844, 0.915] | 0.710 [0.666, 0.754] | 0.751 [0.711, 0.791] | 0.920 [0.913, 0.926] | 0.924 [0.918, 0.929] |
| 10000 | Flat | 0.573 [0.517, 0.630] | 0.747 [0.697, 0.793] | 0.783 [0.737, 0.830] | 0.833 [0.790, 0.873] | 0.662 [0.616, 0.709] | 0.703 [0.660, 0.746] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] |
| 10000 | IVF (nprobe 16) | 0.560 [0.503, 0.617] | 0.727 [0.677, 0.777] | 0.760 [0.713, 0.810] | 0.807 [0.760, 0.850] | 0.645 [0.597, 0.694] | 0.684 [0.639, 0.730] | 0.965 [0.955, 0.974] | 0.971 [0.962, 0.980] |
| 10000 | Quantum-sim S=256 | 0.458 [0.412, 0.505] | 0.612 [0.565, 0.659] | 0.677 [0.631, 0.723] | 0.757 [0.713, 0.798] | 0.551 [0.507, 0.595] | 0.600 [0.558, 0.642] | 0.574 [0.560, 0.589] | 0.563 [0.547, 0.580] |
| 10000 | Quantum-sim S=1024 | 0.533 [0.483, 0.585] | 0.695 [0.648, 0.743] | 0.753 [0.709, 0.797] | 0.817 [0.776, 0.856] | 0.627 [0.583, 0.671] | 0.673 [0.631, 0.715] | 0.731 [0.717, 0.744] | 0.733 [0.719, 0.747] |
| 10000 | Quantum-sim S=4096 | 0.564 [0.512, 0.617] | 0.728 [0.681, 0.775] | 0.771 [0.725, 0.815] | 0.815 [0.773, 0.855] | 0.651 [0.606, 0.698] | 0.691 [0.649, 0.734] | 0.846 [0.836, 0.856] | 0.850 [0.841, 0.860] |
| 10000 | Quantum-sim S=16384 | 0.565 [0.511, 0.620] | 0.740 [0.691, 0.787] | 0.777 [0.730, 0.822] | 0.824 [0.782, 0.865] | 0.656 [0.610, 0.702] | 0.697 [0.654, 0.740] | 0.911 [0.904, 0.918] | 0.917 [0.911, 0.923] |
| all | Flat | 0.490 [0.433, 0.547] | 0.680 [0.627, 0.733] | 0.733 [0.683, 0.783] | 0.783 [0.737, 0.830] | 0.590 [0.542, 0.638] | 0.637 [0.592, 0.682] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] |
| all | IVF (nprobe 16) | 0.473 [0.417, 0.530] | 0.660 [0.607, 0.713] | 0.713 [0.663, 0.763] | 0.760 [0.710, 0.807] | 0.572 [0.523, 0.621] | 0.618 [0.572, 0.665] | 0.953 [0.942, 0.964] | 0.958 [0.946, 0.969] |
| all | Quantum-sim S=256 | 0.392 [0.347, 0.439] | 0.552 [0.505, 0.600] | 0.619 [0.573, 0.667] | 0.703 [0.659, 0.746] | 0.489 [0.446, 0.534] | 0.540 [0.498, 0.583] | 0.566 [0.553, 0.581] | 0.546 [0.530, 0.562] |
| all | Quantum-sim S=1024 | 0.461 [0.411, 0.513] | 0.626 [0.577, 0.675] | 0.693 [0.647, 0.740] | 0.761 [0.715, 0.804] | 0.559 [0.513, 0.605] | 0.608 [0.563, 0.652] | 0.722 [0.709, 0.736] | 0.713 [0.699, 0.728] |
| all | Quantum-sim S=4096 | 0.483 [0.430, 0.537] | 0.661 [0.611, 0.711] | 0.728 [0.680, 0.775] | 0.778 [0.732, 0.823] | 0.583 [0.536, 0.631] | 0.631 [0.586, 0.675] | 0.845 [0.836, 0.855] | 0.841 [0.831, 0.851] |
| all | Quantum-sim S=16384 | 0.493 [0.439, 0.549] | 0.675 [0.623, 0.725] | 0.725 [0.676, 0.774] | 0.781 [0.734, 0.827] | 0.592 [0.544, 0.640] | 0.638 [0.592, 0.683] | 0.918 [0.912, 0.924] | 0.915 [0.909, 0.921] |

**F4 quality vs N**: ![F4](results/figures/F4_quality_vs_N.png) (data `results/figures/F4_quality_vs_N.csv`).
**F3 quality vs shots**: ![F3](results/figures/F3_quality_vs_shots.png) (data `results/figures/F3_quality_vs_shots.csv`).
**F6 agreement with classical ranking vs shots**: ![F6](results/figures/F6_overlap_rbo_vs_shots.png) (data `results/figures/F6_overlap_rbo_vs_shots.csv`).

**T4b In-process retrieval latency per query, embedding excluded (4.2)** (`results/phase4/phase4_20261011_223158/latency_summary.csv`; raw `results/phase4/phase4_20261011_223158/latency_raw.csv`). Protocol: batch-1, 10 warm-up discarded, 100 timed queries, 5 repeats, all conditions shuffled per repeat, 1 thread.

| N | Arm | Median ms | p95 ms | Range of repeat medians (ms) |
|---|---|---|---|---|
| 1000 | Flat k=10 | 0.109 | 0.212 | 0.093-0.204 |
| 1000 | IVF nprobe 16, k=10 | 0.050 | 0.098 | 0.042-0.090 |
| 1000 | Quantum-sim M=50 S=1024 | 0.177 | 0.337 | 0.126-0.255 |
| 1000 | Quantum-sim full scan S=1024 | 0.185 | 0.405 | 0.132-0.302 |
| 2000 | Flat k=10 | 0.169 | 0.323 | 0.125-0.201 |
| 2000 | IVF nprobe 16, k=10 | 0.061 | 0.141 | 0.045-0.128 |
| 2000 | Quantum-sim M=50 S=1024 | 0.333 | 0.797 | 0.162-0.723 |
| 2000 | Quantum-sim full scan S=1024 | 0.450 | 1.019 | 0.253-0.934 |
| 5000 | Flat k=10 | 0.578 | 1.140 | 0.371-0.893 |
| 5000 | IVF nprobe 16, k=10 | 0.176 | 0.344 | 0.120-0.289 |
| 5000 | Quantum-sim M=50 S=1024 | 0.930 | 1.432 | 0.493-1.162 |
| 5000 | Quantum-sim full scan S=1024 | 0.855 | 1.614 | 0.728-1.065 |
| 10000 | Flat k=10 | 1.405 | 3.264 | 1.029-3.039 |
| 10000 | IVF nprobe 16, k=10 | 0.200 | 0.409 | 0.168-0.302 |
| 10000 | Quantum-sim M=50 S=1024 | 1.483 | 2.645 | 1.164-2.479 |
| 10000 | Quantum-sim full scan S=1024 | 2.195 | 3.828 | 1.825-3.173 |
| all | Flat k=10 | 2.918 | 6.710 | 2.121-5.841 |
| all | IVF nprobe 16, k=10 | 0.417 | 0.870 | 0.303-0.705 |
| all | Quantum-sim M=50 S=1024 | 2.903 | 5.687 | 2.367-5.217 |
| all | Quantum-sim full scan S=1024 | 5.175 | 8.361 | 3.810-7.421 |

**Latency scaling: log-log exponent b in latency ~ N^b** (`results/phase4/phase4_20261011_223158/latency_slopes.csv`; point estimate on medians, 95% CI by bootstrapping the 5 repeat medians per N)

| Series | b [95% CI] | R^2 (point fit) |
|---|---|---|
| Flat (exact), k=10 | 1.144 [0.970, 1.320] | 0.988 |
| IVF best nprobe, k=10 | 0.672 [0.510, 0.900] | 0.949 |
| Quantum-sim shortlist M=20, S=1024 | 0.978 [0.833, 1.190] | 0.994 |
| Quantum-sim shortlist M=50, S=1024 | 0.879 [0.763, 1.123] | 0.967 |
| Quantum-sim shortlist M=100, S=1024 | 0.962 [0.834, 1.040] | 0.997 |
| Quantum-sim full scan, S=256 | 1.068 [0.928, 1.173] | 0.989 |
| Quantum-sim full scan, S=1024 | 1.102 [0.896, 1.214] | 0.984 |
| Quantum-sim full scan, S=16384 | 1.037 [0.947, 1.162] | 0.990 |

**Stage breakdown, Quantum-sim M=50 S=1024 (median ms)**: Flat shortlist search, binomial estimate, ranking.

| N | Shortlist search | Estimate (binomial) | Rank | Total |
|---|---|---|---|---|
| 1000 | 0.1132 | 0.0537 | 0.0064 | 0.177 |
| 2000 | 0.2547 | 0.0686 | 0.0081 | 0.333 |
| 5000 | 0.7749 | 0.1197 | 0.0117 | 0.930 |
| 10000 | 1.3371 | 0.1136 | 0.0110 | 1.483 |
| all | 2.7560 | 0.1200 | 0.0110 | 2.903 |

**F5 latency vs N**: ![F5](results/figures/F5_latency_vs_N.png) (data `results/figures/F5_latency_vs_N.csv`).

**Shot-budget ablation (4.3): latency vs S at N=all** (median ms; emulator cost grows with candidates, hardly with S). Quality vs S is in the Phase 3 table and F3.

| S | M=20 | M=50 | M=100 | full scan |
|---|---|---|---|---|
| 64 | 3.223 | 3.148 | 3.320 | - |
| 256 | 2.413 | 2.905 | 3.576 | 5.704 |
| 1024 | 2.696 | 2.903 | 2.626 | 5.175 |
| 4096 | 2.625 | 3.293 | 3.171 | - |
| 16384 | 2.995 | 3.746 | 2.900 | 4.177 |

**MODELLED quantum cost per query at N=all (not measured; Appendix A.3)** (`results/phase4/phase4_20261011_223158/modelled_quantum_cost.csv`): circuits = M (or N), shots = circuits x S; 2-qubit-gate executions use the T6 gate counts of the full circuit with generic state preparation and of the SWAP-test core alone. This is NOT wall-clock quantum speed.

| M | S | Circuits/query | Shots/query | 2q-gate executions (full circuit) | 2q-gate executions (SWAP core only) |
|---|---|---|---|---|---|
| 50 | 256 | 50 | 12800 | 13772800 | 921600 |
| 50 | 1024 | 50 | 51200 | 55091200 | 3686400 |
| 50 | 4096 | 50 | 204800 | 220364800 | 14745600 |
| 50 | 16384 | 50 | 819200 | 881459200 | 58982400 |
| full | 256 | 20958 | 5365248 | 5773006848 | 386297856 |
| full | 1024 | 20958 | 21460992 | 23092027392 | 1545191424 |
| full | 4096 | 20958 | 85843968 | 92368109568 | 6180765696 |
| full | 16384 | 20958 | 343375872 | 369472438272 | 24723062784 |

**Memory vs N (4.2)** (`results/phase4/phase4_20261011_223158/memory_vs_N.csv`; index bytes from Phase 2 `build.csv`): the shortlist arm needs the Flat index only; Tier A circuits would additionally need 512-d padded vectors; full scan holds the 384-d matrix.

| N | Flat index bytes | IVF index bytes | Padded 512-d bytes (Tier A) | Full-scan matrix bytes |
|---|---|---|---|---|
| 1000 | 1536045 | 1593547 | 2048000 | 1536000 |
| 2000 | 3072045 | 3157619 | 4096000 | 3072000 |
| 5000 | 7680045 | 7829763 | 10240000 | 7680000 |
| 10000 | 15360045 | 15594539 | 20480000 | 15360000 |
| all | 32191533 | 32583171 | 42921984 | 32191488 |

Log-log slope of index bytes vs N: Flat 1.000, IVF 0.992.

**Shortlist ablation (4.4)**: M in {20, 50, 100, N (full scan)}; cells are Hit@3 / MRR@10 / Overlap@10 (mean of 5 seeds; Phase 3 `results/phase3/phase3_20261011_221127/retrieval_metrics.csv`); last column: median latency ms at S=1024 (this phase).

| N | M | S=256 | S=1024 | S=4096 | Latency ms (S=1024) |
|---|---|---|---|---|---|
| 5000 | 20 | 0.687 / 0.622 / 0.699 | 0.743 / 0.678 / 0.782 | 0.759 / 0.698 / 0.861 | 0.702 |
| 5000 | 50 | 0.685 / 0.618 / 0.586 | 0.737 / 0.682 / 0.731 | 0.759 / 0.696 / 0.848 | 0.930 |
| 5000 | 100 | 0.675 / 0.610 / 0.537 | 0.738 / 0.671 / 0.720 | 0.760 / 0.700 / 0.851 | 0.754 |
| 5000 | full | 0.663 / 0.593 / 0.452 | 0.746 / 0.674 / 0.706 | 0.761 / 0.695 / 0.843 | 0.855 |
| all | 20 | 0.561 / 0.497 / 0.686 | 0.631 / 0.557 / 0.773 | 0.661 / 0.585 / 0.853 | 2.696 |
| all | 50 | 0.552 / 0.489 / 0.566 | 0.626 / 0.559 / 0.722 | 0.661 / 0.583 / 0.845 | 2.903 |
| all | 100 | 0.522 / 0.468 / 0.533 | 0.628 / 0.555 / 0.713 | 0.656 / 0.585 / 0.846 | 2.626 |
| all | full | 0.537 / 0.474 / 0.467 | 0.623 / 0.557 / 0.704 | 0.659 / 0.580 / 0.845 | 5.175 |

**Failure analysis (4.5)** (`results/phase4/phase4_20261011_223158/failure_summary.json`, 20 examples with scores in `results/phase4/phase4_20261011_223158/failure_examples.csv`): N=all, M=50, S=256, seed 0, k=3. Replay of the Phase 3 random stream reproduces the saved ranking exactly: True. Gold in classical top-3: 204/300; in quantum top-3: 168/300. Dropped by quantum (gold in classical top-3 but not quantum): 42; gained: 6. Median classical gold rank among dropped: 2.0; mean estimated cos^2 of the dropped gold: 0.252.

First 5 of the 20 dumped examples (full text in the CSV):

| query_i | gold classical rank | gold cos | gold k/S | gold c2_hat (true) | gold quantum rank in shortlist | quantum top-3 c2_hat |
|---|---|---|---|---|---|---|
| 19 | 1 | 0.514 | 150/256 | 0.172 (0.264) | 11 | 0.297 | 0.281 | 0.227 |
| 26 | 3 | 0.422 | 150/256 | 0.172 (0.178) | 9 | 0.258 | 0.227 | 0.227 |
| 28 | 2 | 0.617 | 168/256 | 0.312 (0.380) | 5 | 0.359 | 0.352 | 0.336 |
| 40 | 3 | 0.533 | 162/256 | 0.266 (0.284) | 11 | 0.359 | 0.336 | 0.328 |
| 64 | 1 | 0.459 | 160/256 | 0.250 (0.211) | 5 | 0.281 | 0.266 | 0.258 |

**T5a Pre-registered tests (4.6, A.6), classical vs quantum-sim M=50** (`results/phase4/phase4_20261011_223158/tests.csv`). Primary test: paired bootstrap (10k) of the per-query difference between the seed-averaged quantum outcome and the classical outcome; Holm correction within each family (T-a Hit@3, T-b MRR@10; 15 tests each). Secondary, uncorrected: Wilcoxon signed-rank on the same differences and exact McNemar on seed 0 (Hit@3 only). The bootstrap p floor is about 2e-4. 20 of 30 primary tests are significant after Holm.

| Fam. | Metric | N | S | Classical | Quantum | Diff [95% CI] | p (boot) | p (Holm) | Sig. | p Wilcoxon | p McNemar s0 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| T-a | Hit@3 | 1000 | 256 | 0.860 | 0.761 | -0.099 [-0.129, -0.071] | 0.0002 | 0.0030 | yes | 0.0000 | 0.0000 |
| T-b | MRR@10 | 1000 | 256 | 0.796 | 0.703 | -0.093 [-0.114, -0.073] | 0.0002 | 0.0030 | yes | 0.0000 | - |
| T-a | Hit@3 | 1000 | 1024 | 0.860 | 0.836 | -0.024 [-0.046, -0.003] | 0.0254 | 0.1270 | no | 0.0704 | 0.1435 |
| T-b | MRR@10 | 1000 | 1024 | 0.796 | 0.769 | -0.028 [-0.041, -0.015] | 0.0002 | 0.0030 | yes | 0.0000 | - |
| T-a | Hit@3 | 1000 | 4096 | 0.860 | 0.857 | -0.003 [-0.013, +0.007] | 0.6557 | 0.6557 | no | 0.9849 | 0.0312 |
| T-b | MRR@10 | 1000 | 4096 | 0.796 | 0.794 | -0.002 [-0.010, +0.006] | 0.6055 | 0.6055 | no | 0.7145 | - |
| T-a | Hit@3 | 2000 | 256 | 0.827 | 0.739 | -0.087 [-0.115, -0.061] | 0.0002 | 0.0030 | yes | 0.0000 | 0.0000 |
| T-b | MRR@10 | 2000 | 256 | 0.766 | 0.667 | -0.099 [-0.119, -0.078] | 0.0002 | 0.0030 | yes | 0.0000 | - |
| T-a | Hit@3 | 2000 | 1024 | 0.827 | 0.806 | -0.021 [-0.041, +0.000] | 0.0516 | 0.2064 | no | 0.1270 | 0.1435 |
| T-b | MRR@10 | 2000 | 1024 | 0.766 | 0.732 | -0.034 [-0.046, -0.022] | 0.0002 | 0.0030 | yes | 0.0000 | - |
| T-a | Hit@3 | 2000 | 4096 | 0.827 | 0.813 | -0.014 [-0.029, +0.001] | 0.0620 | 0.2064 | no | 0.0991 | 0.0078 |
| T-b | MRR@10 | 2000 | 4096 | 0.766 | 0.755 | -0.011 [-0.020, -0.002] | 0.0122 | 0.0488 | yes | 0.0098 | - |
| T-a | Hit@3 | 5000 | 256 | 0.777 | 0.685 | -0.092 [-0.121, -0.064] | 0.0002 | 0.0030 | yes | 0.0000 | 0.0002 |
| T-b | MRR@10 | 5000 | 256 | 0.708 | 0.618 | -0.090 [-0.110, -0.071] | 0.0002 | 0.0030 | yes | 0.0000 | - |
| T-a | Hit@3 | 5000 | 1024 | 0.777 | 0.737 | -0.040 [-0.062, -0.019] | 0.0002 | 0.0030 | yes | 0.0041 | 0.0963 |
| T-b | MRR@10 | 5000 | 1024 | 0.708 | 0.682 | -0.026 [-0.038, -0.015] | 0.0002 | 0.0030 | yes | 0.0000 | - |
| T-a | Hit@3 | 5000 | 4096 | 0.777 | 0.759 | -0.017 [-0.035, +0.000] | 0.0542 | 0.2064 | no | 0.0858 | 0.2668 |
| T-b | MRR@10 | 5000 | 4096 | 0.708 | 0.696 | -0.012 [-0.020, -0.003] | 0.0080 | 0.0400 | yes | 0.0076 | - |
| T-a | Hit@3 | 10000 | 256 | 0.747 | 0.612 | -0.135 [-0.167, -0.103] | 0.0002 | 0.0030 | yes | 0.0000 | 0.0000 |
| T-b | MRR@10 | 10000 | 256 | 0.662 | 0.551 | -0.110 [-0.133, -0.089] | 0.0002 | 0.0030 | yes | 0.0000 | - |
| T-a | Hit@3 | 10000 | 1024 | 0.747 | 0.695 | -0.051 [-0.073, -0.031] | 0.0002 | 0.0030 | yes | 0.0000 | 0.0072 |
| T-b | MRR@10 | 10000 | 1024 | 0.662 | 0.627 | -0.035 [-0.048, -0.023] | 0.0002 | 0.0030 | yes | 0.0000 | - |
| T-a | Hit@3 | 10000 | 4096 | 0.747 | 0.728 | -0.019 [-0.033, -0.005] | 0.0100 | 0.0700 | no | 0.0216 | 0.0654 |
| T-b | MRR@10 | 10000 | 4096 | 0.662 | 0.651 | -0.010 [-0.020, -0.001] | 0.0258 | 0.0774 | no | 0.0209 | - |
| T-a | Hit@3 | all | 256 | 0.680 | 0.552 | -0.128 [-0.160, -0.097] | 0.0002 | 0.0030 | yes | 0.0000 | 0.0000 |
| T-b | MRR@10 | all | 256 | 0.590 | 0.489 | -0.101 [-0.125, -0.078] | 0.0002 | 0.0030 | yes | 0.0000 | - |
| T-a | Hit@3 | all | 1024 | 0.680 | 0.626 | -0.054 [-0.078, -0.031] | 0.0002 | 0.0030 | yes | 0.0002 | 0.0002 |
| T-b | MRR@10 | all | 1024 | 0.590 | 0.559 | -0.031 [-0.047, -0.017] | 0.0002 | 0.0030 | yes | 0.0001 | - |
| T-a | Hit@3 | all | 4096 | 0.680 | 0.661 | -0.019 [-0.035, -0.004] | 0.0118 | 0.0708 | no | 0.0767 | 0.0923 |
| T-b | MRR@10 | all | 4096 | 0.590 | 0.583 | -0.007 [-0.016, +0.003] | 0.1796 | 0.3592 | no | 0.2245 | - |

T-c (hallucination rate, McNemar at N=all) belongs to Phase 5.

**Measurement hygiene (H7)** (`results/phase4/phase4_20261011_223158/hygiene.json`): plugged in = True, battery 100%, power scheme `Power Scheme GUID: 381b4222-f694-41f0-9685-ff5bb260df2e  (Balanced)`, threads: faiss 1, BLAS/numpy 1 (threadpoolctl), CPU temperature: not monitored; cpu_freq at repeat boundaries logged as throttling proxy. CPU MHz at repeat boundaries: min 2419, max 2419. all conditions shuffled per repeat (seeded) so thermal drift hits all arms alike (H7).

**pytest** (whole suite at Phase 4 exit): 37 tests, 0 failures, 0 errors, 0 skipped (`results/phase4/phase4_20261011_223158/pytest_junit.xml`).

**Manuscript hook**: Sections 7 (retrieval quality and scalability) and 9 (latency); Tables T3, T4, T5a; figures F3-F6.
<!-- END:phase4 -->

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
- **D-3.1 Validation pair mix**: plan 3.3a asks for 500 random corpus pairs. Random paragraph pairs have low cosine (cos^2 near 0), which would only test one end of the range, so the 500 pairs are 250 random corpus pairs plus 250 query-to-exact-top-50 pairs (the retrieval-relevant range). Validation uses unclipped (unbiased) estimates; retrieval uses estimates clipped to [0, 1] (plan 3.1).
- **D-3.2 Tier A without per-call transpile**: Aer executes set_statevector, h and cswap natively; with the same seed the estimates are identical with and without transpile (Phase 3 `tierA_timing.json`), so runs skip transpile (lower cost). The SWAP test itself is still executed by the simulator.
- **D-3.3 Zardini estimator (3.6, [P1]) deferred**: plan Section 0 says to finish all P0 work first; it requires reading the original paper to implement the exact formulas. It is not implemented yet and will be marked "not implemented" if time runs out.
- **D-3.4 Rankings not committed**: per-configuration rankings (`results/phase3/<run>/rankings/*.npz`) are git-ignored; they are fully seeded and regenerate exactly with `python tasks.py phase3`. All summary CSV/JSON files are committed.
- **D-3.5 Shot-threshold rule**: the exit gate "Hit@k within CI" is operationalised two ways: (1) paired bootstrap 95% CI of (quantum - classical) contains 0 at that S and at every larger S in the grid; (2) quantum mean inside the classical 95% CI. Rule (1) is strict: a small but consistent loss on a few queries is flagged as a difference. The formal, pre-registered tests (McNemar / Holm) are Phase 4 (4.6).
- **D-4.1 Two sources of quantum-sim randomness**: quality results (T3, tests, failure analysis) use the seeded Phase 3 rankings (shared random stream per configuration). The latency experiment runs `qrag/rerank.py` (`QuantumSimRetriever`) with its own per-repeat random stream: same distribution, different draws, so no quality metric is taken from the latency run. Full-scan latency uses argpartition + sort of the top-k (equal-key ties at the cut may differ from the stable full sort used for quality).
- **D-4.2 Latency k**: Phase 4 times k=10 (what the pipeline needs) whereas Phase 2 timed k=50; Flat latency was re-measured here, so Phase 2 and Phase 4 Flat numbers are not directly comparable. Power plan was again "Balanced" (see D-2.1).
- **D-4.3 Primary test choice (4.6)**: the plan pre-lists Hit@3 and MRR classical vs quantum with McNemar/paired-bootstrap and Holm. Because the quantum arm has 5 seeds, the primary test is a paired bootstrap on the per-query difference between the seed-averaged quantum outcome and the classical outcome (Holm within each 15-test family). Wilcoxon and exact McNemar (seed 0 only) are reported as uncorrected secondary checks and are not used for conclusions.
- **D-4.4 Memory (4.2)**: "memory vs N" is accounted from serialised index bytes and array sizes (Phase 2 `build.csv`), not from per-process RSS.
<!-- END:deviations -->

## 5. Failures, Limitations, Threats to Validity
<!-- BEGIN:failures -->
- **Swap during benchmark**: the pagefile grew during every model's run (see the "Swap delta" column in the Phase 0 table), so the strict "no swapping" wording of H2(b) is not fully met on this 8 GB machine even for the chosen model; close browsers and other heavy apps during generation runs (H5/H10).
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
