# QRAG-Lab: one-page results summary

Quantum-inspired (SWAP-test, simulated) retrieval vs exact FAISS cosine in a containerised RAG pipeline on SQuAD v1.1. All numbers: `FINDINGS.md` section 8; run on a CPU-only 8 GB laptop.

## What was done

- Corpus ladder 1k to 20958 paragraphs; 300 evaluation questions on 275 gold paragraphs (200 for generation); embedder MiniLM-L6; generator qwen2.5:1.5b (CPU).
- Estimator validated against theory and a real 19-qubit Aer circuit: RMSE slope -0.499 (theory -0.5); circuit cost 0.110 s per circuit (classical simulation).

## Key results

- Retrieval (N=all, Hit@3): Flat 0.680 [0.627, 0.733]; quantum-sim S=1024 0.626 [0.577, 0.675]; S=16384 0.675 [0.623, 0.725].
- Hallucination (N=all, seed 0): rises at S=64 (difference +0.185 [+0.115, +0.255], Holm p = 0.0000), no detectable change at S=1024 (difference +0.015 [-0.040, +0.070], Holm p = 0.7283).
- Mechanism: gold paragraph in context decides the outcome; the 1.5B generator rarely abstains when it is missing.
- Latency (N=all, median / p95 ms): Flat | IVF | quantum-sim | full scan = 2.918 / 6.710 | 0.417 / 0.870 | 2.903 / 5.687 | 5.175 / 8.361. No latency benefit; emulated latency only.
- Break-even: hallucination within +-0.075 from S = 1024; Hit@3 CI contains 0 from S = 16384.
- Reproducibility: clean-room clone reproduced 85 of 85 artifacts.

## Honest framing

No quantum speedup is claimed; the quantum arm is a classical simulation and its latency is emulated. Single dataset, embedder and small generator; 200 generated questions; faithfulness judge not validated by humans yet.

## Figures and tables for the seminar (copies in `docs/seminar/`)

- System architecture: `docs/seminar/F1_architecture.png` (data `F1_architecture.csv`)
- Estimator validation: `docs/seminar/F2_error_vs_shots.png` (data `F2_error_vs_shots.csv`)
- Retrieval quality vs N: `docs/seminar/F4_quality_vs_N.png` (data `F4_quality_vs_N.csv`)
- Retrieval latency vs N: `docs/seminar/F5_latency_vs_N.png` (data `F5_latency_vs_N.csv`)
- Outcome taxonomy: `docs/seminar/F8_outcome_taxonomy.png` (data `F8_outcome_taxonomy.csv`)
- Mediation by gold-in-context: `docs/seminar/F9_hallucination_by_gold_in_context.png` (data `F9_hallucination_by_gold_in_context.csv`)
- Pareto: hallucination vs latency: `docs/seminar/F7_pareto_hallucination.png` (data `F7_pareto_hallucination.csv`)
- Concurrency: `docs/seminar/F10_concurrency.png` (data `F10_concurrency.csv`)
- Tables: T3 main retrieval table, T5b outcome table, T7d break-even (FINDINGS.md sections 2 and 3)
