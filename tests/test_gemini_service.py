#!/usr/bin/python3
import types
import unittest
from unittest.mock import MagicMock, patch

from src.services.gemini_service import (
    GeminiStreamWorker,
    GeminiKeyValidator,
    _configure_client,
    GeminiAPIError,
    GeminiService
)

class GeminiServiceTests(unittest.TestCase):
    def test_configure_client_rejects_empty_key(self):
        with self.assertRaises(GeminiAPIError):
            _configure_client("")

    def test_validate_api_key_invokes_generative_model(self):
        with patch("src.services.gemini_service.genai.configure") as mock_configure, patch(
            "src.services.gemini_service.genai.GenerativeModel"
        ) as mock_model:
            model_instance = MagicMock()
            mock_model.return_value = model_instance
            GeminiService.validate_api_key("my-key", model_name="model-x")
            mock_configure.assert_called_once_with(api_key="my-key")
            model_instance.generate_content.assert_called_once_with("ping", stream=False)

    def test_validate_api_key_propagates_errors(self):
        with patch("src.services.gemini_service.genai.configure"), patch(
            "src.services.gemini_service.genai.GenerativeModel"
        ) as mock_model:
            model_instance = MagicMock()
            model_instance.generate_content.side_effect = RuntimeError("bad key")
            mock_model.return_value = model_instance
            with self.assertRaises(GeminiAPIError):
                GeminiService.validate_api_key("bad-key")

    def test_stream_prompt_yields_chunks_and_resolves(self):
        chunk_a = types.SimpleNamespace(text="Hello ")
        chunk_b = types.SimpleNamespace(text=None)
        chunk_c = types.SimpleNamespace(text="world!")

        class FakeResponse:
            def __init__(self, chunks):
                self._chunks = chunks
                self.resolved = False

            def __iter__(self):
                return iter(self._chunks)

            def resolve(self):
                self.resolved = True

        fake_response = FakeResponse([chunk_a, chunk_b, chunk_c])

        with patch("src.services.gemini_service.genai.configure"), patch(
            "src.services.gemini_service.genai.GenerativeModel"
        ) as mock_model:
            model_instance = MagicMock()
            model_instance.generate_content.return_value = fake_response
            mock_model.return_value = model_instance

            service = GeminiService(api_key="key-123", model_name="model-y")
            chunks = list(service.stream_prompt("prompt"))

        self.assertEqual(chunks, ["Hello ", "world!"])
        self.assertTrue(fake_response.resolved)
        model_instance.generate_content.assert_called_once_with("prompt", stream=True)

    def test_get_stream_worker_binds_service_and_prompt(self):
        with patch("src.services.gemini_service.genai.configure"), patch(
            "src.services.gemini_service.genai.GenerativeModel"
        ) as mock_model:
            mock_model.return_value = MagicMock()
            service = GeminiService(api_key="abc", model_name="model")

        worker = service.get_stream_worker("Prompt text")
        self.assertIsInstance(worker, GeminiStreamWorker)
        self.assertIs(worker.service, service)
        self.assertEqual(worker.prompt, "Prompt text")

    def test_stream_worker_emits_chunks_and_finishes(self):
        class DummyService:
            def stream_prompt(self, prompt):
                yield "chunk-1"
                yield "chunk-2"

        service = DummyService()
        worker = GeminiStreamWorker(service, "Prompt")
        emitted = []
        ended = []

        worker.partial.connect(emitted.append)
        worker.error.connect(lambda message: emitted.append(f"error:{message}"))
        worker.finished.connect(lambda: ended.append(True))

        worker.run()

        self.assertEqual(emitted, ["chunk-1", "chunk-2"])
        self.assertTrue(ended)

    def test_stream_worker_emits_error_and_still_finishes(self):
        class FailingService:
            def stream_prompt(self, prompt):
                raise RuntimeError("boom")

        service = FailingService()
        worker = GeminiStreamWorker(service, "Prompt")
        errors = []
        ended = []

        worker.partial.connect(lambda _: errors.append("partial emitted"))
        worker.error.connect(errors.append)
        worker.finished.connect(lambda: ended.append(True))

        worker.run()

        self.assertEqual(errors, ["boom"])
        self.assertTrue(ended)

    def test_key_validator_emits_success(self):
        with patch.object(GeminiService, "validate_api_key", return_value=None) as mock_validate:
            validator = GeminiKeyValidator("  api-key  ", model_name="model-123")
            successes = []
            failures = []

            validator.success.connect(successes.append)
            validator.failure.connect(failures.append)

            validator.run()

        mock_validate.assert_called_once_with("api-key", model_name="model-123")
        self.assertEqual(successes, ["api-key"])
        self.assertEqual(failures, [])

    def test_key_validator_emits_failure_messages(self):
        with patch.object(
            GeminiService,
            "validate_api_key",
            side_effect=GeminiAPIError("bad key"),
        ) as mock_validate:
            validator = GeminiKeyValidator("bad", model_name="model-x")
            successes = []
            failures = []

            validator.success.connect(successes.append)
            validator.failure.connect(failures.append)

            validator.run()

        mock_validate.assert_called_once_with("bad", model_name="model-x")
        self.assertEqual(successes, [])
        self.assertEqual(failures, ["bad key"])

if __name__ == "__main__":
    unittest.main()
