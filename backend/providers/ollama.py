"""Ollama engine — any local LLM, fully offline.

Separate engines for TranslateGemma 4B, Qwen3.5 2B, and Qwen3 1.7B. Each can
use a different Ollama tag via its environment override. Pull selected tags
first with ``ollama pull <model>`` when running outside the Space image.

Available when the configured model is installed on the Ollama server. Text never leaves the
machine, so this engine is private.
"""

from __future__ import annotations

import os
import json
from collections import OrderedDict
from threading import Event, Lock

import httpx

from ollama_service import model_present
from ollama_models import OllamaModel, configured_models
from inference_runtime import check_cancelled, local_inference
from languages import bcp47, name_for
from providers.base import SYSTEM_PROMPT, TranslationProvider, clean_output, clean_stream, translation_prompt

HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
if "://" not in HOST:
    HOST = "http://" + HOST
CONTEXT_LENGTH = int(os.environ.get("OLLAMA_CONTEXT_LENGTH", "4096"))
NUM_THREADS = int(os.environ.get("OLLAMA_TRANSLATE_THREADS", "0"))


def _messages(model: str, text: str, src: str, tgt: str) -> list[dict]:
    if "translategemma" in model:
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
    description = "Google TranslateGemma · local Ollama inference"
    private = True

    def __init__(self, config: OllamaModel | None = None):
        config = config or configured_models()[0]
        self.id = config.id
        self.model = config.model
        self.name = config.name
        self.description = config.description
        self.setup_hint = f"Install Ollama and `ollama pull {self.model}`"
        self._cache: OrderedDict[tuple[str, str, str], str] = OrderedDict()
        self._cache_lock = Lock()

    def _cached(self, key):
        with self._cache_lock:
            value = self._cache.get(key)
            if value is not None:
                self._cache.move_to_end(key)
            return value

    def _remember(self, key, value):
        with self._cache_lock:
            self._cache[key] = value
            self._cache.move_to_end(key)
            while len(self._cache) > 256:
                self._cache.popitem(last=False)

    def display_name(self) -> str:
        if self.model.startswith("translategemma"):
            size = self.model.split(":", 1)[1].upper() if ":" in self.model else "4B"
            return f"TranslateGemma {size} (Ollama)"
        names = {"qwen3.5:2b-q4_K_M": "Qwen3.5 2B", "qwen3:1.7b": "Qwen3 1.7B"}
        return f"{names.get(self.model, self.model)} (Ollama)"

    def is_available(self) -> bool:
        try:
            resp = httpx.get(f"{HOST}/api/tags", timeout=0.4)
            return resp.status_code == 200 and model_present(resp.json(), self.model)
        except (httpx.HTTPError, ValueError, TypeError, AttributeError):
            return False

    def translate(self, text, src, tgt, api_key=None, model=None) -> str:
        return self._translate(text, src, tgt)

    def _payload(self, text, src, tgt, *, stream):
        options = {"temperature": 0.2, "num_ctx": CONTEXT_LENGTH}
        if NUM_THREADS > 0:
            options["num_thread"] = NUM_THREADS
        payload = {
            "model": self.model,
            "stream": stream,
            "options": options,
            "messages": _messages(self.model, text, src, tgt),
        }
        # Qwen thinking consumes scarce CPU and may loop on small models.
        if self.model.split(":", 1)[0] in {"qwen3", "qwen3.5"}:
            payload["think"] = False
        return payload

    def _translate(self, text: str, src: str, tgt: str) -> str:
        key = (text, src, tgt)
        cached = self._cached(key)
        if cached is not None:
            return cached
        with local_inference():
            cached = self._cached(key)
            if cached is not None:
                return cached
            resp = httpx.post(f"{HOST}/api/chat", json=self._payload(text, src, tgt, stream=False), timeout=120.0)
            resp.raise_for_status()
            data = resp.json()
            if data.get("done_reason") == "length":
                raise RuntimeError("Translation reached the model limit. Try a shorter text.")
            result = clean_output(data["message"]["content"])
            if not result:
                raise RuntimeError("Ollama returned no translation.")
            self._remember(key, result)
            return result

    def stream_translate(self, text, src, tgt, api_key=None, model=None, *, cancel: Event | None = None):
        key = (text, src, tgt)
        check_cancelled(cancel)
        cached = self._cached(key)
        if cached is not None:
            yield cached
            return
        with local_inference(cancel):
            cached = self._cached(key)
            if cached is not None:
                yield cached
                return

            def chunks():
                with httpx.stream("POST", f"{HOST}/api/chat", json=self._payload(text, src, tgt, stream=True), timeout=120.0) as resp:
                    if resp.is_error:
                        resp.read()
                    resp.raise_for_status()
                    for line in resp.iter_lines():
                        check_cancelled(cancel)
                        if not line.strip():
                            continue
                        data = json.loads(line)
                        if data.get("error"):
                            raise RuntimeError(str(data["error"]))
                        content = data.get("message", {}).get("content", "")
                        if content:
                            yield content
                        if data.get("done"):
                            if data.get("done_reason") == "length":
                                raise RuntimeError("Translation reached the model limit. Try a shorter text.")
                            return
                    raise RuntimeError("Ollama interrupted the translation before it finished.")

            result = []
            stream = clean_stream(chunks())
            try:
                for piece in stream:
                    check_cancelled(cancel)
                    result.append(piece)
                    yield piece
            finally:
                stream.close()
            check_cancelled(cancel)
            translation = "".join(result)
            if not translation:
                raise RuntimeError("Ollama returned no translation.")
            self._remember(key, translation)
