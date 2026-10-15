import sys
import unittest
from contextlib import ExitStack
from pathlib import Path
from threading import Event, Thread
from types import SimpleNamespace
from unittest.mock import Mock, patch

import inference_runtime as runtime
from providers import hymt, nllb


class CpuRuntimeTests(unittest.TestCase):
    def cpu_count(self, files, affinity=8, override=0):
        paths = {str(Path(key)): value for key, value in files.items()}
        with ExitStack() as stack:
            stack.enter_context(patch.object(runtime.os, "cpu_count", return_value=64))
            stack.enter_context(patch.object(
                runtime.os, "sched_getaffinity", return_value=set(range(affinity)), create=True
            ))
            stack.enter_context(patch.object(runtime, "_read", side_effect=lambda path: paths.get(str(path), "")))
            return runtime.cpu_thread_count(override)

    def test_cpu_quota_limits_large_host_thread_count(self):
        self.assertEqual(self.cpu_count({"/sys/fs/cgroup/cpu.max": "200000 100000"}), 2)
        self.assertEqual(self.cpu_count({"/sys/fs/cgroup/cpu.max": "200000 100000"}, affinity=1), 1)

    def test_nested_parent_quota_and_v1_quota(self):
        self.assertEqual(self.cpu_count({
            "/proc/self/cgroup": "0::/workload/app",
            "/sys/fs/cgroup/cpu.max": "max 100000",
            "/sys/fs/cgroup/workload/cpu.max": "200000 100000",
            "/sys/fs/cgroup/workload/app/cpu.max": "400000 100000",
        }), 2)
        self.assertEqual(self.cpu_count({
            "/proc/self/cgroup": "3:cpu,cpuacct:/workload",
            "/sys/fs/cgroup/cpu/cpu.cfs_quota_us": "-1",
            "/sys/fs/cgroup/cpu/cpu.cfs_period_us": "100000",
            "/sys/fs/cgroup/cpu/workload/cpu.cfs_quota_us": "150000",
            "/sys/fs/cgroup/cpu/workload/cpu.cfs_period_us": "100000",
        }), 1)

    def test_missing_quota_fallback_and_explicit_override(self):
        self.assertEqual(self.cpu_count({}), 8)
        self.assertEqual(self.cpu_count({"/sys/fs/cgroup/cpu.max": "invalid"}), 8)
        self.assertEqual(self.cpu_count({"/sys/fs/cgroup/cpu.max": "100000 100000"}, override=4), 4)
        with patch.object(runtime.os, "cpu_count", return_value=None), patch.object(
            runtime.os, "sched_getaffinity", side_effect=OSError, create=True
        ), patch.object(runtime, "_quota_limits", return_value=[]):
            self.assertEqual(runtime.cpu_thread_count(), 1)

    def test_cancelled_waiter_never_enters_inference(self):
        cancel = Event()
        started = Event()
        entered = Event()
        stopped = Event()

        def waiter():
            started.set()
            try:
                with runtime.local_inference(cancel):
                    entered.set()
            except InterruptedError:
                stopped.set()

        with runtime.local_inference():
            thread = Thread(target=waiter, daemon=True)
            thread.start()
            self.assertTrue(started.wait(1))
            cancel.set()
            self.assertTrue(stopped.wait(1))
            self.assertFalse(entered.is_set())
        thread.join(1)
        self.assertFalse(thread.is_alive())
        with self.assertRaises(RuntimeError):
            with runtime.local_inference():
                raise RuntimeError("inference failed")
        self.assertFalse(runtime.LOCAL_INFERENCE_LOCK.locked())


def completion_chunks(parts, on_close=None, finish_reason="stop"):
    try:
        yield {"choices": [{"delta": {"role": "assistant"}}]}
        for part in parts:
            if isinstance(part, Exception):
                raise part
            yield {"choices": [{"delta": {"content": part}}]}
        if finish_reason is not None:
            yield {"choices": [{"delta": {}, "finish_reason": finish_reason}]}
    finally:
        if on_close is not None:
            on_close()


