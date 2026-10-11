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


def holm(pvals) -> np.ndarray:
    """Holm-Bonferroni adjusted p-values (monotone, capped at 1), in the input order."""
    p = np.asarray(pvals, dtype=np.float64)
    order = np.argsort(p)
    adj = np.empty_like(p)
    running = 0.0
    m = len(p)
    for rank, i in enumerate(order):
        running = max(running, (m - rank) * p[i])
        adj[i] = min(1.0, running)
    return adj


def paired_bootstrap_p(diff: np.ndarray, n_boot: int = 10_000, seed: int = 42) -> float:
    """Two-sided bootstrap p-value for mean(diff) = 0 (resample items; add-one so p >= 1/(n_boot+1))."""
    diff = np.asarray(diff, dtype=np.float64)
    rng = np.random.default_rng(seed)
    n = len(diff)
    means = np.concatenate([diff[rng.integers(0, n, size=(1000, n))].mean(axis=1) for _ in range(n_boot // 1000)])
    le, ge = (means <= 0).sum(), (means >= 0).sum()
    return float(min(1.0, 2 * (min(le, ge) + 1) / (len(means) + 1)))


def mcnemar_exact(a: np.ndarray, b: np.ndarray) -> tuple[int, int, float]:
    """Exact McNemar on paired booleans. Returns (a-only, b-only, two-sided p)."""
    from scipy.stats import binomtest

    a, b = np.asarray(a, bool), np.asarray(b, bool)
    n10, n01 = int((a & ~b).sum()), int((~a & b).sum())
    n = n10 + n01
    return n10, n01, 1.0 if n == 0 else float(binomtest(min(n10, n01), n, 0.5).pvalue)


def loglog_slope(x: np.ndarray, y: np.ndarray) -> tuple[float, float]:
    """OLS slope and intercept of log(y) on log(x)."""
    s, c = np.polyfit(np.log(x), np.log(y), 1)
    return float(s), float(c)


def loglog_slope_ci(xs, ys_by_x, n_boot: int = 10_000, seed: int = 42) -> tuple[float, float, float, float]:
    """Power-law exponent b in y ~ x^b. ys_by_x: one array of repeat values per x. Point estimate uses the
    median per x; the 95% CI bootstraps the repeats within each x. Returns (b, lo, hi, R^2 of the point fit)."""
    xs = np.asarray(xs, dtype=np.float64)
    med = np.array([np.median(y) for y in ys_by_x])
    b, c = loglog_slope(xs, med)
    resid = np.log(med) - (b * np.log(xs) + c)
    r2 = 1 - (resid**2).sum() / ((np.log(med) - np.log(med).mean()) ** 2).sum()
    rng = np.random.default_rng(seed)
    out = np.empty(n_boot)
    for i in range(n_boot):
        m = np.array([np.median(rng.choice(y, size=len(y), replace=True)) for y in ys_by_x])
        out[i] = np.polyfit(np.log(xs), np.log(m), 1)[0]
    lo, hi = np.percentile(out, [2.5, 97.5])
    return b, float(lo), float(hi), float(r2)
