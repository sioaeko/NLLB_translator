"""Common interface every translation engine implements.

A *provider* is one translation engine — a local model (NLLB, MADLAD…) or a
free-tier cloud API (Gemini, Groq…). The registry exposes whichever ones are
actually usable in the current deployment: a local engine is available when its
model files exist; an API engine is available when its API key is configured.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ProviderInfo:
    id: str
    name: str
    kind: str  # "local" | "api"
    description: str
    available: bool
    private: bool  # True if text never leaves the machine
    setup_hint: str  # what to do when unavailable


class TranslationProvider:
    id: str = ""
    name: str = ""
    kind: str = "local"
    description: str = ""
    private: bool = False
    setup_hint: str = ""

    def is_available(self) -> bool:
        raise NotImplementedError

    def translate(self, text: str, src: str, tgt: str) -> str:
        raise NotImplementedError

    def display_name(self) -> str:
        """Overridable so engines like Ollama can reflect the active model."""
        return self.name

    def info(self) -> ProviderInfo:
        return ProviderInfo(
            id=self.id,
            name=self.display_name(),
            kind=self.kind,
            description=self.description,
            available=self.is_available(),
            private=self.private,
            setup_hint=self.setup_hint,
        )
