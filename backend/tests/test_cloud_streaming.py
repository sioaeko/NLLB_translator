"""Cloud streaming protocol and cancellation tests; no network or API keys."""

import json
import unittest
from contextlib import contextmanager
from threading import Event
from unittest.mock import patch

import httpx

from providers import gemini, groq, openai_api, openrouter
from providers.chat_api import chat_stream_translate


def sse(payload):
    data = payload if isinstance(payload, str) else json.dumps(payload, ensure_ascii=False)
    return f"data: {data}\n\n".encode()


def chat(content=None, finish=None):
    return sse({"choices": [{"delta": {} if content is None else {"content": content}, "finish_reason": finish}]})


def candidate(parts=None, finish=None):
    value = {"content": {"parts": parts or []}}
    if finish:
        value["finishReason"] = finish
    return sse({"candidates": [value]})


class TrackedBody(httpx.SyncByteStream):
    def __init__(self, chunks):
        self.chunks = chunks
        self.reads = 0
        self.closed = False

    def __iter__(self):
        for chunk in self.chunks:
            self.reads += 1
            yield chunk

    def close(self):
        self.closed = True


class CloudStreamingTests(unittest.TestCase):
    def setUp(self):
        self.bodies = []
        self.requests = []
        groq._resolved.clear()
        self.addCleanup(groq._resolved.clear)

    def upstream(self, responses):
        pending = iter(responses)

        @contextmanager
        def stream(method, url, **kwargs):
            self.requests.append((method, url, kwargs))
            status, chunks = next(pending)
            body = TrackedBody(chunks)
            self.bodies.append(body)
            response = httpx.Response(status, stream=body, request=httpx.Request(method, url))
            try:
                yield response
            finally:
                response.close()

        return patch("providers.chat_api.httpx.stream", side_effect=stream)

    def translate(self, **kwargs):
        return chat_stream_translate("https://provider.example/chat", "test-key", "test-model", "Hi", "eng_Latn", "kor_Hang", **kwargs)

    def test_chat_deltas_strip_split_thinking_and_preserve_request(self):
        events = [b": keepalive\n\n", sse({"choices": [{"delta": {"role": "assistant"}}]}),
                  chat(" <thi"), chat("nk>private thought</th"), chat("ink> 안녕"), chat("하세요.  "),
                  chat(finish="stop"), sse({"choices": [], "usage": {"total_tokens": 42}}), sse("[DONE]")]
        with self.upstream([(200, events)]):
            deltas = list(self.translate(extra={"temperature": 0.3}, headers={"X-Title": "Test"}))
        self.assertEqual("".join(deltas), "안녕하세요.")
        self.assertGreaterEqual(len(deltas), 2)
        request = self.requests[0][2]
        self.assertEqual(request["headers"], {"Authorization": "Bearer test-key", "X-Title": "Test"})
        self.assertTrue(request["json"]["stream"])
        self.assertEqual(request["json"]["temperature"], 0.3)
        self.assertEqual(request["timeout"], 60.0)
        self.assertTrue(self.bodies[0].closed)

    def test_chat_truncation_and_provider_error_fail_after_partial_output(self):
        for final in ([], [sse({"error": {"message": "private input must not be echoed"}})]):
            with self.subTest(final=final), self.upstream([(200, [chat("안녕"), *final])]):
                stream = self.translate()
                self.assertEqual(next(stream), "안녕")
                with self.assertRaises(RuntimeError) as caught:
                    list(stream)
                self.assertNotIn("private input", str(caught.exception))
                self.assertTrue(self.bodies[-1].closed)

    def test_chat_empty_or_non_successful_finish_fails(self):
        cases = [([chat(finish="stop"), sse("[DONE]")], "no translation"),
                 ([chat("partial", "length"), sse("[DONE]")], "could not finish"),
                 ([chat("<think>hidden</think>"), sse("[DONE]")], "no translation"),
                 ([b"data: not-json\n\n"], "Invalid streaming")]
        for events, error in cases:
            with self.subTest(error=error), self.upstream([(200, events)]):
                with self.assertRaisesRegex(RuntimeError, error):
                    list(self.translate())

    def test_http_error_body_remains_readable(self):
        with self.upstream([(429, [b'{"error":{"message":"rate limited"}}'])]):
            with self.assertRaises(httpx.HTTPStatusError) as caught:
                list(self.translate())
        self.assertIn("rate limited", caught.exception.response.text)
        self.assertTrue(self.bodies[0].closed)

    def test_cancel_stops_before_next_upstream_read_and_closes_response(self):
        cancel = Event()
        with self.upstream([(200, [chat("안녕"), chat("하세요"), sse("[DONE]")])]):
            stream = self.translate(cancel=cancel)
            self.assertEqual(next(stream), "안녕")
            reads = self.bodies[0].reads
            cancel.set()
            self.assertEqual(list(stream), [])
        self.assertEqual(self.bodies[0].reads, reads)
        self.assertTrue(self.bodies[0].closed)

    def test_closed_generator_closes_response(self):
        with self.upstream([(200, [chat("안녕"), sse("[DONE]")])]):
            stream = self.translate()
            next(stream)
            stream.close()
            self.assertTrue(self.bodies[0].closed)

    def test_pre_cancelled_call_does_not_open_connection(self):
        cancel = Event()
        cancel.set()
        with self.upstream([]):
            self.assertEqual(list(self.translate(cancel=cancel)), [])
        self.assertEqual(self.requests, [])

    def test_openai_and_openrouter_keep_models_headers_and_settings(self):
        with self.upstream([(200, [chat("안녕"), sse("[DONE]")])] * 2):
            list(openai_api.OpenAIProvider().stream_translate("Hi", "eng_Latn", "kor_Hang", api_key="first-key"))
            list(openrouter.OpenRouterProvider().stream_translate("Hi", "eng_Latn", "kor_Hang", api_key="second-key", model="qwen/test-model:free"))
        first, second = [request[2] for request in self.requests]
        self.assertEqual(first["json"]["model"], openai_api.MODEL)
        self.assertEqual(first["json"]["reasoning_effort"], "none")
        self.assertEqual(second["json"]["model"], "qwen/test-model:free")
        self.assertEqual(second["headers"]["HTTP-Referer"], openrouter.APP_URL)
        self.assertEqual(second["headers"]["X-Title"], "NLLB Translator")
        self.assertEqual(second["headers"]["Authorization"], "Bearer second-key")
        self.assertEqual(second["json"]["temperature"], 0.3)

    def test_groq_retries_removed_model_only_before_output(self):
        provider = groq.GroqQwenProvider()
        with self.upstream([(404, [b'{"error":{"code":"model_not_found"}}']),
                            (200, [chat("안녕"), sse("[DONE]")])]), patch.object(provider, "_successor", return_value="qwen/successor") as successor:
            result = list(provider.stream_translate("Hi", "eng_Latn", "kor_Hang", api_key="test-key"))
        self.assertEqual("".join(result), "안녕")
        self.assertEqual(self.requests[1][2]["json"]["model"], "qwen/successor")
        successor.assert_called_once_with("test-key")
        self.assertTrue(all(body.closed for body in self.bodies))

    def test_groq_does_not_retry_after_partial_output(self):
        response = httpx.Response(404, text="model_not_found", request=httpx.Request("POST", "https://example.test"))

        def broken_stream(*args, **kwargs):
            yield "partial"
            response.raise_for_status()

        provider = groq.GroqQwenProvider()
        with patch("providers.groq.chat_stream_translate", side_effect=broken_stream), patch.object(provider, "_successor") as successor:
            result = provider.stream_translate("Hi", "eng_Latn", "kor_Hang", api_key="test-key")
            self.assertEqual(next(result), "partial")
            with self.assertRaises(httpx.HTTPStatusError):
                next(result)
            successor.assert_not_called()

    def test_groq_does_not_retry_authentication_errors(self):
        provider = groq.GroqQwenProvider()
        with self.upstream([(401, [b'{"error":{"message":"invalid key"}}'])]), patch.object(provider, "_successor") as successor:
            with self.assertRaises(httpx.HTTPStatusError):
                list(provider.stream_translate("Hi", "eng_Latn", "kor_Hang", api_key="test-key"))
            successor.assert_not_called()

    def test_byok_requests_are_not_cached_or_shared_between_keys(self):
        provider = openrouter.OpenRouterProvider()
        with self.upstream([(200, [chat("first"), sse("[DONE]")]),
                            (200, [chat("second"), sse("[DONE]")])]):
            first = list(provider.stream_translate("Hi", "eng_Latn", "kor_Hang", api_key="first-key"))
            second = list(provider.stream_translate("Hi", "eng_Latn", "kor_Hang", api_key="second-key"))
        self.assertEqual(first, ["first"])
        self.assertEqual(second, ["second"])
        self.assertEqual(len(self.requests), 2)

    def test_gemini_filters_thoughts_and_preserves_prompt_and_headers(self):
        events = [candidate([{"text": "private thought", "thought": True}]),
                  candidate([{"text": " 안녕"}]), candidate([{"text": "하세요. "}], "STOP")]
        with self.upstream([(200, events)]):
            result = list(gemini.GeminiProvider().stream_translate("Hi", "eng_Latn", "kor_Hang", api_key="test-key"))
        self.assertEqual("".join(result), "안녕하세요.")
        method, url, request = self.requests[0]
        self.assertEqual(method, "POST")
        self.assertTrue(url.endswith(":streamGenerateContent?alt=sse"))
        self.assertNotIn("test-key", url)
        self.assertEqual(request["headers"], {"x-goog-api-key": "test-key"})
        self.assertEqual(request["json"]["generationConfig"]["thinkingConfig"]["thinkingLevel"], "minimal")
        self.assertTrue(self.bodies[0].closed)

    def test_gemini_block_truncation_empty_and_length_fail(self):
        cases = [([sse({"promptFeedback": {"blockReason": "SAFETY"}})], "blocked"),
                 ([candidate([{"text": "안녕"}])], "disconnected"),
                 ([candidate([], "STOP")], "no translation"),
                 ([candidate([{"text": "partial"}], "MAX_TOKENS")], "could not finish")]
        for events, error in cases:
            with self.subTest(error=error), self.upstream([(200, events)]):
                with self.assertRaisesRegex(RuntimeError, error):
                    list(gemini.GeminiProvider().stream_translate("Hi", "eng_Latn", "kor_Hang", api_key="test-key"))
                self.assertTrue(self.bodies[-1].closed)

    def test_gemini_cancel_closes_response_without_reading_next_event(self):
        cancel = Event()
        with self.upstream([(200, [candidate([{"text": "안녕"}]), candidate([], "STOP")])]):
            stream = gemini.GeminiProvider().stream_translate("Hi", "eng_Latn", "kor_Hang", api_key="test-key", cancel=cancel)
            self.assertEqual(next(stream), "안녕")
            reads = self.bodies[0].reads
            cancel.set()
            self.assertEqual(list(stream), [])
        self.assertEqual(self.bodies[0].reads, reads)
        self.assertTrue(self.bodies[0].closed)


if __name__ == "__main__":
    unittest.main()
