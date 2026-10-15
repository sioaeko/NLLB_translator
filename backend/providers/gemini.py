"""Google Gemini engine — free API tier, no self-hosting.

Gemini 3.5 Flash-Lite is on the free tier (no credit card) and strong on Korean
/ CJK. Available whenever ``GEMINI_API_KEY`` is set or the client sends a key.
Text is sent to Google, so this engine is not private.
"""

from __future__ import annotations

import os
from threading import Event

import httpx

from providers.base import SYSTEM_PROMPT, TranslationProvider, clean_output, clean_stream, translation_prompt
from providers.chat_api import iter_sse_data, stream_json

MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash-lite")
ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models"


def _payload(text, src, tgt) -> dict:
    return {
        "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": [{"role": "user", "parts": [{"text": translation_prompt(text, src, tgt)}]}],
        # Minimal thinking keeps Flash-Lite at its lowest latency.
        "generationConfig": {"thinkingConfig": {"thinkingLevel": "minimal"}},
    }


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
            json=_payload(text, src, tgt),
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

    def stream_translate(self, text, src, tgt, api_key=None, model=None, cancel: Event | None = None):
        key = api_key or os.environ.get("GEMINI_API_KEY")
        if not key:
            raise ValueError("No Gemini API key provided.")
        if cancel and cancel.is_set():
            return
        with httpx.stream(
            "POST",
            f"{ENDPOINT}/{MODEL}:streamGenerateContent?alt=sse",
            headers={"x-goog-api-key": key},
            json=_payload(text, src, tgt),
            timeout=60.0,
        ) as response:
            if cancel and cancel.is_set():
                return
            if not response.is_success:
                response.read()
            response.raise_for_status()

            def chunks():
                finished = False
                for data in iter_sse_data(response, cancel):
                    if cancel and cancel.is_set():
                        return
                    payload = stream_json(data, "Gemini")
                    feedback = payload.get("promptFeedback") or {}
                    if feedback.get("blockReason"):
                        raise RuntimeError(f"Gemini blocked the translation ({feedback['blockReason']}).")
                    candidates = payload.get("candidates")
                    if not candidates:  # Usage-only events have no candidate.
                        continue
                    try:
                        candidate = candidates[0]
                        reason = candidate.get("finishReason")
                        if reason and reason != "STOP":
                            raise RuntimeError(f"Gemini could not finish the translation ({reason}).")
                        parts = (candidate.get("content") or {}).get("parts") or []
                        for part in parts:
                            if part.get("thought"):
                                continue
                            content = part.get("text")
                            if content is not None and not isinstance(content, str):
                                raise RuntimeError("Unexpected streaming response from Gemini.")
                            if content:
                                yield content
                    except (KeyError, IndexError, AttributeError, TypeError) as exc:
                        raise RuntimeError("Unexpected streaming response from Gemini.") from exc
                    if reason == "STOP":
                        finished = True
                        break
                if not finished and not (cancel and cancel.is_set()):
                    raise RuntimeError("Gemini disconnected before completing the translation.")

            emitted = False
            for delta in clean_stream(chunks()):
                if cancel and cancel.is_set():
                    return
                emitted = True
                yield delta
            if not emitted and not (cancel and cancel.is_set()):
                raise RuntimeError("Gemini returned no translation text.")
