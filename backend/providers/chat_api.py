"""Shared client for OpenAI-compatible chat endpoints (Groq, OpenAI, OpenRouter)."""

from __future__ import annotations

import httpx

from providers.base import SYSTEM_PROMPT, clean_output, translation_prompt


def chat_translate(
    endpoint: str,
    key: str,
    model: str,
    text: str,
    src: str,
    tgt: str,
    *,
    extra: dict | None = None,
    headers: dict | None = None,
    timeout: float = 60.0,
) -> str:
    """Translate via a chat-completions endpoint; raises httpx.HTTPStatusError on failure."""
    resp = httpx.post(
        endpoint,
        headers={"Authorization": f"Bearer {key}", **(headers or {})},
        json={
            "model": model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": translation_prompt(text, src, tgt)},
            ],
            **(extra or {}),
        },
        timeout=timeout,
    )
    resp.raise_for_status()
    data = resp.json()
    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError(f"Unexpected response from {model}.") from exc
    return clean_output(content or "")
