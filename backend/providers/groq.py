"""Groq engine(s) — free API tier, ultra-fast LPU inference.

Serves open LLMs via an OpenAI-compatible endpoint. One API key (`GROQ_API_KEY`)
powers every Groq engine; each subclass just points at a different model.
Text is sent to Groq, so these engines are not private.
"""

from __future__ import annotations

import os

import httpx

from languages import name_for
from providers.base import TranslationProvider

ENDPOINT = "https://api.groq.com/openai/v1/chat/completions"


class _GroqEngine(TranslationProvider):
    kind = "api"
    private = False
    setup_hint = "Set GROQ_API_KEY (free at console.groq.com/keys)"
    model = ""  # subclass sets this

    def is_available(self) -> bool:
        return bool(os.environ.get("GROQ_API_KEY"))

    def translate(self, text: str, src: str, tgt: str) -> str:
        key = os.environ["GROQ_API_KEY"]
        resp = httpx.post(
            ENDPOINT,
            headers={"Authorization": f"Bearer {key}"},
            json={
                "model": self.model,
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


class GroqProvider(_GroqEngine):
    id = "groq"
    name = "Llama 3.3 70B (Groq)"
    description = "Open LLM on Groq · free API tier · very fast"
    model = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")


class GroqQwenProvider(_GroqEngine):
    id = "groq_qwen"
    name = "Qwen 2.5 32B (Groq)"
    description = "Alibaba Qwen 2.5 on Groq · free API · strong CJK/Korean"
    model = os.environ.get("GROQ_QWEN_MODEL", "qwen-2.5-32b")
