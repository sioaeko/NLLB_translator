"""FastAPI service — multi-engine NLLB / Gemini / Groq translator.

Exposes the translation API and, when a built frontend is present (``static/``),
serves it too so the whole app can run as a single HuggingFace Space.
"""

from __future__ import annotations

import os

import httpx
from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

import providers
from languages import as_list

app = FastAPI(
    title="NLLB Translator API",
    description="Multi-engine neural translation: local NLLB-200 plus free "
    "cloud APIs (Gemini, Groq).",
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
) -> TranslateResponse:
    if not req.text.strip():
        return TranslateResponse(
            translation="", source=req.source, target=req.target, engine=req.engine or ""
        )
    if len(req.text) > MAX_INPUT_CHARS:
        raise HTTPException(400, f"Input too long (max {MAX_INPUT_CHARS} chars).")

    engine_id = req.engine or providers.default_id()
    if not engine_id:
        raise HTTPException(503, "No translation engine is configured.")
    provider = providers.get(engine_id)
    if provider is None:
        raise HTTPException(400, f"Unknown engine: {engine_id!r}")

    # Client-supplied key (bring-your-own-key) for API engines.
    client_keys = {"gemini": x_gemini_key, "groq": x_groq_key}
    api_key = client_keys.get(provider.key_field) if provider.key_field else None

    if provider.kind == "api":
        if not (provider.is_available() or api_key):
            raise HTTPException(503, provider.setup_hint or "Add an API key in Settings.")
    elif not provider.is_available():
        raise HTTPException(503, provider.setup_hint or f"Engine '{engine_id}' is not available.")

    try:
        result = provider.translate(req.text, req.source, req.target, api_key=api_key)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except httpx.HTTPStatusError as exc:
        raise HTTPException(502, f"Upstream API error: {exc.response.status_code}") from exc
    except Exception as exc:  # noqa: BLE001 — surface engine errors to the client
        raise HTTPException(500, f"Translation failed: {exc}") from exc

    return TranslateResponse(
        translation=result, source=req.source, target=req.target, engine=engine_id
    )


# Serve the built frontend if it was copied in (single-container deployment).
_static_dir = os.environ.get("STATIC_DIR", "static")
if os.path.isdir(_static_dir):
    app.mount("/", StaticFiles(directory=_static_dir, html=True), name="static")
