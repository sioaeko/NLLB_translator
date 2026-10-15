"""Hy-MT2 engine — Tencent's 2026 translation model (1.8B), local via llama.cpp.

Apache-2.0, 38 languages, and fast enough on a CPU: it runs from the official
Q4_K_M GGUF (~1.1 GB). Needs the optional ``llama-cpp-python`` package
(``requirements-llm.txt``) and the model file (``fetch_hymt.py``); the engine
reports itself unavailable until both are present.
"""

from __future__ import annotations

import importlib.util
import os
from collections import OrderedDict
from collections.abc import Iterator
from threading import Event, Lock

from inference_runtime import check_cancelled, cpu_thread_count, local_inference
from languages import name_for
from providers.base import TranslationProvider, clean_output, clean_stream

MODEL_PATH = os.environ.get("HYMT_MODEL_PATH", "models/hy-mt2-1.8b/Hy-MT2-1.8B-Q4_K_M.gguf")
N_CTX = int(os.environ.get("HYMT_CTX", "4096"))
N_THREADS = int(os.environ.get("HYMT_THREADS", "0"))

# FLORES-200 code -> (English name, Chinese name) as used in Hy-MT2's prompts.
LANGS: dict[str, tuple[str, str]] = {
    "zho_Hans": ("Chinese", "中文"),
    "zho_Hant": ("Traditional Chinese", "繁体中文"),
    "yue_Hant": ("Cantonese", "粤语"),
    "eng_Latn": ("English", "英语"),
    "fra_Latn": ("French", "法语"),
    "por_Latn": ("Portuguese", "葡萄牙语"),
    "spa_Latn": ("Spanish", "西班牙语"),
    "jpn_Jpan": ("Japanese", "日语"),
    "tur_Latn": ("Turkish", "土耳其语"),
    "rus_Cyrl": ("Russian", "俄语"),
    "arb_Arab": ("Arabic", "阿拉伯语"),
    "kor_Hang": ("Korean", "韩语"),
    "tha_Thai": ("Thai", "泰语"),
    "ita_Latn": ("Italian", "意大利语"),
    "deu_Latn": ("German", "德语"),
    "vie_Latn": ("Vietnamese", "越南语"),
    "zsm_Latn": ("Malay", "马来语"),
    "ind_Latn": ("Indonesian", "印尼语"),
    "tgl_Latn": ("Filipino", "菲律宾语"),
    "hin_Deva": ("Hindi", "印地语"),
    "pol_Latn": ("Polish", "波兰语"),
    "ces_Latn": ("Czech", "捷克语"),
    "nld_Latn": ("Dutch", "荷兰语"),
    "khm_Khmr": ("Khmer", "高棉语"),
    "mya_Mymr": ("Burmese", "缅甸语"),
    "pes_Arab": ("Persian", "波斯语"),
    "guj_Gujr": ("Gujarati", "古吉拉特语"),
    "urd_Arab": ("Urdu", "乌尔都语"),
    "tel_Telu": ("Telugu", "泰卢固语"),
    "mar_Deva": ("Marathi", "马拉地语"),
    "heb_Hebr": ("Hebrew", "希伯来语"),
    "ben_Beng": ("Bengali", "孟加拉语"),
    "tam_Taml": ("Tamil", "泰米尔语"),
    "ukr_Cyrl": ("Ukrainian", "乌克兰语"),
    "bod_Tibt": ("Tibetan", "藏语"),
    "kaz_Cyrl": ("Kazakh", "哈萨克语"),
    "khk_Cyrl": ("Mongolian", "蒙古语"),
    "uig_Arab": ("Uyghur", "维吾尔语"),
}
_CHINESE = {"zho_Hans", "zho_Hant", "yue_Hant"}


def _prompt(text: str, src: str, tgt: str) -> str:
    """Official Hy-MT2 templates: Chinese wording when Chinese is involved."""
    english, chinese = LANGS[tgt]
    if src in _CHINESE or tgt in _CHINESE:
        return f"将以下文本翻译为{chinese}，注意只需要输出翻译后的结果，不要额外解释：\n\n{text}"
    return (
        f"Translate the following text into {english}. Note that you should only "
        f"output the translated result without any additional explanation:\n\n{text}"
    )


