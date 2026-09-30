"""Google Gemini engine — free API tier, no self-hosting.

Gemini 3.5 Flash-Lite is on the free tier (no credit card) and strong on Korean
/ CJK. Available whenever ``GEMINI_API_KEY`` is set or the client sends a key.
Text is sent to Google, so this engine is not private.
"""

from __future__ import annotations

import os

import httpx

from providers.base import SYSTEM_PROMPT, TranslationProvider, clean_output, translation_prompt

MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash-lite")
ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models"


class GeminiProvider(TranslationProvider):
    id = "gemini"
    name = "Gemini 3.5 Flash-Lite"
    kind = "api"
    description = "Google · free API tier · strong on Korean & CJK"
    private = False
    key_field = "gemini"
    setup_hint = "Add a Gemini key under API keys (free at aistudio.google.com/apikey)"

    def is_available(self) -> bool:
        return bool(os.environ.get("GEMINI_API_KEY"))

    def translate(self, text, src, tgt, api_key=None, model=None) -> str:
        key = api_key or os.environ.get("GEMINI_API_KEY")
        if not key:
            raise ValueError("No Gemini API key provided.")
        resp = httpx.post(
            f"{ENDPOINT}/{MODEL}:generateContent",
            # Header, not ?key=, so the key never lands in URLs or access logs.
            headers={"x-goog-api-key": key},
            json={
                "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
                "contents": [{"role": "user", "parts": [{"text": translation_prompt(text, src, tgt)}]}],
                # Minimal thinking keeps Flash-Lite at its lowest latency.
                "generationConfig": {"thinkingConfig": {"thinkingLevel": "minimal"}},
            },
            timeout=60.0,
        )
        resp.raise_for_status()
        data = resp.json()
        try:
            parts = data["candidates"][0]["content"]["parts"]
        except (KeyError, IndexError, TypeError) as exc:
            reason = (data.get("promptFeedback") or {}).get("blockReason") or (
                (data.get("candidates") or [{}])[0].get("finishReason")
            )
            raise RuntimeError(f"Gemini returned no text{f' ({reason})' if reason else ''}.") from exc
        return clean_output("".join(p.get("text", "") for p in parts if not p.get("thought")))
