"""Statistics helpers (D13): nonparametric bootstrap confidence intervals."""
from __future__ import annotations

from typing import Callable

import numpy as np


def bootstrap_ci(values: np.ndarray, stat: Callable[[np.ndarray], float] = np.mean, n_boot: int = 10_000,
                 alpha: float = 0.05, seed: int = 42, chunk: int = 1000) -> tuple[float, float, float]:
    """Percentile bootstrap over items. Returns (point estimate, lo, hi). Vectorised for stat=np.mean."""
    values = np.asarray(values, dtype=np.float64)
    n = len(values)
    rng = np.random.default_rng(seed)
    out = np.empty(n_boot)
    for s in range(0, n_boot, chunk):
        m = min(chunk, n_boot - s)
        sample = values[rng.integers(0, n, size=(m, n))]
        out[s : s + m] = sample.mean(axis=1) if stat is np.mean else np.apply_along_axis(stat, 1, sample)
    lo, hi = np.percentile(out, [100 * alpha / 2, 100 * (1 - alpha / 2)])
    return float(stat(values)), float(lo), float(hi)
