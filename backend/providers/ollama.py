"""Ollama engine — any local LLM, fully offline.

One provider unlocks a whole shelf of open models the user can run locally via
Ollama: Qwen, Gemma / TranslateGemma, Aya, Llama, and more. Set the model with
``OLLAMA_MODEL`` (default ``qwen2.5``); pull it first with ``ollama pull <model>``.

Available whenever a local Ollama server is reachable. Text never leaves the
machine, so this engine is private.
"""

from __future__ import annotations

import os

import httpx

from languages import name_for
from providers.base import TranslationProvider

HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5")


class OllamaProvider(TranslationProvider):
    id = "ollama"
    name = "Local LLM (Ollama)"
    kind = "local"
    description = "Run Qwen / Gemma / TranslateGemma / Aya locally · offline"
    private = True
    setup_hint = "Install Ollama and `ollama pull " + MODEL + "`"

    def display_name(self) -> str:
        return f"{MODEL} (Ollama)"

    def is_available(self) -> bool:
        try:
            resp = httpx.get(f"{HOST}/api/tags", timeout=0.4)
            return resp.status_code == 200
        except httpx.HTTPError:
            return False

    def translate(self, text: str, src: str, tgt: str, api_key: str | None = None) -> str:
        resp = httpx.post(
            f"{HOST}/api/chat",
            json={
                "model": MODEL,
                "stream": False,
                "options": {"temperature": 0.2},
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
            timeout=120.0,
        )
        resp.raise_for_status()
        return resp.json()["message"]["content"].strip()
