"""Phase 9.4: consistency audit of FINDINGS.md against the artifacts (R4, R8).

Usage: python scripts/check_numbers.py [--run-id <phase9 run id>]   (exit code 1 if any hard check fails)
Checks:
  1. Every generated block (<!-- BEGIN:x --> ... <!-- END:x -->) equals what scripts/report.py renders from the artifacts
     right now, so no number inside a generated block was typed or edited by hand.
  2. Every artifact path quoted in FINDINGS.md (`results/...`, `data/...`, figure links) exists.
  3. Hand-authored text (deviations, failures, open questions, prose outside blocks) is scanned for numbers. Numbers that
     are design constants of the plan (ladder sizes, shot grid, seeds, thresholds, profile limits, ...) are allowed;
     any other number is reported as an unflagged hand-typed number (hard failure).
Writes results/phase9/<run_id>/number_audit.json when a run id is given (or a current Phase 9 run exists).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT))

import report  # noqa: E402

HAND_BLOCKS = ("deviations", "failures", "open")
# design constants that legitimately appear in hand-authored text (plan sections 2-3B, A.4-A.6)
ALLOWED = {
    "0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13", "14", "15", "16", "20", "25", "30", "32", "45", "48", "50", "64", "100", "128", "200",
    "256", "300", "384", "512", "1000", "1024", "2000", "2048", "4096", "5000", "8192", "10000", "16384", "11434",
    "42", "95", "250", "500", "0.25", "0.3", "0.5", "0.7", "0.05", "0.075", "0.10", "0.95", "1.5", "2.5", "1.1", "2.0", "1.0", "2024", "2026", "2023",
}
NUM = re.compile(r"(?<![\w.\-/@#])(\d+(?:\.\d+)?)(?![\w])")
PATH = re.compile(r"(?:`|\()((?:results|data)/[^`)\s]+)(?:`|\))")


def generated_mismatches(text: str) -> list[str]:
    rendered = report.render(text)
    names = re.findall(r"<!-- BEGIN:(\w+) -->", text)
    out = []
    for n in names:
        if n in HAND_BLOCKS:
            continue
        pat = re.compile(rf"<!-- BEGIN:{n} -->\n(.*?)<!-- END:{n} -->", re.S)
        a, b = pat.search(text), pat.search(rendered)
        if not a or not b or a.group(1) != b.group(1):
            out.append(n)
    return out


def hand_text(text: str) -> list[tuple[str, str]]:
    """(region name, text) for hand-authored regions."""
    regions = []
    for n in HAND_BLOCKS:
        m = re.search(rf"<!-- BEGIN:{n} -->\n(.*?)<!-- END:{n} -->", text, re.S)
        if m:
            regions.append((n, m.group(1)))
    outside = re.sub(r"<!-- BEGIN:(\w+) -->.*?<!-- END:\1 -->", "", text, flags=re.S)
    outside = re.sub(r"```.*?```", "", outside, flags=re.S)  # command listings
    regions.append(("prose outside blocks", outside))
    return regions


def scan_numbers(regions) -> tuple[list[dict], int]:
    flagged, allowed = [], 0
    for name, body in regions:
        for line in body.splitlines():
            clean = re.sub(r"`[^`]*`", "", line)  # code spans: paths, identifiers, model names
            clean = re.sub(r"(?:plan|task|tasks|item|items)\s+\d{1,2}\.\d{1,2}[a-z]?", "", clean)  # plan task references
            clean = re.sub(r"\(\d{1,2}\.\d{1,2}[a-z]?(?=[,)\s])", "(", clean)
            clean = re.sub(r"\b(?:D|P|T|F|S|N|M|R|RQ|H|E|phase|Phase|Section|section|Table|table|block)[-\s]?\d+(?:\.\d+)*[a-z]?\b", "", clean)
            for m in NUM.finditer(clean):
                tok = m.group(1)
                if tok in ALLOWED:
                    allowed += 1
                else:
                    flagged.append({"region": name, "number": tok, "context": clean.strip()[max(0, m.start() - 60): m.end() + 60]})
    return flagged, allowed


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id")
    a = ap.parse_args()
    text = report.FINDINGS.read_text(encoding="utf-8")
    mism = generated_mismatches(text)
    paths = sorted(set(PATH.findall(text)))
    missing = [p for p in paths if "<" not in p and "*" not in p and not (ROOT / p.rstrip(".,;:")).exists()]
    flagged, allowed = scan_numbers(hand_text(text))
    res = {"generated_blocks_checked": len([n for n in re.findall(r"<!-- BEGIN:(\w+) -->", text) if n not in HAND_BLOCKS]),
           "generated_blocks_not_reproducible": mism, "artifact_paths_checked": len(paths), "missing_paths": missing,
           "hand_numbers_allowed_design_constants": allowed, "unflagged_hand_numbers": flagged,
           "passed": not mism and not missing and not flagged}
    rid = a.run_id
    cur = ROOT / "results" / "phase9" / ".current_run"
    if not rid and cur.exists():
        rid = cur.read_text(encoding="utf-8").strip()
    if rid:
        d = ROOT / "results" / "phase9" / rid
        d.mkdir(parents=True, exist_ok=True)
        (d / "number_audit.json").write_text(json.dumps(res, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({k: (v if k != "unflagged_hand_numbers" else v[:15]) for k, v in res.items()}, indent=2, ensure_ascii=False))
    sys.exit(0 if res["passed"] else 1)


if __name__ == "__main__":
    main()
