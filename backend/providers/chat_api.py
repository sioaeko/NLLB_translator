"""Shared client for OpenAI-compatible chat endpoints (Groq, OpenAI, OpenRouter)."""

from __future__ import annotations

import json
from collections.abc import Iterator
from threading import Event

import httpx

from providers.base import SYSTEM_PROMPT, clean_output, clean_stream, translation_prompt


def iter_sse_data(response: httpx.Response, cancel: Event | None = None) -> Iterator[str]:
    """Read SSE data fields, checking cancellation before every upstream read."""
    lines = iter(response.iter_lines())
    fields: list[str] = []
    while not (cancel and cancel.is_set()):
        try:
            line = next(lines)
        except StopIteration:
            if fields and not (cancel and cancel.is_set()):
                yield "\n".join(fields)
            return
        if cancel and cancel.is_set():
            return
        if not line:
            if fields:
                yield "\n".join(fields)
                fields = []
        elif line.startswith("data:"):
            value = line[5:]
            fields.append(value[1:] if value.startswith(" ") else value)


def stream_json(data: str, model: str) -> dict:
    try:
        payload = json.loads(data)
    except (ValueError, TypeError) as exc:
        raise RuntimeError(f"Invalid streaming response from {model}.") from exc
    if not isinstance(payload, dict):
        raise RuntimeError(f"Unexpected streaming response from {model}.")
    if payload.get("error"):
        # Provider error bodies can contain submitted text; keep stream errors generic.
        raise RuntimeError(f"{model} returned an error while translating.")
    return payload


def chat_stream_translate(
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
    cancel: Event | None = None,
) -> Iterator[str]:
    """Yield translation deltas from an OpenAI-compatible SSE endpoint."""
    if cancel and cancel.is_set():
        return
    with httpx.stream(
        "POST",
        endpoint,
        headers={"Authorization": f"Bearer {key}", **(headers or {})},
        json={
            "model": model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": translation_prompt(text, src, tgt)},
            ],
            **(extra or {}),
            "stream": True,
        },
        timeout=timeout,
    ) as response:
        if cancel and cancel.is_set():
            return
        if not response.is_success:
            # Streaming responses must be read before callers can inspect .text.
            response.read()
        response.raise_for_status()

        def chunks() -> Iterator[str]:
            done = False
            for data in iter_sse_data(response, cancel):
                if cancel and cancel.is_set():
                    return
                if data.strip() == "[DONE]":
                    done = True
                    break
                payload = stream_json(data, model)
                choices = payload.get("choices")
                if not choices:  # Usage / heartbeat events have no choices.
                    continue
                try:
                    choice = choices[0]
                    reason = choice.get("finish_reason")
                    if reason and reason != "stop":
                        raise RuntimeError(f"{model} could not finish the translation ({reason}).")
                    content = (choice.get("delta") or {}).get("content")
                except (KeyError, IndexError, AttributeError, TypeError) as exc:
                    raise RuntimeError(f"Unexpected streaming response from {model}.") from exc
                if content is not None and not isinstance(content, str):
                    raise RuntimeError(f"Unexpected streaming response from {model}.")
                if content:
                    yield content
            if not done and not (cancel and cancel.is_set()):
                raise RuntimeError(f"{model} disconnected before completing the translation.")

        emitted = False
        for delta in clean_stream(chunks()):
            if cancel and cancel.is_set():
                return
            emitted = True
            yield delta
        if not emitted and not (cancel and cancel.is_set()):
            raise RuntimeError(f"{model} returned no translation text.")


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
