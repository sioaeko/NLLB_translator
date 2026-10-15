"""Translation API integration tests with in-process fake providers only."""

import asyncio
import json
import socket
import unittest
from contextlib import nullcontext
from threading import Event
from types import SimpleNamespace
from unittest.mock import Mock, patch

import httpx
from fastapi.testclient import TestClient

import main


def require_asyncio_ipc():
    # Windows asyncio uses a loopback socket pair even for in-process ASGI tests.
    # A restricted runner can block accept forever; fail the prerequisite quickly.
    previous_timeout = socket.getdefaulttimeout()
    try:
        socket.setdefaulttimeout(0.5)
        first, second = socket.socketpair()
        first.close()
        second.close()
    except OSError as exc:
        raise unittest.SkipTest(f"Asyncio local IPC unavailable in this runner: {exc}") from exc
    finally:
        socket.setdefaulttimeout(previous_timeout)


def provider(**overrides):
    fields = dict(
        id="fake", kind="local", key_field="", setup_hint="Configure fake engine.",
        is_available=Mock(return_value=True),
        translate=Mock(return_value="안녕하세요"),
        stream_translate=Mock(side_effect=lambda *args, **kwargs: iter(["안녕", "하세요"])),
    )
    fields.update(overrides)
    return SimpleNamespace(**fields)


def request(**overrides):
    return main.TranslateRequest(**{
        "text": "Hello", "source": "eng_Latn", "target": "kor_Hang", "engine": "fake", **overrides,
    })


class StreamEndpointTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        require_asyncio_ipc()

    def setUp(self):
        self.client = TestClient(main.app)
        self.addCleanup(self.client.close)

    def packets(self, response):
        return [json.loads(line) for line in response.text.splitlines() if line]

    def test_done_matches_deltas_and_disables_response_buffering_cache(self):
        engine = provider()
        with patch.object(main.providers, "get", return_value=engine):
            response = self.client.post("/api/translate/stream", json=request().model_dump())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-type"], "application/x-ndjson")
        self.assertEqual(response.headers["cache-control"], "no-store")
        self.assertEqual(response.headers["x-accel-buffering"], "no")
        packets = self.packets(response)
        self.assertEqual([packet["type"] for packet in packets], ["delta", "delta", "done"])
        self.assertEqual(packets[-1]["translation"], "".join(packet["text"] for packet in packets[:-1]))
        self.assertEqual(packets[-1]["engine"], "fake")

    def test_error_after_partial_output_never_sends_done(self):
        def broken(*args, **kwargs):
            yield "부분 번역"
            raise RuntimeError("decode failed")

        engine = provider(stream_translate=Mock(side_effect=broken))
        with patch.object(main.providers, "get", return_value=engine):
            response = self.client.post("/api/translate/stream", json=request().model_dump())
        packets = self.packets(response)
        self.assertEqual([packet["type"] for packet in packets], ["delta", "error"])
        self.assertEqual(packets[1]["status"], 500)
        self.assertIn("decode failed", packets[1]["detail"])

    def test_empty_text_keeps_sync_shortcut_without_loading_provider(self):
        with patch.object(main.providers, "get") as get:
            for path in ("/api/translate", "/api/translate/stream"):
                response = self.client.post(path, json=request(text=" \n\t").model_dump())
                self.assertEqual(response.status_code, 200)
                result = response.json() if path.endswith("translate") else self.packets(response)[0]
                self.assertEqual(result["translation"], "")
            get.assert_not_called()

    def test_same_language_bypasses_unavailable_engine_and_inference(self):
        engine = provider(kind="api", key_field="openai", is_available=Mock(return_value=False))
        with patch.object(main.providers, "get", return_value=engine):
            for path in ("/api/translate", "/api/translate/stream"):
                response = self.client.post(path, json=request(target="eng_Latn").model_dump())
                self.assertEqual(response.status_code, 200)
                result = response.json() if path.endswith("translate") else self.packets(response)[-1]
                self.assertEqual(result["translation"], "Hello")
        engine.translate.assert_not_called()
        engine.stream_translate.assert_not_called()
        engine.is_available.assert_not_called()

    def test_invalid_request_fails_before_stream_starts(self):
        engine = provider()
        with patch.object(main.providers, "get", return_value=engine):
            for change in ({"source": "unknown"}, {"text": "a" * (main.MAX_INPUT_CHARS + 1)}):
                for path in ("/api/translate", "/api/translate/stream"):
                    with self.subTest(path=path, fields=tuple(change)):
                        response = self.client.post(path, json=request(**change).model_dump())
                        self.assertEqual(response.status_code, 400)
                        self.assertIn("detail", response.json())
        engine.stream_translate.assert_not_called()
        engine.translate.assert_not_called()

    def test_unknown_and_unavailable_engine_reject_before_stream_starts(self):
        with patch.object(main.providers, "get", return_value=None):
            response = self.client.post("/api/translate/stream", json=request().model_dump())
            self.assertEqual(response.status_code, 400)
        engine = provider(is_available=Mock(return_value=False))
        with patch.object(main.providers, "get", return_value=engine):
            response = self.client.post("/api/translate/stream", json=request().model_dump())
            self.assertEqual(response.status_code, 503)

    def test_byok_passes_only_selected_provider_key_and_openrouter_model(self):
        headers = {"X-OpenRouter-Key": "router-test-key", "X-OpenAI-Key": "other-test-key",
                   "X-OpenRouter-Model": "qwen/test:free"}
        engine = provider(kind="api", key_field="openrouter", is_available=Mock(return_value=False))
        with patch.object(main.providers, "get", return_value=engine):
            response = self.client.post("/api/translate/stream", json=request().model_dump(), headers=headers)
        self.assertEqual(response.status_code, 200)
        options = engine.stream_translate.call_args.kwargs
        self.assertEqual(options["api_key"], "router-test-key")
        self.assertEqual(options["model"], "qwen/test:free")
        self.assertIsInstance(options["cancel"], Event)
        self.assertNotIn("test-key", response.text)
        engine.key_field = "openai"
        with patch.object(main.providers, "get", return_value=engine):
            response = self.client.post("/api/translate", json=request().model_dump(), headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(engine.translate.call_args.kwargs, {"api_key": "other-test-key", "model": None})

    def test_sync_response_and_http_error_mapping_remain_compatible(self):
        engine = provider()
        with patch.object(main.providers, "get", return_value=engine):
            response = self.client.post("/api/translate", json=request().model_dump())
            self.assertEqual(response.json(), {"translation": "안녕하세요", "source": "eng_Latn", "target": "kor_Hang", "engine": "fake"})
            upstream = httpx.Response(429, json={"error": {"message": "limited"}},
                                      request=httpx.Request("POST", "https://example.test"))
            failure = httpx.HTTPStatusError("limited", request=upstream.request, response=upstream)
            engine.translate.side_effect = failure
            response = self.client.post("/api/translate", json=request().model_dump())
            self.assertEqual(response.status_code, 502)
            self.assertIn("rate limit", response.json()["detail"])


class StreamLifecycleTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        require_asyncio_ipc()

    async def test_first_delta_is_available_before_provider_finishes(self):
        proceed = Event()
        finished = Event()

        def incremental(*args, **kwargs):
            try:
                yield "first"
                if not proceed.wait(2):
                    raise RuntimeError("Test did not release provider")
                yield " second"
            finally:
                finished.set()

        engine = provider(stream_translate=incremental)
        stream = main._stream_response(request(), engine, None, None)
        try:
            first = json.loads(await asyncio.wait_for(anext(stream), 1))
            self.assertEqual(first, {"type": "delta", "text": "first"})
            self.assertFalse(finished.is_set())
            proceed.set()
            remaining = [json.loads(packet) async for packet in stream]
            self.assertEqual(remaining[-1]["translation"], "first second")
        finally:
            proceed.set()
            await stream.aclose()

    async def test_closing_response_generator_cancels_and_closes_provider(self):
        closed = Event()
        captured = []

        def waiting(*args, cancel, **kwargs):
            captured.append(cancel)
            try:
                yield "first"
                if not cancel.wait(2):
                    raise RuntimeError("Cancellation never reached provider")
            finally:
                closed.set()

        stream = main._stream_response(request(), provider(stream_translate=waiting), None, None)
        await asyncio.wait_for(anext(stream), 1)
        await stream.aclose()
        self.assertTrue(captured[0].is_set())
        self.assertTrue(await asyncio.to_thread(closed.wait, 1))

    async def test_asgi_disconnect_while_sending_closes_retained_body_iterator(self):
        closed = Event()
        captured = []
        sending = asyncio.Event()

        def waiting(*args, cancel, **kwargs):
            captured.append(cancel)
            try:
                yield "first"
                cancel.wait(2)
            finally:
                closed.set()

        engine = provider(stream_translate=waiting)
        with patch.object(main.providers, "get", return_value=engine):
            response = main.translate_stream_endpoint(request(), None, None, None, None, None)

        async def receive():
            await sending.wait()
            return {"type": "http.disconnect"}

        async def send(message):
            if message["type"] == "http.response.body" and message.get("body"):
                sending.set()
                # Keep the iterator suspended at yield while ASGI cancels send.
                await asyncio.Event().wait()

        try:
            await asyncio.wait_for(response({"type": "http", "asgi": {"version": "3.0", "spec_version": "2.0"}}, receive, send), 1)
            self.assertTrue(captured[0].is_set(), "ASGI disconnect must close the retained body iterator")
            self.assertTrue(await asyncio.to_thread(closed.wait, 1))
        finally:
            await response.body_iterator.aclose()


def run_without_loop(awaitable):
    """Drive a coroutine whose mocked I/O never suspends; no socket IPC needed."""
    try:
        awaitable.send(None)
    except StopIteration as result:
        return result.value
    raise AssertionError("Unexpected suspended awaitable in no-I/O test")


class StreamBridgeTests(unittest.TestCase):
    """Exercise the real worker/queue bridge even when asyncio IPC is blocked."""

    def setUp(self):
        async def immediate_receive(func):
            return func()

        mocked = patch.object(main.anyio.to_thread, "run_sync", side_effect=immediate_receive)
        mocked.start()
        self.addCleanup(mocked.stop)

    def test_partial_output_precedes_completion_and_close_cancels_worker(self):
        closed = Event()
        captured = []

        def waiting(*args, cancel, **kwargs):
            captured.append(cancel)
            try:
                yield "first"
                cancel.wait(1)
            finally:
                closed.set()

        stream = main._stream_response(request(), provider(stream_translate=waiting), None, None)
        try:
            self.assertEqual(json.loads(run_without_loop(anext(stream))), {"type": "delta", "text": "first"})
            self.assertFalse(closed.is_set())
        finally:
            run_without_loop(stream.aclose())
        self.assertTrue(captured[0].is_set())
        self.assertTrue(closed.wait(1))

    def test_partial_then_error_has_no_done_packet(self):
        def broken(*args, **kwargs):
            yield "first"
            raise RuntimeError("failed after partial output")

        stream = main._stream_response(request(), provider(stream_translate=broken), None, None)
        try:
            first = json.loads(run_without_loop(anext(stream)))
            second = json.loads(run_without_loop(anext(stream)))
            self.assertEqual([first["type"], second["type"]], ["delta", "error"])
            with self.assertRaises(StopAsyncIteration):
                run_without_loop(anext(stream))
        finally:
            run_without_loop(stream.aclose())

    def test_send_failure_explicitly_closes_body_iterator(self):
        closed = []

        async def body():
            try:
                yield "partial"
            finally:
                closed.append(True)

        async def failed_send(*args):
            raise OSError("client disconnected")

        response = main.TranslationStreamingResponse(body())
        self.assertEqual(run_without_loop(anext(response.body_iterator)), "partial")
        with patch.object(main.StreamingResponse, "__call__", side_effect=failed_send), patch.object(
            main.anyio, "CancelScope", return_value=nullcontext()
        ):
            with self.assertRaisesRegex(OSError, "disconnected"):
                run_without_loop(response({}, None, None))
        self.assertEqual(closed, [True])


if __name__ == "__main__":
    unittest.main()
