"""Hallucination measurement (plan D10): correctness, abstention, HHEM faithfulness, five-way outcome taxonomy."""
from __future__ import annotations

import re
import string

HHEM_REPO = "vectara/hallucination_evaluation_model"
HHEM_REVISION = "de9a5e6ba9ba49531a022dba17e35ffeb2a6fad8"  # pinned (verified in Phase 5)
ABSTAIN_RE = re.compile(r"cannot find the answer|i don'?t know|i do not know", re.I)
OUTCOMES = ("correct_grounded", "correct_ungrounded", "hallucinated", "misread", "abstained")


def normalize_answer(s: str) -> str:
    """Official SQuAD v1.1 normalisation: lower, drop punctuation and articles, collapse whitespace."""
    s = s.lower()
    s = "".join(ch for ch in s if ch not in set(string.punctuation))
    s = re.sub(r"\b(a|an|the)\b", " ", s)
    return " ".join(s.split())


def contains_gold(output: str, answers: list[str]) -> bool:
    out = normalize_answer(output)
    return any(normalize_answer(a) and normalize_answer(a) in out for a in answers)


def is_abstain(output: str) -> bool:
    return bool(ABSTAIN_RE.search(output))


def hypothesis(question: str, answer: str) -> str:
    """HHEM hypothesis: the answer stated as a claim about the question (short spans alone are hard to judge)."""
    return f'The answer to the question "{question}" is {answer}'


def outcome(correct: bool, abstained: bool, faithful: bool | None, gold_in_context: bool) -> str:
    """Appendix A.4 rules, in this order: A; C and F; C and not F; not C with gold in context; else hallucinated."""
    if abstained:
        return "abstained"
    if correct:
        return "correct_grounded" if faithful else "correct_ungrounded"
    return "misread" if gold_in_context else "hallucinated"


class HHEMJudge:
    """Vectara HHEM-2.1-Open: P(hypothesis consistent with premise). CPU, batch scoring."""

    def __init__(self, threads: int = 4):
        import torch
        from transformers import AutoModelForSequenceClassification

        torch.set_num_threads(threads)
        self.model = AutoModelForSequenceClassification.from_pretrained(HHEM_REPO, trust_remote_code=True, revision=HHEM_REVISION)

    def score(self, pairs: list[tuple[str, str]], batch: int = 4) -> list[float]:
        out = []
        for i in range(0, len(pairs), batch):
            out += [float(x) for x in self.model.predict(pairs[i : i + batch])]
        return out
