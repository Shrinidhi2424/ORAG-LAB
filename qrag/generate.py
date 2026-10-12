"""Generator wrapper (plan 5.2): Ollama, CPU-only, deterministic decoding, disk cache keyed by
hash(model, model digest, messages, options) so reruns are exact (R6)."""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = ROOT / "cache" / "llm"
MODEL = "qwen2.5:1.5b-instruct"  # chosen by the Phase 0 H2 gate
OPTIONS = {"temperature": 0, "seed": 42, "num_ctx": 2048, "num_predict": 48, "num_gpu": 0}

SYSTEM_RAG = ("You answer questions using ONLY the provided context. If the context does not contain the answer, "
              "reply exactly: I cannot find the answer in the provided context.")
SYSTEM_CLOSED = ("Answer the question from your own knowledge. If you do not know the answer, "
                 "reply exactly: I don't know.")
ANSWER_HINT = "Answer concisely (a few words or one sentence)."


def build_messages(question: str, contexts: list[str] | None) -> list[dict]:
    """Appendix A.5 prompt; contexts=None gives the closed-book control prompt."""
    if contexts is None:
        return [{"role": "system", "content": SYSTEM_CLOSED},
                {"role": "user", "content": f"Question: {question}\n{ANSWER_HINT}"}]
    ctx = "\n".join(f"[{i + 1}] {c}" for i, c in enumerate(contexts))
    return [{"role": "system", "content": SYSTEM_RAG},
            {"role": "user", "content": f"Context:\n{ctx}\n\nQuestion: {question}\n{ANSWER_HINT}"}]


def cache_key(model: str, digest: str, messages: list[dict], options: dict) -> str:
    blob = json.dumps({"model": model, "digest": digest, "messages": messages, "options": options}, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


class OllamaGenerator:
    def __init__(self, model: str = MODEL, options: dict | None = None, cache_dir: Path = CACHE_DIR, keep_alive: str = "5m"):
        import ollama

        self.client = ollama.Client()
        self.model, self.options, self.keep_alive = model, dict(options or OPTIONS), keep_alive
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.digest = next(m.digest for m in self.client.list().models if m.model == model)

    def key(self, messages: list[dict]) -> str:
        return cache_key(self.model, self.digest, messages, self.options)

    def cached(self, key: str) -> dict | None:
        p = self.cache_dir / f"{key}.json"
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None

    def generate(self, messages: list[dict]) -> dict:
        key = self.key(messages)
        hit = self.cached(key)
        if hit is not None:
            return {**hit, "cached": True}
        t0 = time.perf_counter()
        r = self.client.chat(model=self.model, messages=messages, options=self.options, keep_alive=self.keep_alive)
        rec = {"key": key, "model": self.model, "digest": self.digest, "options": self.options,
               "text": r.message.content.strip(), "done_reason": r.done_reason, "wall_s": time.perf_counter() - t0,
               "prompt_tokens": r.prompt_eval_count, "gen_tokens": r.eval_count,
               "prompt_eval_s": (r.prompt_eval_duration or 0) / 1e9, "eval_s": (r.eval_duration or 0) / 1e9}
        tmp = self.cache_dir / f"{key}.json.tmp"
        tmp.write_text(json.dumps(rec, ensure_ascii=False), encoding="utf-8")
        tmp.replace(self.cache_dir / f"{key}.json")  # atomic: an interrupted run never leaves a partial entry
        return {**rec, "cached": False}

    def unload(self) -> None:
        self.client.generate(model=self.model, prompt="", keep_alive=0)
