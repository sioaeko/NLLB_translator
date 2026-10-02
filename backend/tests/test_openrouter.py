import unittest
from unittest.mock import patch

from providers.openrouter import OpenRouterProvider


class OpenRouterTests(unittest.TestCase):
    def test_nemotron_translation_disables_reasoning(self):
        with patch("providers.openrouter.chat_translate", return_value="translated") as chat:
            OpenRouterProvider().translate(
                "Hello", "eng_Latn", "kor_Hang", api_key="test-key",
                model="nvidia/nemotron-3.5-lightning:free",
            )
            self.assertEqual(chat.call_args.kwargs["extra"]["reasoning"], {"enabled": False})

    def test_custom_model_keeps_its_own_reasoning_defaults(self):
        with patch("providers.openrouter.chat_translate", return_value="translated") as chat:
            OpenRouterProvider().translate(
                "Hello", "eng_Latn", "kor_Hang", api_key="test-key", model="vendor/custom-model",
            )
            self.assertEqual(chat.call_args.args[2], "vendor/custom-model")
            self.assertNotIn("reasoning", chat.call_args.kwargs["extra"])
