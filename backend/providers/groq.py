"""Groq engine — free API tier, ultra-fast LPU inference.

Serves open LLMs (Llama, Qwen…) via an OpenAI-compatible endpoint. Available
whenever ``GROQ_API_KEY`` is set. Text is sent to Groq, so not private.
"""

from __future__ import annotations

import os

import httpx

from languages import name_for
from providers.base import TranslationProvider

MODEL = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
ENDPOINT = "https://api.groq.com/openai/v1/chat/completions"


class GroqProvider(TranslationProvider):
    id = "groq"
    name = "Llama 3.3 70B (Groq)"
    kind = "api"
    description = "Open LLM on Groq · free API tier · very fast"
    private = False
    setup_hint = "Set GROQ_API_KEY (free at console.groq.com/keys)"

    def is_available(self) -> bool:
        return bool(os.environ.get("GROQ_API_KEY"))

    def translate(self, text: str, src: str, tgt: str) -> str:
        key = os.environ["GROQ_API_KEY"]
        resp = httpx.post(
            ENDPOINT,
            headers={"Authorization": f"Bearer {key}"},
            json={
                "model": MODEL,
                "temperature": 0.2,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a translation engine. Output only the "
                        "translation of the user's text, with no notes or quotes.",
                    },
                    {
                        "role": "user",
                        "content": f"Translate from {name_for(src)} to "
                        f"{name_for(tgt)}:\n\n{text}",
                    },
                ],
            },
            timeout=30.0,
        )
        resp.raise_for_status()
        data = resp.json()
        try:
            return data["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError) as exc:
            raise RuntimeError(f"Unexpected Groq response: {data}") from exc
