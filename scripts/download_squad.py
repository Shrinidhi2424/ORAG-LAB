"""Task 0.5: download SQuAD v1.1 (official JSON) and store sha256 checksums."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from qrag.manifest import write_run_manifest  # noqa: E402

BASE = "https://rajpurkar.github.io/SQuAD-explorer/dataset/"
FILES = ["train-v1.1.json", "dev-v1.1.json"]
RAW = ROOT / "data" / "raw" / "squad_v1.1"
CHECKSUMS = ROOT / "data" / "squad_v1.1.checksums.json"


def digest(path: Path, algo: str) -> str:
    h = hashlib.new(algo)
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", required=True)
    args = ap.parse_args()
    RAW.mkdir(parents=True, exist_ok=True)
    info = {}
    for name in FILES:
        dest = RAW / name
        if not dest.exists():
            print(f"downloading {name} ...")
            urllib.request.urlretrieve(BASE + name, dest)
        data = json.loads(dest.read_text(encoding="utf-8"))
        n_par = sum(len(a["paragraphs"]) for a in data["data"])
        n_q = sum(len(p["qas"]) for a in data["data"] for p in a["paragraphs"])
        info[name] = {
            "url": BASE + name,
            "bytes": dest.stat().st_size,
            "sha256": digest(dest, "sha256"),
            "md5": digest(dest, "md5"),
            "version": data.get("version"),
            "articles": len(data["data"]),
            "paragraphs": n_par,
            "questions": n_q,
        }
    CHECKSUMS.write_text(json.dumps(info, indent=2), encoding="utf-8")
    out_dir = ROOT / "results" / "phase0" / args.run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "squad_checksums.json").write_text(json.dumps(info, indent=2), encoding="utf-8")
    write_run_manifest(out_dir, "phase0", args.run_id, seeds={"global": 42}, config={"task": "download_squad"})
    print(json.dumps(info, indent=2))


if __name__ == "__main__":
    main()