class HyMTProvider(TranslationProvider):
    id = "hymt"
    name = "Hy-MT2 (1.8B)"
    kind = "local"
    description = "Tencent · 38 languages · 2026"
    private = True
    setup_hint = "Run `python fetch_hymt.py` and install requirements-llm.txt"

    def __init__(self) -> None:
        self._llm = None
        self._lock = Lock()
        self._infer_lock = Lock()  # a llama.cpp context serves one request at a time
        self._cache: OrderedDict[tuple[str, str, str], str] = OrderedDict()
        self._cache_lock = Lock()

    def is_available(self) -> bool:
        return os.path.isfile(MODEL_PATH) and importlib.util.find_spec("llama_cpp") is not None

    def _ensure_loaded(self) -> None:
        if self._llm is not None:
            return
        with self._lock:
            if self._llm is not None:
                return
            from llama_cpp import Llama

            threads = cpu_thread_count(N_THREADS)
            self._llm = Llama(
                model_path=MODEL_PATH,
                n_ctx=N_CTX,
                n_threads=threads,
                n_threads_batch=threads,
                verbose=False,
            )

    def _translate_line(self, text: str, src: str, tgt: str) -> str:
        return clean_output("".join(self._stream_translate_line(text, src, tgt)))

    def _cached_line(self, key: tuple[str, str, str]) -> str | None:
        with self._cache_lock:
            if key not in self._cache:
                return None
            self._cache.move_to_end(key)
            return self._cache[key]

    def _stream_translate_line(
        self, text: str, src: str, tgt: str, cancel: Event | None = None
    ) -> Iterator[str]:
        check_cancelled(cancel)
        key = (text, src, tgt)
        cached = self._cached_line(key)
        if cached is not None:
            yield cached
            return

        with local_inference(cancel), self._infer_lock:
            # Another request may have completed this line while we waited.
            cached = self._cached_line(key)
            if cached is not None:
                yield cached
                return
            chunks = self._llm.create_chat_completion(
                messages=[{"role": "user", "content": _prompt(text, src, tgt)}],
                # Sampling settings recommended on the model card.
                temperature=0.7,
                top_p=0.6,
                top_k=20,
                repeat_penalty=1.05,
                max_tokens=min(2048, 64 + 4 * len(text)),
                stream=True,
            )
            output = []

            def content_deltas():
                for chunk in chunks:
                    check_cancelled(cancel)
                    choices = chunk.get("choices", [])
                    delta = choices[0].get("delta", {}).get("content") if choices else None
                    if delta:
                        yield delta
                    reason = choices[0].get("finish_reason") if choices else None
                    if reason is not None:
                        if reason == "length":
                            raise RuntimeError("Translation reached the model limit. Try a shorter text.")
                        if reason != "stop":
                            raise RuntimeError(f"Hy-MT2 stopped without completing the translation ({reason}).")
                        return
                raise RuntimeError("Hy-MT2 interrupted the translation before it finished.")

            stream = clean_stream(content_deltas())
            try:
                for delta in stream:
                    check_cancelled(cancel)
                    output.append(delta)
                    yield delta
            finally:
                # Closing the outer generator also closes llama.cpp's generator
                # and releases both locks. A partial or failed line never caches.
                stream.close()
                close = getattr(chunks, "close", None)
                if close is not None:
                    close()
            check_cancelled(cancel)
            translation = clean_output("".join(output))
            if not translation:
                raise RuntimeError("Hy-MT2 returned no translation.")
            with self._cache_lock:
                self._cache[key] = translation
                self._cache.move_to_end(key)
                while len(self._cache) > 2048:
                    self._cache.popitem(last=False)

    def _validate(self, src: str, tgt: str) -> None:
        for code in (src, tgt):
            if code not in LANGS:
                raise ValueError(
                    f"Hy-MT2 doesn't support {name_for(code)}. Try NLLB-200 for this language."
                )

    def translate(self, text, src, tgt, api_key=None, model=None) -> str:
        self._validate(src, tgt)
        self._ensure_loaded()
        # Line by line: keeps each prompt short and lets unchanged lines hit the cache
        # while the user is still typing.
        return "\n".join(
            self._translate_line(line, src, tgt) if line.strip() else "" for line in text.split("\n")
        )

    def stream_translate(
        self, text, src, tgt, api_key=None, model=None, cancel: Event | None = None
    ) -> Iterator[str]:
        check_cancelled(cancel)
        self._validate(src, tgt)
        self._ensure_loaded()
        for index, line in enumerate(text.split("\n")):
            check_cancelled(cancel)
            if index:
                yield "\n"
            if line.strip():
                yield from self._stream_translate_line(line, src, tgt, cancel)
