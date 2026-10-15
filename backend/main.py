"""FastAPI service — multi-engine translator (local models + cloud APIs).

Exposes the translation API and, when a built frontend is present (``static/``),
serves it too so the whole app can run as a single HuggingFace Space.
"""

from __future__ import annotations

import os
import json
from queue import Empty, Full, Queue
from threading import Event, Thread

import anyio
import httpx
from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

import providers
from languages import as_list, is_valid

app = FastAPI(
    title="NLLB Translator API",
    description="Multi-engine translation: local NLLB-200 and Hy-MT2, plus cloud "
    "APIs (Gemini, Groq, OpenAI, OpenRouter) with bring-your-own-key.",
    version="2.0.0",
)

_origins = os.environ.get("CORS_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _origins],
    allow_methods=["*"],
    allow_headers=["*"],
)

MAX_INPUT_CHARS = int(os.environ.get("MAX_INPUT_CHARS", "5000"))

_PROVIDER_NAMES = {"gemini": "Gemini", "groq": "Groq", "openai": "OpenAI", "openrouter": "OpenRouter"}


def _upstream_message(key_field: str, resp: httpx.Response) -> str:
    """Turn a provider's HTTP error into something a user can act on."""
    who = _PROVIDER_NAMES.get(key_field, "The provider")
    code = resp.status_code
    if code in (401, 403):
        return f"{who} rejected the API key ({code}). Check it under API keys."
    if code == 429:
        return f"{who} rate limit reached. Wait a moment and try again."
    try:
        body = resp.json()
        err = body.get("error", body) if isinstance(body, dict) else body
        detail = err.get("message", "") if isinstance(err, dict) else str(err)
    except ValueError:
        detail = resp.text
    detail = " ".join((detail or "").split())[:200]
    return f"{who} returned an error ({code})" + (f": {detail}" if detail else ".")


class TranslateRequest(BaseModel):
    text: str = Field(..., description="Text to translate.")
    source: str = Field(..., description="Source FLORES-200 code, e.g. 'eng_Latn'.")
    target: str = Field(..., description="Target FLORES-200 code, e.g. 'kor_Hang'.")
    engine: str | None = Field(None, description="Engine id; defaults to first available.")


class TranslateResponse(BaseModel):
    translation: str
    source: str
    target: str
    engine: str


def _resolve(req: TranslateRequest, client_keys: dict, model: str | None):
    if len(req.text) > MAX_INPUT_CHARS:
        raise HTTPException(400, f"Input too long (max {MAX_INPUT_CHARS} chars).")
    if not is_valid(req.source) or not is_valid(req.target):
        raise HTTPException(400, "Unknown language code.")
    engine_id = req.engine or providers.default_id()
    if not engine_id:
        raise HTTPException(503, "No translation engine is configured.")
    provider = providers.get(engine_id)
    if provider is None:
        raise HTTPException(400, f"Unknown engine: {engine_id!r}")
    key = client_keys.get(provider.key_field) if provider.key_field else None
    if req.source != req.target:
        if provider.kind == "api":
            if not (provider.is_available() or key):
                raise HTTPException(503, provider.setup_hint or "Add an API key in Settings.")
        elif not provider.is_available():
            raise HTTPException(503, provider.setup_hint or f"Engine '{engine_id}' is not available.")
    return provider, key, model if provider.key_field == "openrouter" else None


def _translation_error(exc: Exception, provider) -> HTTPException:
    if isinstance(exc, ValueError):
        return HTTPException(400, str(exc))
    if isinstance(exc, httpx.HTTPStatusError):
        return HTTPException(502, _upstream_message(provider.key_field, exc.response))
    if isinstance(exc, httpx.TimeoutException):
        return HTTPException(504, "The engine took too long to answer. Try again.")
    return HTTPException(500, f"Translation failed: {exc}")


def _packet(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False) + "\n"


class TranslationStreamingResponse(StreamingResponse):
    async def __call__(self, scope, receive, send):
        try:
            await super().__call__(scope, receive, send)
        finally:
            # Disconnect can cancel send() while the iterator is suspended at a
            # yield. Close it explicitly so cancellation reaches the CPU worker.
            close = getattr(self.body_iterator, "aclose", None)
            if close is not None:
                with anyio.CancelScope(shield=True):
                    await close()