class HyMTStreamingTests(unittest.TestCase):
    def setUp(self):
        self.provider = hymt.HyMTProvider()
        self.provider._llm = Mock()

    def test_real_incremental_output_and_shared_completed_line_cache(self):
        self.provider._llm.create_chat_completion.side_effect = lambda **_: completion_chunks(
            ["  안녕", "하세요", "  "]
        )
        stream = self.provider.stream_translate("Hello", "eng_Latn", "kor_Hang")
        self.addCleanup(stream.close)
        self.assertEqual(next(stream), "안녕")
        self.assertFalse(self.provider._cache)
        self.assertEqual("".join(stream), "하세요")
        self.assertEqual(self.provider.translate("Hello\n\nHello", "eng_Latn", "kor_Hang"), "안녕하세요\n\n안녕하세요")
        self.assertEqual(self.provider._llm.create_chat_completion.call_count, 1)
        options = self.provider._llm.create_chat_completion.call_args.kwargs
        self.assertTrue(options["stream"])
        self.assertEqual(options["temperature"], 0.7)
        self.assertEqual(options["top_p"], 0.6)

    def test_generator_close_releases_inference_and_does_not_cache_partial_line(self):
        closed = Mock()
        self.provider._llm.create_chat_completion.side_effect = lambda **_: completion_chunks(
            ["partial", " remainder"], closed
        )
        stream = self.provider.stream_translate("Hello", "eng_Latn", "kor_Hang")
        self.addCleanup(stream.close)
        self.assertEqual(next(stream), "partial")
        self.assertTrue(runtime.LOCAL_INFERENCE_LOCK.locked())
        stream.close()
        closed.assert_called_once()
        self.assertFalse(self.provider._infer_lock.locked())
        self.assertFalse(runtime.LOCAL_INFERENCE_LOCK.locked())
        self.assertFalse(self.provider._cache)

    def test_cancel_and_backend_failure_do_not_cache(self):
        for fail in (False, True):
            with self.subTest(failure=fail):
                cancel = Event()
                self.provider._llm.create_chat_completion.side_effect = lambda **_: completion_chunks(
                    ["partial", RuntimeError("decode failed") if fail else " more"]
                )
                stream = self.provider.stream_translate("Hello", "eng_Latn", "kor_Hang", cancel=cancel)
                self.addCleanup(stream.close)
                self.assertEqual(next(stream), "partial")
                if not fail:
                    cancel.set()
                with self.assertRaises(RuntimeError if fail else InterruptedError):
                    list(stream)
                self.assertFalse(self.provider._cache)
                self.assertFalse(runtime.LOCAL_INFERENCE_LOCK.locked())

    def test_reasoning_removal_and_blank_lines_match_sync_output(self):
        self.provider._llm.create_chat_completion.side_effect = lambda **_: completion_chunks(
            ["  <thi", "nk>hidden</think>", "Result  "]
        )
        text = "\nHello\n  \n"
        output = "".join(self.provider.stream_translate(text, "eng_Latn", "kor_Hang"))
        self.assertEqual(output, "\nResult\n\n")
        self.assertEqual(self.provider.translate(text, "eng_Latn", "kor_Hang"), output)

    def test_truncated_interrupted_and_empty_results_never_cache(self):
        for reason, parts in (
            ("length", ["Partial result"]),
            ("tool_calls", ["Partial result"]),
            (None, ["Partial result"]),
            ("stop", ["  ", "<think>hidden</think>", "\n"]),
        ):
            with self.subTest(reason=reason, parts=parts):
                closed = Mock()
                self.provider._llm.create_chat_completion.side_effect = lambda **_: completion_chunks(
                    parts, closed, finish_reason=reason
                )
                with self.assertRaises(RuntimeError):
                    self.provider.translate("Hello", "eng_Latn", "kor_Hang")
                closed.assert_called_once()
                self.assertFalse(self.provider._cache)
                self.assertFalse(self.provider._infer_lock.locked())
                self.assertFalse(runtime.LOCAL_INFERENCE_LOCK.locked())

    def test_model_uses_available_cpu_for_both_thread_pools(self):
        provider = hymt.HyMTProvider()
        llama = Mock()
        with patch.dict(sys.modules, {"llama_cpp": SimpleNamespace(Llama=llama)}), patch.object(
            hymt, "cpu_thread_count", return_value=2
        ):
            provider._ensure_loaded()
        self.assertEqual(llama.call_args.kwargs["n_threads"], 2)
        self.assertEqual(llama.call_args.kwargs["n_threads_batch"], 2)


