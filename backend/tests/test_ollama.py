import subprocess
import unittest
from threading import Event
from unittest.mock import Mock, patch

import httpx

import ollama_service
from providers import ollama


class OllamaTests(unittest.TestCase):
    def setUp(self):
        self.provider = ollama.OllamaProvider()
        self.provider._translate.cache_clear()

    def test_daemon_without_selected_model_is_unavailable(self):
        with patch.object(ollama.httpx, "get", return_value=Mock(
            status_code=200, json=lambda: {"models": [{"name": "qwen3:4b"}]}
        )):
            self.assertFalse(self.provider.is_available())

    def test_selected_model_is_available(self):
        with patch.object(ollama.httpx, "get", return_value=Mock(
            status_code=200, json=lambda: {"models": [{"name": "translategemma:4b"}]}
        )):
            self.assertTrue(self.provider.is_available())

    def test_default_tag_and_registry_port(self):
        self.assertTrue(ollama_service.model_present(
            {"models": [{"name": "localhost:5000/team/model:latest"}]},
            "localhost:5000/team/model",
        ))
        self.assertFalse(ollama_service.model_present(
            {"models": [{"name": "translategemma:12b"}]}, "translategemma:4b"
        ))

    def test_unreachable_daemon_is_unavailable(self):
        with patch.object(ollama.httpx, "get", side_effect=httpx.ConnectError("offline")):
            self.assertFalse(self.provider.is_available())

    def test_request_limits_and_cache(self):
        response = Mock()
        response.json.return_value = {"message": {"content": " translated "}}
        with patch.object(ollama.httpx, "post", return_value=response) as post, \
             patch.object(ollama, "NUM_THREADS", 2):
            self.assertEqual(self.provider.translate("Hello", "eng_Latn", "kor_Hang"), "translated")
            self.provider.translate("Hello", "eng_Latn", "kor_Hang")
            self.assertEqual(post.call_count, 1)
            payload = post.call_args.kwargs["json"]
            self.assertEqual(payload["options"]["num_ctx"], 4096)
            self.assertEqual(payload["options"]["num_thread"], 2)
            self.assertEqual(payload["messages"][0]["role"], "user")
            self.assertIn("Korean (ko)", payload["messages"][0]["content"])

    def test_failed_requests_are_not_cached(self):
        with patch.object(ollama.httpx, "post", side_effect=httpx.ReadTimeout("busy")) as post:
            for _ in range(2):
                with self.assertRaises(httpx.ReadTimeout):
                    self.provider.translate("retry", "eng_Latn", "kor_Hang")
            self.assertEqual(post.call_count, 2)

    def test_service_exit_fails_container(self):
        stop = Mock()
        stop.wait.return_value = False
        self.assertEqual(ollama_service.supervise([Mock(poll=lambda: 0)], stop), 1)

    def test_startup_detects_crashed_server(self):
        with self.assertRaisesRegex(RuntimeError, "exited before"):
            ollama_service.wait_ready(Mock(poll=lambda: 1), "http://localhost:11434", Event())

    def test_shutdown_escalates_after_timeout(self):
        process = Mock(pid=123, poll=lambda: None)
        process.wait.side_effect = [subprocess.TimeoutExpired("ollama", 15), 0]
        with patch.object(ollama_service.os, "name", "nt"):
            ollama_service.stop_process(process)
        process.terminate.assert_called_once()
        process.kill.assert_called_once()


if __name__ == "__main__":
    unittest.main()
