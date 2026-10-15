"""Common interface every translation engine implements.

A *provider* is one translation engine — a local model (NLLB, Hy-MT2…) or a
cloud API (Gemini, Groq, OpenAI, OpenRouter…). The registry exposes whichever
ones are actually usable: a local engine is available when its model files
exist; an API engine is available when its API key is configured (server env)
OR supplied by the client per-request (bring-your-own-key).
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from dataclasses import dataclass
from threading import Event

from languages import name_for


@dataclass
class ProviderInfo:
    id: str
    name: str
    kind: str  # "local" | "api"
    description: str
    available: bool  # ready from server-side config (env key / local model)
    private: bool  # True if text never leaves the machine
    setup_hint: str  # what to do when unavailable
    key_field: str  # which client key unlocks it ("gemini", "groq"…); "" for local


# Shared prompt for general-purpose LLM engines.
SYSTEM_PROMPT = (
    "You are a translation engine. Translate the user's text faithfully and "
    "naturally. Output only the translation, with no notes, quotes, or "
    "explanations. Preserve line breaks."
)


def translation_prompt(text: str, src: str, tgt: str) -> str:
    return f"Translate from {name_for(src)} to {name_for(tgt)}:\n\n{text}"


_THINK = re.compile(r"<think>.*?</think>", re.S)


def clean_output(text: str) -> str:
    """Drop inline reasoning blocks some LLMs emit, plus surrounding whitespace."""
    return _THINK.sub("", text).strip()


def clean_stream(chunks: Iterator[str]) -> Iterator[str]:
    """Hide reasoning even across chunk boundaries, and trim outer whitespace."""
    buffer = ""
    thinking = False
    started = False
    whitespace = ""

    def visible(text: str) -> str:
        nonlocal started, whitespace
        if not started:
            text = text.lstrip()
        text = whitespace + text
        body = text.rstrip()
        whitespace = text[len(body):]
        if body:
            started = True
        return body

    try:
        for chunk in chunks:
            buffer += chunk
            while buffer:
                marker = "</think>" if thinking else "<think>"
                index = buffer.find(marker)
                if index >= 0:
                    if not thinking:
                        text = visible(buffer[:index])
                        if text:
                            yield text
                    buffer = buffer[index + len(marker):]
                    thinking = not thinking
                    continue
                keep = next((n for n in range(min(len(marker) - 1, len(buffer)), 0, -1)
                             if buffer.endswith(marker[:n])), 0)
                safe = buffer[:-keep] if keep else buffer
                buffer = buffer[-keep:] if keep else ""
                if not thinking:
                    text = visible(safe)
                    if text:
                        yield text
                break
        if not thinking:
            text = visible(buffer)
            if text:
                yield text
    finally:
        close = getattr(chunks, "close", None)
        if close is not None:
            close()


class TranslationProvider:
    id: str = ""
    name: str = ""
    kind: str = "local"
    description: str = ""
    private: bool = False
    setup_hint: str = ""
    key_field: str = ""

    def is_available(self) -> bool:
        raise NotImplementedError

    def translate(
        self,
        text: str,
        src: str,
        tgt: str,
        api_key: str | None = None,
        model: str | None = None,
    ) -> str:
        raise NotImplementedError

    def display_name(self) -> str:
        """Overridable so engines like Ollama can reflect the active model."""
        return self.name

    def stream_translate(self, text, src, tgt, api_key=None, model=None, *, cancel: Event | None = None):
        if cancel is not None and cancel.is_set():
            return
        result = self.translate(text, src, tgt, api_key=api_key, model=model)
        if cancel is None or not cancel.is_set():
            yield result

    def info(self) -> ProviderInfo:
        return ProviderInfo(
            id=self.id,
            name=self.display_name(),
            kind=self.kind,
            description=self.description,
            available=self.is_available(),
            private=self.private,
            setup_hint=self.setup_hint,
            key_field=self.key_field,
        )
