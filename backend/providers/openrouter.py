"""OpenRouter engine — one key, hundreds of models (several free).

The client picks the model per request (``X-OpenRouter-Model``); by default we
use a free, strongly multilingual model. Not private.
"""

from __future__ import annotations

import os
import re

from providers.base import TranslationProvider
from providers.chat_api import chat_translate

ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = os.environ.get("OPENROUTER_MODEL", "google/gemma-4-31b-it:free")
APP_URL = os.environ.get("APP_URL", "https://github.com/sioaeko/NLLB_translator")
_SLUG = re.compile(r"^[A-Za-z0-9._-]+/[A-Za-z0-9._:-]+$")


class OpenRouterProvider(TranslationProvider):
    id = "openrouter"
    name = "OpenRouter"
    kind = "api"
    description = f"Using {DEFAULT_MODEL}"
    private = False
    key_field = "openrouter"
    setup_hint = "Add an OpenRouter key under API keys (openrouter.ai/keys)"

    def is_available(self) -> bool:
        return bool(os.environ.get("OPENROUTER_API_KEY"))

    def translate(self, text, src, tgt, api_key=None, model=None) -> str:
        key = api_key or os.environ.get("OPENROUTER_API_KEY")
        if not key:
            raise ValueError("No OpenRouter API key provided.")
        slug = (model or DEFAULT_MODEL).strip()
        if not _SLUG.match(slug):
            raise ValueError(f"Not a valid OpenRouter model id: {slug!r}")
        return chat_translate(
            ENDPOINT,
            key,
            slug,
            text,
            src,
            tgt,
            headers={"HTTP-Referer": APP_URL, "X-Title": "NLLB Translator"},
            extra={"temperature": 0.3},
        )
