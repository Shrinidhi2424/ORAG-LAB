"""Timing utility (R5, D15): perf_counter, discarded warm-up, median / p95."""
from __future__ import annotations

import time
from dataclasses import asdict, dataclass
from typing import Callable, Sequence

import numpy as np


@dataclass
class TimingStats:
    n: int
    median_ms: float
    p95_ms: float
    mean_ms: float
    min_ms: float
    max_ms: float

    def as_dict(self) -> dict:
        return asdict(self)


def summarize(samples_s: Sequence[float]) -> TimingStats:
    ms = np.asarray(samples_s, dtype=np.float64) * 1e3
    return TimingStats(
        n=int(ms.size),
        median_ms=float(np.median(ms)),
        p95_ms=float(np.percentile(ms, 95)),
        mean_ms=float(ms.mean()),
        min_ms=float(ms.min()),
        max_ms=float(ms.max()),
    )


def time_calls(fn: Callable[[object], object], inputs: Sequence, warmup: int = 10) -> tuple[list[float], TimingStats]:
    """Call fn(x) for each input; the first `warmup` inputs are run but discarded."""
    for x in inputs[:warmup]:
        fn(x)
    samples = []
    for x in inputs[warmup:]:
        t0 = time.perf_counter()
        fn(x)
        samples.append(time.perf_counter() - t0)
    return samples, summarize(samples)


class Stopwatch:
    """Context manager: `with Stopwatch() as sw: ...; sw.elapsed` (seconds)."""

    def __enter__(self):
        self._t0 = time.perf_counter()
        self.elapsed = 0.0
        return self

    def __exit__(self, *exc):
        self.elapsed = time.perf_counter() - self._t0
        return False
