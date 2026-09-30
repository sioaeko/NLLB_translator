"""OpenAI engine — GPT-6 Luna, OpenAI's low-cost model (bring your own key).

$0.10 / $0.50 per 1M input / output tokens, so a typical sentence costs a
small fraction of a cent. Reasoning is switched off: translation doesn't need
it, and it keeps latency and cost at their lowest. Not private.
"""

from __future__ import annotations

import os

from providers.base import TranslationProvider
from providers.chat_api import chat_translate

ENDPOINT = "https://api.openai.com/v1/chat/completions"
MODEL = os.environ.get("OPENAI_MODEL", "gpt-6-luna")
_PRETTY = {"gpt-6-luna": "GPT-6 Luna", "gpt-5.6-luna": "GPT-5.6 Luna"}


class OpenAIProvider(TranslationProvider):
    id = "openai"
    name = "GPT-6 Luna"
    kind = "api"
    description = "OpenAI · $0.10 / $0.50 per 1M tokens"
    private = False
    key_field = "openai"
    setup_hint = "Add an OpenAI key under API keys (platform.openai.com/api-keys)"

    def display_name(self) -> str:
        return _PRETTY.get(MODEL, MODEL)

    def is_available(self) -> bool:
        return bool(os.environ.get("OPENAI_API_KEY"))

    def translate(self, text, src, tgt, api_key=None, model=None) -> str:
        key = api_key or os.environ.get("OPENAI_API_KEY")
        if not key:
            raise ValueError("No OpenAI API key provided.")
        return chat_translate(ENDPOINT, key, MODEL, text, src, tgt, extra={"reasoning_effort": "none"})
