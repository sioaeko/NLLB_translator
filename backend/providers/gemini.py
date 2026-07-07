"""Google Gemini engine — free API tier, no self-hosting.

Uses Gemini's generous free tier (no credit card). Strong on Korean / CJK and
low-resource prose. Available whenever ``GEMINI_API_KEY`` is set. Text is sent to
Google, so this engine is not private.
"""

from __future__ import annotations

import os

import httpx

from languages import name_for
from providers.base import TranslationProvider

MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash-lite")
ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models"


class GeminiProvider(TranslationProvider):
    id = "gemini"
    name = "Gemini 2.5 Flash-Lite"
    kind = "api"
    description = "Google Gemini · free API tier · excellent for Korean/CJK"
    private = False
    setup_hint = "Set GEMINI_API_KEY (free at aistudio.google.com/apikey)"

    def is_available(self) -> bool:
        return bool(os.environ.get("GEMINI_API_KEY"))

    def translate(self, text: str, src: str, tgt: str) -> str:
        key = os.environ["GEMINI_API_KEY"]
        prompt = (
            f"Translate the following text from {name_for(src)} to "
            f"{name_for(tgt)}. Output ONLY the translation, with no notes, "
            f"quotes, or explanations.\n\n{text}"
        )
        url = f"{ENDPOINT}/{MODEL}:generateContent?key={key}"
        resp = httpx.post(
            url,
            json={
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.2},
            },
            timeout=30.0,
        )
        resp.raise_for_status()
        data = resp.json()
        try:
            return data["candidates"][0]["content"]["parts"][0]["text"].strip()
        except (KeyError, IndexError) as exc:
            raise RuntimeError(f"Unexpected Gemini response: {data}") from exc
