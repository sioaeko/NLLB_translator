"""Download the NLLB-200 model from HuggingFace and convert it to CTranslate2
int8 format for fast, low-memory CPU inference.

Run once before starting the server:

    python convert_model.py

This produces ~600 MB in ``models/nllb-200-distilled-600M-int8`` (vs ~2.4 GB
for the fp32 HuggingFace checkpoint).
"""

from __future__ import annotations

import os
import subprocess
import sys

HF_MODEL = os.environ.get("HF_MODEL", "facebook/nllb-200-distilled-600M")
OUT_DIR = os.environ.get("CT2_MODEL_DIR", "models/nllb-200-distilled-600M-int8")
QUANTIZATION = os.environ.get("CT2_COMPUTE_TYPE", "int8")


def main() -> int:
    if os.path.isdir(OUT_DIR):
        print(f"Model already converted at '{OUT_DIR}'. Nothing to do.")
        return 0

    os.makedirs(os.path.dirname(OUT_DIR) or ".", exist_ok=True)
    # Invoke via `-m` so it works without the Scripts dir on PATH (Windows venvs).
    cmd = [
        sys.executable, "-m", "ctranslate2.converters.transformers",
        "--model", HF_MODEL,
        "--output_dir", OUT_DIR,
        "--quantization", QUANTIZATION,
    ]
    print("Running:", " ".join(cmd))
    result = subprocess.run(cmd)
    if result.returncode == 0:
        print(f"\nDone. CTranslate2 model written to '{OUT_DIR}'.")
    else:
        print("\nConversion failed.", file=sys.stderr)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
