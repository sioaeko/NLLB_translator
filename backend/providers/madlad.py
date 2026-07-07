"""MADLAD-400 engine — local inference via CTranslate2 (int8).

Google's open T5-based MT model covering 400+ languages, generally higher
quality than NLLB. Heavier than NLLB (3B), so it's a local/GPU engine — not the
free-CPU-Space default. Convert it once with:

    HF_MODEL=google/madlad400-3b-mt \\
    CT2_MODEL_DIR=models/madlad400-3b-mt-int8 \\
    python convert_model.py

MADLAD selects the target language via a ``<2xx>`` token prefixed to the input;
the source language is auto-detected.
"""

from __future__ import annotations

import os
from functools import lru_cache
from threading import Lock

from providers.base import TranslationProvider

MODEL_DIR = os.environ.get("MADLAD_MODEL_DIR", "models/madlad400-3b-mt-int8")
HF_MODEL = os.environ.get("MADLAD_HF_MODEL", "google/madlad400-3b-mt")
DEVICE = os.environ.get("CT2_DEVICE", "cpu")
COMPUTE_TYPE = os.environ.get("CT2_COMPUTE_TYPE", "int8")
MAX_DECODING_LENGTH = int(os.environ.get("MAX_DECODING_LENGTH", "256"))

# FLORES-200 code -> MADLAD-400 language code (common subset).
FLORES_TO_MADLAD: dict[str, str] = {
    "eng_Latn": "en", "kor_Hang": "ko", "jpn_Jpan": "ja", "zho_Hans": "zh",
    "zho_Hant": "zh", "yue_Hant": "yue", "spa_Latn": "es", "fra_Latn": "fr",
    "deu_Latn": "de", "rus_Cyrl": "ru", "por_Latn": "pt", "ita_Latn": "it",
    "nld_Latn": "nl", "pol_Latn": "pl", "tur_Latn": "tr", "arb_Arab": "ar",
    "hin_Deva": "hi", "ben_Beng": "bn", "vie_Latn": "vi", "tha_Thai": "th",
    "ind_Latn": "id", "zsm_Latn": "ms", "ukr_Cyrl": "uk", "ces_Latn": "cs",
    "ron_Latn": "ro", "ell_Grek": "el", "heb_Hebr": "iw", "swe_Latn": "sv",
    "dan_Latn": "da", "fin_Latn": "fi", "nob_Latn": "no", "hun_Latn": "hu",
    "bul_Cyrl": "bg", "hrv_Latn": "hr", "srp_Cyrl": "sr", "slk_Latn": "sk",
    "slv_Latn": "sl", "lit_Latn": "lt", "lvs_Latn": "lv", "est_Latn": "et",
    "cat_Latn": "ca", "tgl_Latn": "tl", "pes_Arab": "fa", "urd_Arab": "ur",
    "tam_Taml": "ta", "tel_Telu": "te", "mal_Mlym": "ml", "kan_Knda": "kn",
    "mar_Deva": "mr", "guj_Gujr": "gu", "pan_Guru": "pa", "mya_Mymr": "my",
    "khm_Khmr": "km", "lao_Laoo": "lo", "sin_Sinh": "si", "amh_Ethi": "am",
    "swh_Latn": "sw", "yor_Latn": "yo", "ibo_Latn": "ig", "hau_Latn": "ha",
    "zul_Latn": "zu", "afr_Latn": "af", "isl_Latn": "is", "gle_Latn": "ga",
    "cym_Latn": "cy", "eus_Latn": "eu", "glg_Latn": "gl", "kat_Geor": "ka",
    "hye_Armn": "hy", "azj_Latn": "az", "kaz_Cyrl": "kk", "uzn_Latn": "uz",
    "mkd_Cyrl": "mk", "als_Latn": "sq", "bel_Cyrl": "be", "npi_Deva": "ne",
}


class MADLADProvider(TranslationProvider):
    id = "madlad"
    name = "MADLAD-400 (3B)"
    kind = "local"
    description = "Google's open MT model · 400+ languages · higher quality than NLLB"
    private = True
    setup_hint = "Convert MADLAD locally (see README — heavy, ~3 GB)"

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
    def _translate_line(self, text: str, madlad_tgt: str) -> str:
        prompt = f"<2{madlad_tgt}> {text}"
        source = self._tokenizer.convert_ids_to_tokens(self._tokenizer.encode(prompt))
        results = self._translator.translate_batch(
            [source], beam_size=4, max_decoding_length=MAX_DECODING_LENGTH
        )
        target_tokens = results[0].hypotheses[0]
        return self._tokenizer.decode(
            self._tokenizer.convert_tokens_to_ids(target_tokens)
        )

    def translate(self, text: str, src: str, tgt: str) -> str:
        madlad_tgt = FLORES_TO_MADLAD.get(tgt)
        if madlad_tgt is None:
            raise ValueError(
                "MADLAD engine doesn't support this target language yet — "
                "try NLLB, or pick a more common language."
            )
        self._ensure_loaded()
        out = []
        for line in text.split("\n"):
            out.append(self._translate_line(line, madlad_tgt) if line.strip() else "")
        return "\n".join(out)
