"""MiniLM-L6-v2 embedding (CPU), L2 normalisation and zero-padding to 512 for the quantum arm."""
from __future__ import annotations

import numpy as np

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
DIM, PADDED_DIM = 384, 512


def load_model():
    import torch
    from sentence_transformers import SentenceTransformer

    torch.set_num_threads(4)
    return SentenceTransformer(MODEL_NAME, device="cpu")


def embed_texts(model, texts: list[str], batch_size: int = 64) -> np.ndarray:
    """float32, L2-normalised so inner product = cosine."""
    vecs = model.encode(texts, batch_size=batch_size, show_progress_bar=False, convert_to_numpy=True,
                        normalize_embeddings=True)
    return np.ascontiguousarray(vecs, dtype=np.float32)


def pad_to_512(vecs: np.ndarray) -> np.ndarray:
    """Zero-pad 384 -> 512 (2^9). Norm and cosine are unchanged."""
    out = np.zeros((vecs.shape[0], PADDED_DIM), dtype=np.float32)
    out[:, : vecs.shape[1]] = vecs
    return out
