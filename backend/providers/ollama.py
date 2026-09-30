"""Ollama engine — any local LLM, fully offline.

Defaults to Google's TranslateGemma 4B (2026, 55 languages), a model built for
translation; any other Ollama model works too via ``OLLAMA_MODEL``. Pull it
first with ``ollama pull <model>``.

Available whenever a local Ollama server is reachable. Text never leaves the
machine, so this engine is private.
"""

from __future__ import annotations

import os

import httpx

from languages import bcp47, name_for
from providers.base import SYSTEM_PROMPT, TranslationProvider, clean_output, translation_prompt

HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
MODEL = os.environ.get("OLLAMA_MODEL", "translategemma:4b")


def _messages(text: str, src: str, tgt: str) -> list[dict]:
    if "translategemma" in MODEL:
        # TranslateGemma's documented prompt format.
        s, t = name_for(src), name_for(tgt)
        prompt = (
            f"You are a professional {s} ({bcp47(src)}) to {t} ({bcp47(tgt)}) translator. "
            f"Your goal is to accurately convey the meaning and nuances of the original {s} "
            f"text while adhering to {t} grammar, vocabulary, and cultural sensitivities. "
            f"Produce only the {t} translation, without any additional explanations or "
            f"commentary. Please translate the following {s} text into {t}:\n\n\n{text}"
        )
        return [{"role": "user", "content": prompt}]
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": translation_prompt(text, src, tgt)},
    ]


class OllamaProvider(TranslationProvider):
    id = "ollama"
    name = "Local LLM (Ollama)"
    kind = "local"
    description = "TranslateGemma or any model on your Ollama"
    private = True
    setup_hint = "Install Ollama and `ollama pull " + MODEL + "`"

    def display_name(self) -> str:
        if MODEL.startswith("translategemma"):
            size = MODEL.split(":", 1)[1].upper() if ":" in MODEL else "4B"
            return f"TranslateGemma {size} (Ollama)"
        return f"{MODEL} (Ollama)"

    def is_available(self) -> bool:
        try:
            resp = httpx.get(f"{HOST}/api/tags", timeout=0.4)
            return resp.status_code == 200
        except httpx.HTTPError:
            return False

    def translate(self, text, src, tgt, api_key=None, model=None) -> str:
        resp = httpx.post(
            f"{HOST}/api/chat",
            json={
                "model": MODEL,
                "stream": False,
                "options": {"temperature": 0.2},
                "messages": _messages(text, src, tgt),
            },
            timeout=120.0,
        )
        resp.raise_for_status()
        return clean_output(resp.json()["message"]["content"])
