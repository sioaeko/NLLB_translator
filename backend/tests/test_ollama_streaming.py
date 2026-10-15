import json
import unittest
from contextlib import contextmanager
from threading import Event
from unittest.mock import Mock, patch

import httpx

from inference_runtime import LOCAL_INFERENCE_LOCK
from ollama_models import configured_models
from providers.ollama import OllamaProvider


class OllamaStreamingTests(unittest.TestCase):
    def setUp(self):
        self.provider = OllamaProvider()
        self.closed = False
        self.read = []

    def upstream(self, events):
        @contextmanager
        def response(*args, **kwargs):
            def lines():
                for event in events:
                    self.read.append(event)
                    yield json.dumps(event)
            try:
                yield Mock(is_error=False, iter_lines=lines)
            finally:
                self.closed = True
        return patch("providers.ollama.httpx.stream", side_effect=response)

    def stream(self, **kwargs):
        return self.provider.stream_translate("Hello", "eng_Latn", "kor_Hang", **kwargs)

    def test_emits_before_completion_and_shares_sync_cache(self):
        events = [
            {"message": {"content": "  안녕"}},
            {"message": {"content": "하세요  "}},
            {"done": True, "done_reason": "stop"},
        ]
        with self.upstream(events) as stream:
            output = self.stream()
            self.assertEqual(next(output), "안녕")
            self.assertEqual(len(self.read), 1)
            self.assertEqual("".join(output), "하세요")
            self.assertTrue(self.closed)
            self.assertEqual("".join(self.stream()), "안녕하세요")
            with patch("providers.ollama.httpx.post") as post:
                self.assertEqual(self.provider.translate("Hello", "eng_Latn", "kor_Hang"), "안녕하세요")
                post.assert_not_called()
            self.assertEqual(stream.call_count, 1)

    def test_sync_result_is_reused_by_stream(self):
        response = Mock(json=lambda: {"message": {"content": "안녕"}})
        with patch("providers.ollama.httpx.post", return_value=response):
            self.provider.translate("Hello", "eng_Latn", "kor_Hang")
        with patch("providers.ollama.httpx.stream") as upstream:
            self.assertEqual(list(self.stream()), ["안녕"])
            upstream.assert_not_called()

    def test_split_thinking_is_hidden(self):
        chunks = [" <thi", "nk>private", " reasoning</th", "ink> 안", "녕  "]
        with self.upstream([*[{"message": {"content": c}} for c in chunks], {"done": True}]):
            self.assertEqual("".join(self.stream()), "안녕")

    def test_truncation_length_errors_and_empty_outputs_never_cache(self):
        for events in (
            [{"message": {"content": "partial"}}],
            [{"message": {"content": "partial"}}, {"done": True, "done_reason": "length"}],
            [{"error": "runner failed"}],
            [{"done": True}],
        ):
            with self.subTest(events=events), self.upstream(events) as upstream:
                for _ in range(2):
                    with self.assertRaises(RuntimeError):
                        list(self.stream())
                self.assertEqual(upstream.call_count, 2)
                self.assertFalse(self.provider._cache)
                self.assertTrue(self.closed)

    def test_close_releases_response_and_inference_slot_without_caching(self):
        with self.upstream([{"message": {"content": "partial"}}, {"done": True}]):
            output = self.stream()
            self.assertEqual(next(output), "partial")
            output.close()
        self.assertTrue(self.closed)
        self.assertFalse(self.provider._cache)
        self.assertTrue(LOCAL_INFERENCE_LOCK.acquire(blocking=False))
        LOCAL_INFERENCE_LOCK.release()

    def test_cancel_after_partial_does_not_cache(self):
        cancel = Event()
        with self.upstream([{"message": {"content": "partial"}}, {"done": True}]):
            output = self.stream(cancel=cancel)
            next(output)
            cancel.set()
            with self.assertRaises(InterruptedError):
                next(output)
        self.assertTrue(self.closed)
        self.assertFalse(self.provider._cache)

    def test_precancelled_stream_never_starts_upstream(self):
        cancel = Event()
        cancel.set()
        with patch("providers.ollama.httpx.stream") as upstream:
            with self.assertRaises(InterruptedError):
                list(self.stream(cancel=cancel))
            upstream.assert_not_called()

    def test_stream_payload_preserves_model_prompt_and_limits(self):
        for config in configured_models():
            with self.subTest(model=config.model):
                self.provider = OllamaProvider(config)
                with self.upstream([{"message": {"content": "번역"}, "done": True}]) as upstream, patch("providers.ollama.NUM_THREADS", 2):
                    self.assertEqual("".join(self.stream(model="ignored/cloud-model")), "번역")
                    payload = upstream.call_args.kwargs["json"]
                    self.assertEqual(payload["model"], config.model)
                    self.assertIs(payload["stream"], True)
                    self.assertEqual(payload["options"]["num_thread"], 2)
                    if config.id != "ollama":
                        self.assertIs(payload["think"], False)

    def test_http_error_is_read_and_response_closed(self):
        response = httpx.Response(503, json={"error": "not ready"}, request=httpx.Request("POST", "http://localhost/api/chat"))
        with patch("providers.ollama.httpx.stream") as upstream:
            upstream.return_value.__enter__.return_value = response
            with self.assertRaises(httpx.HTTPStatusError):
                list(self.stream())
            upstream.return_value.__exit__.assert_called_once()
        self.assertFalse(self.provider._cache)


if __name__ == "__main__":
    unittest.main()
