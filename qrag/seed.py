"""Global seed utility (R2)."""
from __future__ import annotations

import os
import random

import numpy as np

DEFAULT_SEED = 42


def set_global_seed(seed: int = DEFAULT_SEED) -> np.random.Generator:
    """Seed python, numpy (legacy) and torch if present; return a fresh Generator."""
    os.environ["PYTHONHASHSEED"] = str(seed)
    random.seed(seed)
    np.random.seed(seed)
    try:
        import torch

        torch.manual_seed(seed)
    except ImportError:
        pass
    return np.random.default_rng(seed)
