"""Shared Ollama catalog for API routing and container model preparation."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class OllamaModel:
    id: str
    model: str
    name: str
    description: str


def configured_models() -> tuple[OllamaModel, ...]:
    return (
        OllamaModel(
            "ollama", os.environ.get("OLLAMA_MODEL", "translategemma:4b"),
            "TranslateGemma 4B", "Google TranslateGemma · local Ollama inference",
        ),
        OllamaModel(
            "ollama_qwen35", os.environ.get("OLLAMA_QWEN35_MODEL", "qwen3.5:2b-q4_K_M"),
            "Qwen3.5 2B", "Alibaba · compact multilingual model · runs on this server",
        ),
        OllamaModel(
            "ollama_qwen3", os.environ.get("OLLAMA_QWEN3_MODEL", "qwen3:1.7b"),
            "Qwen3 1.7B", "Alibaba · smaller multilingual model · runs on this server",
        ),
    )
