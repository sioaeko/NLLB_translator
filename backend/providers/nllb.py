"""NLLB-200 engine — local inference via CTranslate2 (int8).

Light enough to run on a free HuggingFace Spaces CPU. Heavy objects load lazily
on first use and are shared across requests.
"""

from __future__ import annotations

import os
from collections import OrderedDict
from collections.abc import Iterator
from threading import Event, Lock

from inference_runtime import check_cancelled, cpu_thread_count, local_inference
from languages import is_valid
from providers.base import TranslationProvider

MODEL_DIR = os.environ.get("CT2_MODEL_DIR", "models/nllb-200-distilled-600M-int8")
HF_MODEL = os.environ.get("HF_MODEL", "facebook/nllb-200-distilled-600M")
DEVICE = os.environ.get("CT2_DEVICE", "cpu")
COMPUTE_TYPE = os.environ.get("CT2_COMPUTE_TYPE", "int8")
MAX_DECODING_LENGTH = int(os.environ.get("MAX_DECODING_LENGTH", "256"))
N_THREADS = int(os.environ.get("CT2_THREADS", "0"))


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
        self._infer_lock = Lock()  # HF fast tokenizers are not thread-safe
        self._cache: OrderedDict[tuple[str, str, str], str] = OrderedDict()
        self._cache_lock = Lock()

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

            # Load the tokenizer first and publish `_translator` LAST: it is the
            # guard the fast path checks, so a concurrent request must never see
            # the translator ready while the tokenizer is still None.
            tokenizer = transformers.AutoTokenizer.from_pretrained(HF_MODEL)
            translator = ctranslate2.Translator(
                MODEL_DIR,
                device=DEVICE,
                compute_type=COMPUTE_TYPE,
                intra_threads=cpu_thread_count(N_THREADS),
                inter_threads=1,
            )
            self._tokenizer = tokenizer
            self._translator = translator

    def _cached_line(self, key: tuple[str, str, str]) -> str | None:
        with self._cache_lock:
            if key not in self._cache:
                return None
            self._cache.move_to_end(key)
            return self._cache[key]

    def _translate_line(
        self, text: str, src: str, tgt: str, cancel: Event | None = None
    ) -> str:
        check_cancelled(cancel)
        key = (text, src, tgt)
        cached = self._cached_line(key)
        if cached is not None:
            return cached
        # Serialize tokenizer use: the Rust fast tokenizer raises "Already
        # borrowed" under concurrent access, and setting src_lang mutates it.
        with local_inference(cancel), self._infer_lock:
            cached = self._cached_line(key)
            if cached is not None:
                return cached
            self._tokenizer.src_lang = src
            source = self._tokenizer.convert_ids_to_tokens(self._tokenizer.encode(text))
            results = self._translator.translate_batch(
                [source],
                target_prefix=[[tgt]],
                beam_size=4,
                max_decoding_length=MAX_DECODING_LENGTH,
            )
            target_tokens = results[0].hypotheses[0][1:]  # drop target-lang token
            translated = self._tokenizer.decode(
                self._tokenizer.convert_tokens_to_ids(target_tokens)
            )
            check_cancelled(cancel)
            with self._cache_lock:
                self._cache[key] = translated
                self._cache.move_to_end(key)
                while len(self._cache) > 2048:
                    self._cache.popitem(last=False)
            return translated

    def translate(self, text, src, tgt, api_key=None, model=None) -> str:
        return "".join(self.stream_translate(text, src, tgt, api_key, model))

    def stream_translate(
        self, text, src, tgt, api_key=None, model=None, cancel: Event | None = None
    ) -> Iterator[str]:
        check_cancelled(cancel)
        if not is_valid(src) or not is_valid(tgt):
            raise ValueError("Unknown language code for NLLB.")
        self._ensure_loaded()
        # Keep beam search quality and the shared per-line cache. Completed
        # lines can appear immediately while subsequent lines are still decoded.
        for index, line in enumerate(text.split("\n")):
            check_cancelled(cancel)
            if index:
                yield "\n"
            if line.strip():
                yield self._translate_line(line, src, tgt, cancel)
