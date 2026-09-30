"""Download the Hy-MT2 1.8B GGUF (official Tencent Q4_K_M build, ~1.1 GB).

Run once before starting the server if you want the Hy-MT2 engine:

    python fetch_hymt.py

It also needs ``llama-cpp-python`` (see requirements-llm.txt).
"""

from __future__ import annotations

import os

from huggingface_hub import hf_hub_download

REPO = os.environ.get("HYMT_REPO", "tencent/Hy-MT2-1.8B-GGUF")
FILE = os.environ.get("HYMT_FILE", "Hy-MT2-1.8B-Q4_K_M.gguf")
OUT_DIR = os.environ.get("HYMT_DIR", "models/hy-mt2-1.8b")


def main() -> None:
    path = hf_hub_download(REPO, FILE, local_dir=OUT_DIR)
    print(f"Hy-MT2 ready at {path} ({os.path.getsize(path) / 1e6:.0f} MB)")


if __name__ == "__main__":
    main()
