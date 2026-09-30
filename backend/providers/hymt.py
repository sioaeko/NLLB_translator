"""Hy-MT2 engine — Tencent's 2026 translation model (1.8B), local via llama.cpp.

Apache-2.0, 38 languages, and fast enough on a CPU: it runs from the official
Q4_K_M GGUF (~1.1 GB). Needs the optional ``llama-cpp-python`` package
(``requirements-llm.txt``) and the model file (``fetch_hymt.py``); the engine
reports itself unavailable until both are present.
"""

from __future__ import annotations

import importlib.util
import os
from functools import lru_cache
from threading import Lock

from languages import name_for
from providers.base import TranslationProvider, clean_output

MODEL_PATH = os.environ.get("HYMT_MODEL_PATH", "models/hy-mt2-1.8b/Hy-MT2-1.8B-Q4_K_M.gguf")
N_CTX = int(os.environ.get("HYMT_CTX", "4096"))
N_THREADS = int(os.environ.get("HYMT_THREADS", "0")) or None  # None: llama.cpp decides

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

    def is_available(self) -> bool:
        return os.path.isfile(MODEL_PATH) and importlib.util.find_spec("llama_cpp") is not None

    def _ensure_loaded(self) -> None:
        if self._llm is not None:
            return
        with self._lock:
            if self._llm is not None:
                return
            from llama_cpp import Llama

            self._llm = Llama(model_path=MODEL_PATH, n_ctx=N_CTX, n_threads=N_THREADS, verbose=False)

    @lru_cache(maxsize=2048)
    def _translate_line(self, text: str, src: str, tgt: str) -> str:
        with self._infer_lock:
            out = self._llm.create_chat_completion(
                messages=[{"role": "user", "content": _prompt(text, src, tgt)}],
                # Sampling settings recommended on the model card.
                temperature=0.7,
                top_p=0.6,
                top_k=20,
                repeat_penalty=1.05,
                max_tokens=min(2048, 64 + 4 * len(text)),
            )
        return clean_output(out["choices"][0]["message"]["content"] or "")

    def translate(self, text, src, tgt, api_key=None, model=None) -> str:
        for code in (src, tgt):
            if code not in LANGS:
                raise ValueError(
                    f"Hy-MT2 doesn't support {name_for(code)}. Try NLLB-200 for this language."
                )
        self._ensure_loaded()
        # Line by line: keeps each prompt short and lets unchanged lines hit the cache
        # while the user is still typing.
        return "\n".join(
            self._translate_line(line, src, tgt) if line.strip() else "" for line in text.split("\n")
        )
