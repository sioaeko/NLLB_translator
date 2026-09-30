"""Groq engines — free API tier, very fast inference.

One API key (``GROQ_API_KEY`` or the client's) powers every Groq engine; each
subclass points at a different model. Groq retires models often, sometimes with
no notice, so when a request fails because the model is gone we look up Groq's
live catalogue and switch to the newest model of the same family.
Text is sent to Groq, so these engines are not private.
"""

from __future__ import annotations

import logging
import os
import re

import httpx

from providers.base import TranslationProvider
from providers.chat_api import chat_translate

API = "https://api.groq.com/openai/v1"
log = logging.getLogger(__name__)

# engine id -> replacement model chosen after the configured one disappeared
_resolved: dict[str, str] = {}


def _model_gone(resp: httpx.Response) -> bool:
    if resp.status_code not in (400, 404):
        return False
    body = resp.text.lower()
    return any(s in body for s in ("model_not_found", "model_decommissioned", "decommissioned", "does not exist"))


class _GroqEngine(TranslationProvider):
    kind = "api"
    private = False
    key_field = "groq"
    setup_hint = "Add a Groq key under API keys (free at console.groq.com/keys)"
    model = ""  # preferred model id
    family = ""  # id prefix used to find a successor
    extra: dict = {}

    def is_available(self) -> bool:
        return bool(os.environ.get("GROQ_API_KEY"))

    def _successor(self, key: str) -> str | None:
        resp = httpx.get(f"{API}/models", headers={"Authorization": f"Bearer {key}"}, timeout=15.0)
        resp.raise_for_status()
        ids = [m["id"] for m in resp.json().get("data", []) if m.get("active", True)]
        candidates = [i for i in ids if i.startswith(self.family) and "guard" not in i]
        if not candidates:
            return None
        # Highest version / size wins, e.g. qwen3.8-27b over qwen3.6-27b.
        return max(candidates, key=lambda i: [float(n) for n in re.findall(r"\d+(?:\.\d+)?", i)])

    def translate(self, text, src, tgt, api_key=None, model=None) -> str:
        key = api_key or os.environ.get("GROQ_API_KEY")
        if not key:
            raise ValueError("No Groq API key provided.")
        current = _resolved.get(self.id, self.model)
        endpoint = f"{API}/chat/completions"
        try:
            return chat_translate(endpoint, key, current, text, src, tgt, extra=self.extra)
        except httpx.HTTPStatusError as exc:
            if not _model_gone(exc.response):
                raise
            successor = self._successor(key)
            if not successor or successor == current:
                raise
            log.warning("Groq model %s is gone; switching %s to %s", current, self.id, successor)
            _resolved[self.id] = successor
            return chat_translate(endpoint, key, successor, text, src, tgt, extra=self.extra)


class GroqQwenProvider(_GroqEngine):
    id = "groq_qwen"
    name = "Qwen 3.8 27B (Groq)"
    description = "Alibaba · free on Groq · strong on CJK"
    model = os.environ.get("GROQ_QWEN_MODEL", "qwen/qwen3.8-27b")
    family = "qwen/"
    extra = {"temperature": 0.3}  # thinking is off by default on this model


class GroqGptOssProvider(_GroqEngine):
    id = "groq_gptoss"
    name = "GPT-OSS 120B (Groq)"
    description = "OpenAI open-weight · free on Groq · very fast"
    model = os.environ.get("GROQ_GPTOSS_MODEL", "openai/gpt-oss-120b")
    family = "openai/gpt-oss"
    extra = {"reasoning_effort": "low"}  # reasoning comes back in a separate field
