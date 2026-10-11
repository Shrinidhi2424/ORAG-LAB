"""Tier B: vectorised emulator of the ideal SWAP-test measurement statistics (plan D2, task 3.1).

k ~ Binomial(S, P0), P0 = (1 + c^2) / 2, c = exact cosine  ->  c2_hat = 2k/S - 1 (estimate of cos^2).
Sampling k from the exact binomial is identical in distribution to S shots of the noise-free SWAP test.
HONESTY NOTE: the exact cosine is computed first; this measures retrieval under shot noise, not speed.
"""
from __future__ import annotations

import numpy as np

SHOTS_GRID = (64, 128, 256, 512, 1024, 2048, 4096, 8192, 16384)


def p0(cos: np.ndarray) -> np.ndarray:
    return np.clip((1.0 + np.asarray(cos, dtype=np.float64) ** 2) / 2.0, 0.0, 1.0)


def zero_counts(cos: np.ndarray, shots: int, rng: np.random.Generator) -> np.ndarray:
    """Ancilla-0 counts, int32, same shape as cos."""
    return rng.binomial(shots, p0(cos)).astype(np.int32)


def c2_from_counts(k: np.ndarray, shots: int, clip: bool = True) -> np.ndarray:
    c2 = 2.0 * np.asarray(k, dtype=np.float64) / shots - 1.0
    return np.clip(c2, 0.0, 1.0) if clip else c2


def estimate_c2(cos: np.ndarray, shots: int, rng: np.random.Generator, clip: bool = True) -> np.ndarray:
    return c2_from_counts(zero_counts(cos, shots, rng), shots, clip)


def theory_sd(cos: np.ndarray, shots: int) -> np.ndarray:
    """Std of the unclipped estimator: sqrt((1 - c^4) / S)."""
    return np.sqrt((1.0 - np.asarray(cos, dtype=np.float64) ** 4) / shots)


def config_rng(seed: int, *tags: int) -> np.random.Generator:
    """Independent, reproducible stream per (seed, config tags)."""
    return np.random.default_rng(np.random.SeedSequence([int(seed), *map(int, tags)]))


def rank_keys(c2_hat: np.ndarray, cos: np.ndarray, tie: str = "classical", rng: np.random.Generator | None = None) -> np.ndarray:
    """Sort keys (higher = better). Primary: clipped c2_hat. Ties: by classical cosine (default design choice)
    or uniformly at random ('random'); remaining ties by position via a stable sort."""
    if tie == "classical":
        frac = (np.asarray(cos, dtype=np.float64) + 1.0) / 2.0
    elif tie == "random":
        frac = rng.random(np.shape(c2_hat))
    elif tie == "none":
        frac = np.zeros(np.shape(c2_hat))
    else:
        raise ValueError(tie)
    # c2_hat values are multiples of 2/S >= 2/16384, so a tie-break term scaled into [0, 1e-6) never reorders them
    return np.asarray(c2_hat, dtype=np.float64) + 1e-6 * 0.999 * frac


def topk_from_keys(keys: np.ndarray, k: int) -> np.ndarray:
    """Row-wise top-k positions by descending key; equal keys keep ascending position (stable)."""
    return np.argsort(-keys, axis=-1, kind="stable")[..., :k]
