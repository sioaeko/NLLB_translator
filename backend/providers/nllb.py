"""NLLB-200 engine — local inference via CTranslate2 (int8).

Light enough to run on a free HuggingFace Spaces CPU. Heavy objects load lazily
on first use and are shared across requests.
"""

from __future__ import annotations

import os
from functools import lru_cache
from threading import Lock

from languages import is_valid
from providers.base import TranslationProvider

MODEL_DIR = os.environ.get("CT2_MODEL_DIR", "models/nllb-200-distilled-600M-int8")
HF_MODEL = os.environ.get("HF_MODEL", "facebook/nllb-200-distilled-600M")
DEVICE = os.environ.get("CT2_DEVICE", "cpu")
COMPUTE_TYPE = os.environ.get("CT2_COMPUTE_TYPE", "int8")
MAX_DECODING_LENGTH = int(os.environ.get("MAX_DECODING_LENGTH", "256"))


class NLLBProvider(TranslationProvider):
    id = "nllb"
    name = "NLLB-200 (600M)"
    kind = "local"
    description = "Meta's open translation model · 200 languages · runs offline"
    private = True
    setup_hint = "Convert the model: `python convert_model.py`"

    def __init__(self) -> None:
        self._translator = None
        self._tokenizer = None
        self._lock = Lock()

    def is_available(self) -> bool:
        return os.path.isdir(MODEL_DIR)

    def _ensure_loaded(self) -> None:
        if self._translator is not None:
            return
        with self._lock:
            if self._translator is not None:
                return
            import ctranslate2
            import transformers

            self._translator = ctranslate2.Translator(
                MODEL_DIR, device=DEVICE, compute_type=COMPUTE_TYPE
            )
            self._tokenizer = transformers.AutoTokenizer.from_pretrained(HF_MODEL)

    @lru_cache(maxsize=2048)
    def _translate_line(self, text: str, src: str, tgt: str) -> str:
        self._tokenizer.src_lang = src
        source = self._tokenizer.convert_ids_to_tokens(self._tokenizer.encode(text))
        results = self._translator.translate_batch(
            [source],
            target_prefix=[[tgt]],
            beam_size=4,
            max_decoding_length=MAX_DECODING_LENGTH,
        )
        target_tokens = results[0].hypotheses[0][1:]  # drop the target-lang token
        return self._tokenizer.decode(
            self._tokenizer.convert_tokens_to_ids(target_tokens)
        )

    def translate(self, text: str, src: str, tgt: str) -> str:
        if not is_valid(src) or not is_valid(tgt):
            raise ValueError("Unknown language code for NLLB.")
        self._ensure_loaded()
        out = []
        for line in text.split("\n"):
            out.append(self._translate_line(line, src, tgt) if line.strip() else "")
        return "\n".join(out)
