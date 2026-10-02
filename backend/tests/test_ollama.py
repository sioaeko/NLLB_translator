import os
import subprocess
import unittest
from contextlib import ExitStack
from threading import Event
from unittest.mock import Mock, patch

import httpx

import ollama_service
from ollama_models import configured_models
import providers
from providers import ollama


class OllamaTests(unittest.TestCase):
    def setUp(self):
        environment = patch.dict(os.environ, {
            "OLLAMA_HOST": "http://127.0.0.1:11434",
            "OLLAMA_MODEL": "translategemma:4b",
            "OLLAMA_QWEN35_MODEL": "qwen3.5:2b-q4_K_M",
            "OLLAMA_QWEN3_MODEL": "qwen3:1.7b",
        })
        environment.start()
        self.addCleanup(environment.stop)
        self.provider = ollama.OllamaProvider()
        self.provider._translate.cache_clear()
        self.addCleanup(self.provider._translate.cache_clear)

    def service_mocks(self, installed, children, pull=False):
        """Keep lifecycle tests independent of real processes and signal handlers."""
        stack = self.enterContext(ExitStack())
        stack.enter_context(patch.object(ollama_service.sys, "argv", [
            "ollama_service.py", *(["--pull"] if pull else []),
        ]))
        stack.enter_context(patch.object(ollama_service.signal, "signal"))
        stack.enter_context(patch.object(ollama_service, "wait_ready"))
        stack.enter_context(patch.object(ollama_service, "read_models", return_value={
            "models": [{"name": model} for model in installed],
        }))
        stack.enter_context(patch("builtins.print"))
        spawn = stack.enter_context(patch.object(ollama_service, "spawn", side_effect=children))
        stop = stack.enter_context(patch.object(ollama_service, "stop_process"))
        supervise = stack.enter_context(patch.object(ollama_service, "supervise", return_value=0))
        return spawn, stop, supervise

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

    def test_all_local_model_ids_are_registered(self):
        for engine_id in ("ollama", "ollama_qwen35", "ollama_qwen3"):
            with self.subTest(engine=engine_id):
                provider = providers.get(engine_id)
                self.assertIsInstance(provider, ollama.OllamaProvider)
                self.assertEqual(provider.id, engine_id)

    def test_each_engine_availability_requires_its_own_model(self):
        engines = [ollama.OllamaProvider(config) for config in configured_models()]
        for installed in engines:
            with self.subTest(installed=installed.model), patch.object(
                ollama.httpx, "get", return_value=Mock(
                    status_code=200, json=lambda: {"models": [{"name": installed.model}]},
                ),
            ):
                self.assertEqual(
                    [engine.id for engine in engines if engine.is_available()],
                    [installed.id],
                )

    def test_each_engine_routes_and_caches_independently_with_correct_prompt(self):
        expected_models = {
            "ollama": "translategemma:4b",
            "ollama_qwen35": "qwen3.5:2b-q4_K_M",
            "ollama_qwen3": "qwen3:1.7b",
        }
        engines = [ollama.OllamaProvider(config) for config in configured_models()]

        def translate_response(*args, **kwargs):
            return Mock(json=lambda: {"message": {"content": kwargs["json"]["model"]}})

        with patch.object(ollama.httpx, "post", side_effect=translate_response) as post:
            for engine in engines:
                with self.subTest(engine=engine.id):
                    # A cloud-model selection must not redirect a local engine.
                    result = engine.translate("Hello", "eng_Latn", "kor_Hang", model="other/model")
                    self.assertEqual(result, expected_models[engine.id])
                    payload = post.call_args.kwargs["json"]
                    self.assertEqual(payload["model"], expected_models[engine.id])
                    if engine.id == "ollama":
                        self.assertEqual([m["role"] for m in payload["messages"]], ["user"])
                        self.assertIn("Korean (ko)", payload["messages"][0]["content"])
                        self.assertNotIn("think", payload)
                    else:
                        self.assertIs(payload["think"], False)
                        self.assertEqual([m["role"] for m in payload["messages"]], ["system", "user"])
                        self.assertIn("Hello", payload["messages"][1]["content"])
            self.assertEqual(post.call_count, 3)
            for engine in reversed(engines):
                self.assertEqual(
                    engine.translate("Hello", "eng_Latn", "kor_Hang"),
                    expected_models[engine.id],
                )
            self.assertEqual(post.call_count, 3)

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

    def test_prepare_pulls_all_configured_models_and_cleans_up(self):
        models = ["translategemma:4b", "qwen3.5:2b-q4_K_M", "qwen3:1.7b"]
        server = Mock(poll=lambda: None)
        pulls = [Mock(poll=lambda: 0, returncode=0) for _ in models]
        spawn, stop, supervise = self.service_mocks(models, [server, *pulls], pull=True)
        self.assertEqual(ollama_service.main(), 0)
        self.assertEqual(
            [call.args[0] for call in spawn.call_args_list],
            [["ollama", "serve"], *[["ollama", "pull", model] for model in models]],
        )
        self.assertEqual([call.args[0] for call in stop.call_args_list], [*reversed(pulls), server])
        supervise.assert_not_called()

    def test_environment_overrides_apply_to_provider_and_unique_model_pulls(self):
        with patch.dict(os.environ, {
            "OLLAMA_MODEL": "custom/shared:latest",
            "OLLAMA_QWEN35_MODEL": "custom/shared:latest",
            "OLLAMA_QWEN3_MODEL": "custom/small:latest",
        }):
            engines = {config.id: ollama.OllamaProvider(config) for config in configured_models()}
            self.assertEqual({key: engine.model for key, engine in engines.items()}, {
                "ollama": "custom/shared:latest",
                "ollama_qwen35": "custom/shared:latest",
                "ollama_qwen3": "custom/small:latest",
            })
            models = ["custom/shared:latest", "custom/small:latest"]
            server = Mock(poll=lambda: None)
            pulls = [Mock(poll=lambda: 0, returncode=0) for _ in models]
            spawn, _, _ = self.service_mocks(models, [server, *pulls], pull=True)
            self.assertEqual(ollama_service.main(), 0)
            self.assertEqual(
                [call.args[0] for call in spawn.call_args_list],
                [["ollama", "serve"], *[["ollama", "pull", model] for model in models]],
            )

    def test_missing_required_model_prevents_api_start_and_cleans_up(self):
        models = [config.model for config in configured_models()]
        server = Mock(poll=lambda: None)
        spawn, stop, supervise = self.service_mocks(models[:-1], [server])
        with self.assertRaisesRegex(RuntimeError, "model is missing: qwen3:1.7b"):
            ollama_service.main()
        spawn.assert_called_once_with(["ollama", "serve"])
        stop.assert_called_once_with(server)
        supervise.assert_not_called()

    def test_all_required_models_allow_api_start(self):
        models = [config.model for config in configured_models()]
        server, api = Mock(poll=lambda: None), Mock(poll=lambda: None)
        spawn, stop, supervise = self.service_mocks(models, [server, api])
        self.assertEqual(ollama_service.main(), 0)
        self.assertEqual(spawn.call_count, 2)
        api_command = spawn.call_args.args[0]
        self.assertEqual(api_command[:4], [ollama_service.sys.executable, "-m", "uvicorn", "main:app"])
        self.assertEqual(supervise.call_args.args[0], [server, api])
        self.assertEqual([call.args[0] for call in stop.call_args_list], [api, server])

    def test_failed_pull_stops_preparation_and_cleans_up(self):
        models = [config.model for config in configured_models()]
        server = Mock(poll=lambda: None)
        first_pull = Mock(poll=lambda: 0, returncode=0)
        failed_pull = Mock(poll=lambda: 1, returncode=1)
        spawn, stop, supervise = self.service_mocks(
            models, [server, first_pull, failed_pull], pull=True,
        )
        with self.assertRaisesRegex(RuntimeError, "pull failed for qwen3.5:2b-q4_K_M"):
            ollama_service.main()
        self.assertEqual(spawn.call_count, 3)
        self.assertEqual([call.args[0] for call in stop.call_args_list], [failed_pull, first_pull, server])
        supervise.assert_not_called()

    def test_successful_pull_still_requires_installed_models(self):
        models = [config.model for config in configured_models()]
        server = Mock(poll=lambda: None)
        pulls = [Mock(poll=lambda: 0, returncode=0) for _ in models]
        _, stop, supervise = self.service_mocks(models[:-1], [server, *pulls], pull=True)
        with self.assertRaisesRegex(RuntimeError, "model is missing"):
            ollama_service.main()
        self.assertEqual(stop.call_count, 4)
        supervise.assert_not_called()

    def test_shutdown_escalates_after_timeout(self):
        process = Mock(pid=123, poll=lambda: None)
        process.wait.side_effect = [subprocess.TimeoutExpired("ollama", 15), 0]
        with patch.object(ollama_service.os, "name", "nt"):
            ollama_service.stop_process(process)
        process.terminate.assert_called_once()
        process.kill.assert_called_once()


if __name__ == "__main__":
    unittest.main()
