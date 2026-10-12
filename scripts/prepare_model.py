"""Copy the pinned MiniLM snapshot from the local Hugging Face cache into models/minilm (git-ignored) so that the
embedder image can bake it in. Verifies the revision against the one recorded in Phase 1."""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from huggingface_hub import snapshot_download  # noqa: E402

from qrag.embed import MODEL_NAME  # noqa: E402


def main() -> None:
    src = Path(snapshot_download(MODEL_NAME))
    p1 = ROOT / "results" / "phase1" / (ROOT / "results/phase1/.current_run").read_text(encoding="utf-8").strip() / "embed_info.json"
    expected = json.loads(p1.read_text(encoding="utf-8"))["revision"]
    assert src.name == expected, f"snapshot {src.name} != Phase 1 revision {expected}"
    dst = ROOT / "models" / "minilm"
    if dst.exists():
        shutil.rmtree(dst)
    dst.mkdir(parents=True)
    n = 0
    for f in src.rglob("*"):
        if f.is_file() and f.suffix not in (".h5", ".ot", ".msgpack", ".onnx") and "onnx" not in f.parts and "openvino" not in f.parts:
            target = dst / f.relative_to(src)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(f.resolve(), target)
            n += 1
    size = sum(f.stat().st_size for f in dst.rglob("*") if f.is_file())
    print(f"copied {n} files ({size / 1e6:.1f} MB) of revision {src.name} to {dst}")


if __name__ == "__main__":
    main()