async def _stream_response(req, provider, api_key, model):
    """A bounded bridge keeps CPU/HTTP work off the event loop and cancels on disconnect."""
    cancel = Event()
    messages = Queue(maxsize=8)

    def send(data):
        while not cancel.is_set():
            try:
                messages.put(data, timeout=0.1)
                return
            except Full:
                pass
        raise InterruptedError("Translation cancelled.")

    def produce():
        stream = None
        try:
            parts = []
            if req.source == req.target:
                stream = iter([req.text])
            else:
                stream = provider.stream_translate(req.text, req.source, req.target,
                                                   api_key=api_key, model=model, cancel=cancel)
            for piece in stream:
                if cancel.is_set():
                    raise InterruptedError("Translation cancelled.")
                parts.append(piece)
                if piece:
                    send({"type": "delta", "text": piece})
            send({"type": "done", "translation": "".join(parts), "source": req.source,
                  "target": req.target, "engine": provider.id})
        except InterruptedError:
            if not cancel.is_set():
                send({"type": "error", "detail": "Translation was interrupted. Try again.", "status": 503})
        except Exception as exc:
            error = _translation_error(exc, provider)
            if not cancel.is_set():
                try:
                    send({"type": "error", "detail": error.detail, "status": error.status_code})
                except InterruptedError:
                    pass
        finally:
            close = getattr(stream, "close", None)
            if close is not None:
                close()

    def receive():
        try:
            return messages.get(timeout=0.2)
        except Empty:
            return None

    worker = Thread(target=produce, name="translation-stream", daemon=True)
    worker.start()
    try:
        while True:
            message = await anyio.to_thread.run_sync(receive)
            if message is None:
                if not worker.is_alive():
                    # The worker may have queued its last event after receive()
                    # timed out and before this liveness check.
                    try:
                        message = messages.get_nowait()
                    except Empty:
                        yield _packet({"type": "error", "detail": "Translation stopped before completion.", "status": 500})
                        break
                else:
                    continue
            yield _packet(message)
            if message["type"] in {"done", "error"}:
                break
    finally:
        cancel.set()


@app.post("/api/translate/stream")
def translate_stream_endpoint(
    req: TranslateRequest,
    x_gemini_key: str | None = Header(default=None),
    x_groq_key: str | None = Header(default=None),
    x_openai_key: str | None = Header(default=None),
    x_openrouter_key: str | None = Header(default=None),
    x_openrouter_model: str | None = Header(default=None),
):
    if not req.text.strip():
        stream = iter([_packet({"type": "done", "translation": "", "source": req.source,
                               "target": req.target, "engine": req.engine or ""})])
    else:
        provider, key, model = _resolve(req, {"gemini": x_gemini_key, "groq": x_groq_key,
                                            "openai": x_openai_key, "openrouter": x_openrouter_key},
                                        x_openrouter_model)
        stream = _stream_response(req, provider, key, model)
    return TranslationStreamingResponse(stream, media_type="application/x-ndjson",
                             headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"})


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "default_engine": providers.default_id()}


@app.get("/api/engines")
def engines() -> dict:
    return {
        "engines": [vars(i) for i in providers.all_infos()],
        "default": providers.default_id(),
    }


@app.get("/api/languages")
def languages() -> dict:
    return {"languages": as_list()}


@app.post("/api/translate", response_model=TranslateResponse)
def translate_endpoint(
    req: TranslateRequest,
    x_gemini_key: str | None = Header(default=None),
    x_groq_key: str | None = Header(default=None),
    x_openai_key: str | None = Header(default=None),
    x_openrouter_key: str | None = Header(default=None),
    x_openrouter_model: str | None = Header(default=None),
) -> TranslateResponse:
    if not req.text.strip():
        return TranslateResponse(
            translation="", source=req.source, target=req.target, engine=req.engine or ""
        )
    # Client-supplied key (bring-your-own-key) for API engines.
    client_keys = {
        "gemini": x_gemini_key,
        "groq": x_groq_key,
        "openai": x_openai_key,
        "openrouter": x_openrouter_key,
    }
    provider, api_key, model = _resolve(req, client_keys, x_openrouter_model)

    try:
        result = req.text if req.source == req.target else provider.translate(req.text, req.source, req.target, api_key=api_key, model=model)
    except Exception as exc:  # noqa: BLE001 — surface engine errors to the client
        raise _translation_error(exc, provider) from exc

    return TranslateResponse(
        translation=result, source=req.source, target=req.target, engine=provider.id
    )


# Serve the built frontend if it was copied in (single-container deployment).
_static_dir = os.environ.get("STATIC_DIR", "static")
if os.path.isdir(_static_dir):
    app.mount("/", StaticFiles(directory=_static_dir, html=True), name="static")
