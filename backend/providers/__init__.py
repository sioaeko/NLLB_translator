"""Registry of translation engines.

Add a new engine by implementing ``TranslationProvider`` and appending an
instance to ``_PROVIDERS`` below. The API automatically exposes whichever ones
report themselves available.
"""

from __future__ import annotations

from providers.base import ProviderInfo, TranslationProvider
from providers.gemini import GeminiProvider
from providers.groq import GroqProvider, GroqQwenProvider
from providers.madlad import MADLADProvider
from providers.nllb import NLLBProvider
from providers.ollama import OllamaProvider

# Order = display order in the UI. Local/private engines first.
_PROVIDERS: list[TranslationProvider] = [
    NLLBProvider(),
    MADLADProvider(),
    OllamaProvider(),
    GeminiProvider(),
    GroqQwenProvider(),
    GroqProvider(),
]

_BY_ID = {p.id: p for p in _PROVIDERS}


def all_infos() -> list[ProviderInfo]:
    return [p.info() for p in _PROVIDERS]


def available_infos() -> list[ProviderInfo]:
    return [p.info() for p in _PROVIDERS if p.is_available()]


def get(provider_id: str) -> TranslationProvider | None:
    return _BY_ID.get(provider_id)


def default_id() -> str | None:
    """First available engine, preferring local/private ones."""
    for p in _PROVIDERS:
        if p.is_available():
            return p.id
    return None
