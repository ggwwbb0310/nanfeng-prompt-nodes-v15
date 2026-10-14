import asyncio
import importlib.util
import unittest
from pathlib import Path
from unittest.mock import patch

MODULE_PATH = Path(__file__).with_name("storyboard_api.py")
spec = importlib.util.spec_from_file_location("nanfeng_storyboard_api_test", MODULE_PATH)
api = importlib.util.module_from_spec(spec)
spec.loader.exec_module(api)


class StoryboardAPIRegressionTests(unittest.TestCase):
    def test_output_budget_is_bounded_for_two_segments(self):
        self.assertEqual(api.storyboard_output_budget(2), 2000)

    def test_job_does_not_restart_entire_paid_pipeline_after_transient_error(self):
        job = api.StoryboardJob("job", {})
        calls = 0

        def fail_once(_payload, cancel_event=None):
            nonlocal calls
            calls += 1
            raise api.TransientAPIError("upstream timeout")

        def no_wait(_seconds):
            if calls >= 2:
                job.cancelled = True
            return job.cancelled

        with patch.object(api, "generate_storyboard", side_effect=fail_once), \
             patch.object(job.cancel_event, "wait", side_effect=no_wait):
            api._run_storyboard_job(job)

        self.assertEqual(calls, 1)
        self.assertEqual(job.status, "failed")
        self.assertIn("upstream timeout", job.error)

    def test_generate_uses_short_single_attempt_text_request(self):
        cfg = {
            "NANFENG_TEXT_BASE_URL": "https://example.test/v1",
            "NANFENG_TEXT_API_KEY": "key",
            "NANFENG_TEXT_MODEL": "model",
            "NANFENG_TEXT_PROTOCOL": "chat_completions",
        }
        captured = {}

        def fake_request(*args, **kwargs):
            captured.update(kwargs)
            return "段1\n\n测试分镜"

        with patch.object(api, "resolve_input_images", return_value=[]), \
             patch.object(api, "resolve_input_media", return_value=[]), \
             patch.object(api, "load_storyboard_skill", return_value="skill"), \
             patch.object(api, "storyboard_messages", return_value=[]), \
             patch.object(api, "request_model", side_effect=fake_request):
            result = asyncio.run(api.generate_storyboard({
                "segment_count": 1,
                "duration_seconds": 5,
                "mode": "t2va",
                "idea": "test",
            }, cfg))

        self.assertEqual(len(result["segments"]), 1)
        self.assertLessEqual(captured["timeout"], 180)
        self.assertEqual(captured["attempts"], 1)

    def test_request_model_can_collect_streamed_chat_chunks(self):
        class FakeResponse:
            status = 200
            headers = {"content-type": "text/event-stream"}
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def __iter__(self):
                return iter([
                    b'data: {"choices":[{"delta":{"content":"hello "}}]}\n',
                    b'data: {"choices":[{"delta":{"content":"world"},"finish_reason":"stop"}]}\n',
                    b'data: [DONE]\n',
                ])

        with patch.object(api.urllib.request, "urlopen", return_value=FakeResponse()):
            text = api.request_model(
                "https://example.test/v1", "key", "model", [{"role": "user", "content": "x"}],
                stream=True, attempts=1,
            )

        self.assertEqual(text, "hello world")

    def test_regular_skill_stays_small_enough_for_proxy(self):
        skill = api.load_storyboard_skill("ref2va", "regular_storyboard")
        self.assertLess(len(skill), 15000)
        self.assertNotIn("# Embedded reference:", skill)

    def test_disable_reasoning_uses_openai_compatible_control(self):
        captured = {}

        class FakeResponse:
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def read(self):
                return b'{"choices":[{"message":{"content":"ok"}}]}'

        def fake_urlopen(request, timeout):
            captured.update(__import__("json").loads(request.data.decode("utf-8")))
            return FakeResponse()

        with patch.object(api.urllib.request, "urlopen", side_effect=fake_urlopen):
            api.request_model(
                "https://example.test/v1", "key", "gpt-5.6-sol", [{"role": "user", "content": "x"}],
                disable_reasoning=True, attempts=1,
            )

        self.assertEqual(captured.get("reasoning_effort"), "none")

    def test_disable_reasoning_does_not_send_unknown_field_to_generic_model(self):
        captured = {}

        class FakeResponse:
            headers = {"content-type": "application/json"}
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def read(self): return b'{"choices":[{"message":{"content":"ok"}}]}'

        def fake_urlopen(request, timeout):
            captured.update(__import__("json").loads(request.data.decode("utf-8")))
            return FakeResponse()

        with patch.object(api.urllib.request, "urlopen", side_effect=fake_urlopen):
            api.request_model("https://example.test/v1", "key", "generic-vision", [{"role": "user", "content": "x"}], disable_reasoning=True, attempts=1)

        self.assertNotIn("reasoning_effort", captured)
        self.assertNotIn("thinking", captured)

    def test_stream_requires_done_or_finish_reason(self):
        class FakeResponse:
            headers = {"content-type": "text/event-stream"}
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def __iter__(self): return iter([b'data: {"choices":[{"delta":{"content":"partial"}}]}\n'])

        with patch.object(api.urllib.request, "urlopen", return_value=FakeResponse()):
            with self.assertRaises(api.StoryboardFormatError):
                api.request_model("https://example.test/v1", "key", "model", [{"role": "user", "content": "x"}], stream=True, attempts=1)

    def test_stream_accepts_plain_json_fallback(self):
        class FakeResponse:
            headers = {"content-type": "application/json"}
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def read(self): return b'{"choices":[{"message":{"content":"fallback"}}]}'

        with patch.object(api.urllib.request, "urlopen", return_value=FakeResponse()):
            text = api.request_model("https://example.test/v1", "key", "model", [{"role": "user", "content": "x"}], stream=True, attempts=1)
        self.assertEqual(text, "fallback")

    def test_budget_scales_to_twelve_segments(self):
        self.assertGreaterEqual(api.storyboard_output_budget(12), 7000)

    def test_skill_includes_compact_runtime_contract(self):
        skill = api.load_storyboard_skill("ref2va", "regular_storyboard")
        self.assertIn("Runtime compact Ref2VA contract", skill)
        self.assertIn("[Shot 2] At MM:SS.mmm", skill)

    def test_cancel_after_vision_prevents_text_request(self):
        cfg = {
            "NANFENG_VISION_BASE_URL": "https://example.test/v1", "NANFENG_VISION_API_KEY": "key",
            "NANFENG_VISION_MODEL": "vision", "NANFENG_VISION_PROTOCOL": "chat_completions",
            "NANFENG_TEXT_BASE_URL": "https://example.test/v1", "NANFENG_TEXT_API_KEY": "key",
            "NANFENG_TEXT_MODEL": "text", "NANFENG_TEXT_PROTOCOL": "chat_completions",
        }
        cancelled = __import__("threading").Event()
        text_called = False

        async def fake_analyze(_images, _cfg, cancel_event=None):
            cancelled.set()
            return "analysis"

        def fake_request(*args, **kwargs):
            nonlocal text_called
            text_called = True
            return "段1\n\ntest"

        with patch.object(api, "resolve_input_images", return_value=[{"index": 1}]), \
             patch.object(api, "resolve_input_media", return_value=[]), \
             patch.object(api, "load_storyboard_skill", return_value="skill"), \
             patch.object(api, "analyze_images", side_effect=fake_analyze), \
             patch.object(api, "request_model", side_effect=fake_request):
            with self.assertRaises(api.StoryboardCancelled):
                asyncio.run(api.generate_storyboard({"segment_count": 1, "duration_seconds": 5, "mode": "i2va"}, cfg, cancel_event=cancelled))

        self.assertFalse(text_called)

    def test_vision_request_never_retries_unknown_billing_result(self):
        captured = {}

        def fake_request(*args, **kwargs):
            captured.update(kwargs)
            return "analysis"

        image = {"index": 1, "mime": "image/jpeg", "base64": "unique-test-image"}
        cfg = {"NANFENG_VISION_BASE_URL": "https://example.test/v1", "NANFENG_VISION_API_KEY": "key", "NANFENG_VISION_MODEL": "vision", "NANFENG_VISION_PROTOCOL": "chat_completions"}
        with patch.object(api, "request_model", side_effect=fake_request), patch.object(api, "_save_vision_cache"):
            asyncio.run(api.analyze_images([image], cfg))
        self.assertEqual(captured["attempts"], 1)
        self.assertLessEqual(captured["timeout"], 60)

    def test_nonstream_rejects_length_truncation_even_with_text(self):
        with self.assertRaises(api.StoryboardFormatError):
            api._extract_text({"choices": [{"finish_reason": "length", "message": {"content": "partial"}}]})

    def test_stream_rejects_length_finish_reason(self):
        class FakeResponse:
            headers = {"content-type": "text/event-stream"}
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def __iter__(self):
                return iter([b'data: {"choices":[{"delta":{"content":"partial"},"finish_reason":"length"}]}\n', b'data: [DONE]\n'])
        with patch.object(api.urllib.request, "urlopen", return_value=FakeResponse()):
            with self.assertRaises(api.StoryboardFormatError):
                api.request_model("https://example.test/v1", "key", "model", [{"role": "user", "content": "x"}], stream=True, attempts=1)

    def test_saved_key_can_only_be_used_with_saved_base_url(self):
        self.assertEqual(api.resolve_discovery_credentials("https://saved.test/v1", "", "https://saved.test/v1", "secret"), ("https://saved.test/v1", "secret"))
        with self.assertRaises(ValueError):
            api.resolve_discovery_credentials("https://evil.test/v1", "", "https://saved.test/v1", "secret")
        self.assertEqual(api.resolve_discovery_credentials("https://evil.test/v1", "provided", "https://saved.test/v1", "secret"), ("https://evil.test/v1", "provided"))

    def test_stream_length_remains_truncated_after_later_stop(self):
        class FakeResponse:
            headers = {"content-type": "text/event-stream"}
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def __iter__(self):
                return iter([
                    b'data: {"choices":[{"delta":{"content":"partial"},"finish_reason":"length"}]}\n',
                    b'data: {"choices":[{"delta":{},"finish_reason":"stop"}]}\n',
                    b'data: [DONE]\n',
                ])
        with patch.object(api.urllib.request, "urlopen", return_value=FakeResponse()):
            with self.assertRaises(api.StoryboardFormatError):
                api.request_model("https://example.test/v1", "key", "model", [{"role": "user", "content": "x"}], stream=True, attempts=1)


if __name__ == "__main__":
    unittest.main()
