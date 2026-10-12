"""Pydantic request/response schemas shared by all services (plan 6.1)."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Arm = Literal["classical", "quantum"]


class EmbedRequest(BaseModel):
    texts: list[str] = Field(min_length=1, max_length=64)


class EmbedResponse(BaseModel):
    service: str = "embedder"
    dim: int
    vectors: list[list[float]]
    compute_ms: float


class RetrieveRequest(BaseModel):
    vector: list[float]
    k: int = Field(default=10, ge=1, le=100)
    N: str = "all"  # corpus ladder rung: 1000 | 2000 | 5000 | 10000 | all
    M: int = Field(default=50, ge=1, le=1000)  # shortlist (quantum only)
    shots: int = Field(default=1024, ge=1, le=1 << 20)  # quantum only
    seed: int = 0  # quantum only


class RetrieveResponse(BaseModel):
    """Identical schema for the classical and the quantum-sim endpoint."""
    service: str
    arm: Arm
    N: str
    k: int
    ids: list[int]  # global paragraph indices, best first
    scores: list[float]  # exact cosine (classical) or estimated cos^2 (quantum-sim, emulated)
    compute_ms: float
    stages: dict[str, float] = {}


class GenerateRequest(BaseModel):
    messages: list[dict]


class GenerateResponse(BaseModel):
    service: str = "generator-gateway"
    text: str
    cached: bool
    model: str
    wall_s: float
    compute_ms: float


class RagRequest(BaseModel):
    question: str
    arm: Arm = "classical"
    k: int = Field(default=3, ge=1, le=20)
    N: str = "all"
    M: int = 50
    shots: int = 1024
    seed: int = 0


class Context(BaseModel):
    idx: int
    score: float
    text: str | None = None


class RagResponse(BaseModel):
    mode: Literal["retrieval_only", "full"]
    arm: Arm
    N: str
    question: str
    contexts: list[Context]
    answer: str | None = None
    answer_cached: bool | None = None
    timings: dict[str, float]  # ms; hop = client-side wall time of a service call, compute = time reported by the service
