"""
Handles interactions with the Google Generative AI (Gemini) API.
"""

from __future__ import annotations

import logging
import google.generativeai as genai
from PyQt6.QtCore import QThread, pyqtSignal
from src.constants import DEFAULT_MODEL_NAME

logger = logging.getLogger(__name__)

class GeminiAPIError(Exception):
    """Raised when the Gemini service reports an error that should reach the UI."""

def _configure_client(api_key: str) -> None:
    if not api_key:
        raise GeminiAPIError("API key is empty.")
    genai.configure(api_key=api_key)

class GeminiStreamWorker(QThread):
    """
    Streams responses from the Gemini API without blocking the UI thread.
    """

    partial = pyqtSignal(str)
    error = pyqtSignal(str)
    finished = pyqtSignal()

    def __init__(self, service: "GeminiService", prompt: str):
        super().__init__()
        self.service = service
        self.prompt = prompt

    def run(self) -> None:
        try:
            for chunk in self.service.stream_prompt(self.prompt):
                self.partial.emit(chunk)
        except Exception as exc:
            logger.exception("Gemini stream failed: %s", exc)
            self.error.emit(str(exc))
        finally:
            self.finished.emit()

class GeminiKeyValidator(QThread):
    """
    Validates Gemini API keys asynchronously.
    """

    success = pyqtSignal(str)
    failure = pyqtSignal(str)

    def __init__(self, api_key: str, model_name: str = DEFAULT_MODEL_NAME):
        super().__init__()
        self.api_key = api_key.strip()
        self.model_name = model_name

    def run(self) -> None:
        try:
            GeminiService.validate_api_key(self.api_key, model_name=self.model_name)
        except GeminiAPIError as exc:
            logger.warning("Gemini API key validation failed: %s", exc)
            self.failure.emit(str(exc))
        except Exception as exc:
            logger.exception("Unexpected error during API key validation: %s", exc)
            self.failure.emit(f"Unexpected error: {exc}")
        else:
            logger.info("Gemini API key validated using model %s", self.model_name)
            self.success.emit(self.api_key)

class GeminiService:
    """
    Thin wrapper around the Gemini Generative AI model.
    """

    def __init__(self, api_key: str, model_name: str = DEFAULT_MODEL_NAME):
        _configure_client(api_key)
        self.api_key = api_key
        self.model_name = model_name
        self.model = genai.GenerativeModel(model_name)

    def get_stream_worker(self, prompt: str) -> GeminiStreamWorker:
        """
        Returns a worker to stream a response for the given prompt.
        """
        return GeminiStreamWorker(self, prompt)

    def stream_prompt(self, prompt: str):
        """
        Streams text chunks for the provided prompt.
        """
        response = self.model.generate_content(prompt, stream=True)
        try:
            for chunk in response:
                if text := getattr(chunk, "text", None):
                    yield text
        finally:
            try:
                response.resolve()
            except Exception:
                pass

    @staticmethod
    def validate_api_key(key: str, *, model_name: str = DEFAULT_MODEL_NAME) -> None:
        """
        Validates the given Gemini API key by making a lightweight API call.
        """
        try:
            _configure_client(key)
            model = genai.GenerativeModel(model_name)
            model.generate_content("ping", stream=False)
            logger.debug("Gemini API key validation succeeded for model %s", model_name)
        except Exception as exc:
            logger.error("Gemini API key validation failed for model %s: %s", model_name, exc)
            raise GeminiAPIError(str(exc)) from exc