class NLLBStreamingTests(unittest.TestCase):
    def setUp(self):
        self.provider = nllb.NLLBProvider()
        self.provider._translator = Mock()
        self.provider._translator.translate_batch.return_value = [
            SimpleNamespace(hypotheses=[["kor_Hang", "translated"]])
        ]
        self.provider._tokenizer = Mock()
        self.provider._tokenizer.decode.return_value = "Translated"

    def test_line_stream_preserves_blanks_and_caches_without_changing_beam(self):
        stream = self.provider.stream_translate("First\n\nSecond\n", "eng_Latn", "kor_Hang")
        self.addCleanup(stream.close)
        self.assertEqual(next(stream), "Translated")
        self.assertEqual(self.provider._translator.translate_batch.call_count, 1)
        self.assertEqual("".join(stream), "\n\nTranslated\n")
        self.assertEqual(self.provider._translator.translate_batch.call_count, 2)
        self.assertEqual(self.provider._translator.translate_batch.call_args.kwargs["beam_size"], 4)
        # A cache hit is available even while another engine owns the CPU slot.
        with runtime.local_inference():
            self.assertEqual(self.provider.translate("First", "eng_Latn", "kor_Hang"), "Translated")
        self.assertEqual(self.provider._translator.translate_batch.call_count, 2)

    def test_cancel_during_a_line_does_not_cache_or_start_next_line(self):
        cancel = Event()
        result = self.provider._translator.translate_batch.return_value

        def finish_after_cancel(*args, **kwargs):
            cancel.set()
            return result

        self.provider._translator.translate_batch.side_effect = finish_after_cancel
        with self.assertRaises(InterruptedError):
            list(self.provider.stream_translate("First\nSecond", "eng_Latn", "kor_Hang", cancel=cancel))
        self.assertFalse(self.provider._cache)
        self.assertFalse(runtime.LOCAL_INFERENCE_LOCK.locked())
        self.assertEqual(self.provider._translator.translate_batch.call_count, 1)

    def test_stream_close_does_not_start_remaining_lines(self):
        stream = self.provider.stream_translate("First\nSecond", "eng_Latn", "kor_Hang")
        self.addCleanup(stream.close)
        next(stream)
        stream.close()
        self.assertEqual(self.provider._translator.translate_batch.call_count, 1)
        self.assertFalse(runtime.LOCAL_INFERENCE_LOCK.locked())

    def test_model_uses_one_worker_and_available_cpu(self):
        provider = nllb.NLLBProvider()
        translator = Mock()
        tokenizer = Mock()
        with patch.dict(sys.modules, {
            "ctranslate2": SimpleNamespace(Translator=translator),
            "transformers": SimpleNamespace(AutoTokenizer=tokenizer),
        }), patch.object(nllb, "cpu_thread_count", return_value=2):
            provider._ensure_loaded()
        self.assertEqual(translator.call_args.kwargs["intra_threads"], 2)
        self.assertEqual(translator.call_args.kwargs["inter_threads"], 1)
        self.assertIs(provider._tokenizer, tokenizer.from_pretrained.return_value)


if __name__ == "__main__":
    unittest.main()
