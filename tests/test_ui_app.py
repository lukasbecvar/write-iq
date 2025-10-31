#!/usr/bin/python3
import os
import unittest
from unittest.mock import MagicMock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtGui import QCloseEvent
from src.ui import TextHelperApp, AppMode
from src.models import AppConfig, UserSettings
from src.constants import DEFAULT_LANGUAGE_CODE
from PyQt6.QtWidgets import QApplication, QDialog
from src.services.gemini_service import GeminiAPIError

class DummySignal:
    def __init__(self):
        self._callback = None

    def connect(self, callback):
        self._callback = callback

    def emit(self, *args, **kwargs):
        if self._callback:
            self._callback(*args, **kwargs)

class DummyWorker:
    def __init__(self, chunk_text="Gemini chunk"):
        self.partial = DummySignal()
        self.error = DummySignal()
        self.finished = DummySignal()
        self.chunk_text = chunk_text
        self.started = False
        self.deleted = False
        self._running = False

    def isRunning(self):
        return self._running

    def start(self):
        self.started = True
        self._running = True
        self.partial.emit(self.chunk_text)
        self._running = False
        self.finished.emit()

    def deleteLater(self):
        self.deleted = True

    def requestInterruption(self):
        self._running = False

class TextHelperAppTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._qapp = QApplication.instance() or QApplication([])

    def setUp(self):
        self.qtimer_patcher = patch("src.ui.QTimer.singleShot", new=lambda *args, **kwargs: None)
        self.qtimer_patcher.start()
        self.addCleanup(self.qtimer_patcher.stop)

        config = AppConfig(api_key="", settings=UserSettings(default_language="cs"))
        self.window = TextHelperApp(config=config)
        self.addCleanup(self.window.close)

    def test_build_prompt_switches_with_mode(self):
        grammar_prompt = self.window._build_prompt("Please fix me.")
        self.assertIn("expert proofreader", grammar_prompt)
        self.assertTrue(grammar_prompt.strip().endswith("Please fix me."))

        self.window.on_mode_translate()
        self.assertEqual(self.window.mode, AppMode.TRANSLATE)
        translate_prompt = self.window._build_prompt("Hello world")
        self.assertIn("Translate the following text into", translate_prompt)
        self.assertIn("Czech", translate_prompt)

    def test_clear_all_clears_text_and_status(self):
        self.window.input_edit.setPlainText("Input text")
        self.window.output_edit.setPlainText("Output text")
        self.window.clear_all()
        self.assertEqual(self.window.input_edit.toPlainText(), "")
        self.assertEqual(self.window.output_edit.toPlainText(), "")
        self.assertEqual(self.window.status_label.text(), "Cleared.")
        self.assertFalse(self.window.copy_btn.isEnabled())

    def test_reset_copy_btn_respects_output_content(self):
        self.window.copy_btn.setEnabled(False)
        self.window.output_edit.setPlainText("Result")
        self.window.reset_copy_btn()
        self.assertTrue(self.window.copy_btn.isEnabled())
        self.window.output_edit.clear()
        self.window.reset_copy_btn()
        self.assertFalse(self.window.copy_btn.isEnabled())

    def test_set_language_selection_falls_back_to_default(self):
        self.window._set_language_selection("xx")
        self.assertEqual(self.window.lang_combo.currentData(), DEFAULT_LANGUAGE_CODE)

    def test_on_submit_requires_active_service(self):
        with patch("src.ui.QMessageBox.warning") as mock_warning:
            self.window.open_settings = MagicMock()
            self.window.gemini_service = None
            self.window.on_submit()

        mock_warning.assert_called_once()
        self.window.open_settings.assert_called_once_with(require_key=True)

    def test_on_submit_guard_clause_for_running_worker(self):
        self.window.gemini_service = MagicMock()
        self.window.gemini_service.get_stream_worker = MagicMock()

        class RunningWorker:
            def __init__(self):
                self.interrupted = False

            def isRunning(self):
                return True

            def requestInterruption(self):
                self.interrupted = True

            def wait(self, _timeout):
                return True

        self.window.worker = RunningWorker()
        with patch("src.ui.QMessageBox.information") as mock_info:
            self.window.on_submit()
        mock_info.assert_called_once()
        self.window.gemini_service.get_stream_worker.assert_not_called()

    def test_on_submit_with_empty_input_sets_warning_output(self):
        class NoOpService:
            def get_stream_worker(self, _prompt):
                raise AssertionError("Should not build worker for empty input")

        self.window.gemini_service = NoOpService()
        self.window.input_edit.setPlainText("   ")

        self.window.on_submit()

        self.assertEqual(self.window.output_edit.toPlainText(), "⚠️ No input text.")
        self.assertTrue(self.window.copy_btn.isEnabled())
        self.assertEqual(self.window.copy_btn.text(), "📋 Copy")
        self.assertEqual(self.window.status_label.text(), "Ready.")

    def test_on_submit_streams_and_enables_copy(self):
        dummy_worker = DummyWorker("Processed text")

        class CapturingService:
            def __init__(self):
                self.prompts = []

            def get_stream_worker(self, prompt):
                self.prompts.append(prompt)
                return dummy_worker

        service = CapturingService()
        self.window.gemini_service = service
        self.window.input_edit.setPlainText("Sample sentence.")

        self.window.on_submit()

        self.assertTrue(dummy_worker.started)
        self.assertTrue(dummy_worker.deleted)
        self.assertIsNone(self.window.worker)
        self.assertIn("Sample sentence.", service.prompts[0])
        self.assertEqual(self.window.output_edit.toPlainText(), "Processed text")
        self.assertEqual(self.window.status_label.text(), "Completed.")
        self.assertTrue(self.window.copy_btn.isEnabled())

    def test_copy_output_sets_clipboard_and_updates_button(self):
        self.window.output_edit.setPlainText("Translated text")
        fake_clipboard = MagicMock()

        with patch("src.ui.QApplication.clipboard", return_value=fake_clipboard):
            self.window.copy_output()

        fake_clipboard.setText.assert_called_once_with("Translated text")
        self.assertEqual(self.window.copy_btn.text(), "✅ Copied")
        self.assertFalse(self.window.copy_btn.isEnabled())

    def test_copy_output_with_empty_text_disables_button(self):
        self.window.output_edit.clear()
        self.window.copy_btn.setEnabled(True)

        with patch("src.ui.QApplication.clipboard") as mock_clipboard:
            self.window.copy_output()

        mock_clipboard.assert_not_called()
        self.assertEqual(self.window.copy_btn.text(), "📋 Copy")
        self.assertFalse(self.window.copy_btn.isEnabled())

    def test_on_worker_error_updates_output_and_status(self):
        with patch("src.ui.QMessageBox.critical") as mock_critical:
            self.window.on_worker_error("Gemini failed")

        self.assertEqual(self.window.output_edit.toPlainText(), "⚠️ Gemini failed")
        self.assertEqual(self.window.status_label.text(), "⚠️ Gemini failed")
        mock_critical.assert_called_once()
        self.assertEqual(self.window._last_error_message, "Gemini failed")

    def test_on_finished_handles_error_message(self):
        dummy_worker = DummyWorker()
        self.window.worker = dummy_worker
        self.window._last_error_message = "Timeout"
        self.window.output_edit.clear()

        self.window.on_finished()

        self.assertTrue(dummy_worker.deleted)
        self.assertIsNone(self.window.worker)
        self.assertEqual(self.window.status_label.text(), "⚠️ Timeout")
        self.assertFalse(self.window.copy_btn.isEnabled())
        self.assertIsNone(self.window._last_error_message)

    def test_on_finished_without_output_sets_status(self):
        dummy_worker = DummyWorker()
        self.window.worker = dummy_worker
        self.window.output_edit.clear()

        self.window.on_finished()

        self.assertTrue(dummy_worker.deleted)
        self.assertIsNone(self.window.worker)
        self.assertEqual(self.window.status_label.text(), "No response received.")
        self.assertFalse(self.window.copy_btn.isEnabled())

    def test_close_event_interrupts_threads(self):
        class RunningThread:
            def __init__(self):
                self.interrupted = False
                self.wait_called = False

            def isRunning(self):
                return True

            def requestInterruption(self):
                self.interrupted = True

            def wait(self, _timeout):
                self.wait_called = True
                return True

        worker = RunningThread()
        validator = RunningThread()
        self.window.worker = worker
        self.window._key_validator = validator

        event = QCloseEvent()
        self.window.closeEvent(event)

        self.assertTrue(worker.interrupted)
        self.assertTrue(worker.wait_called)
        self.assertIsNone(self.window.worker)
        self.assertTrue(validator.interrupted)
        self.assertTrue(validator.wait_called)
        self.assertIsNone(self.window._key_validator)

    def test_apply_settings_handles_activation_failure(self):
        payload = {
            "api_key": "new-key",
            "default_language": "fr",
            "model_name": "gemini-2.5-pro",
        }
        original_language = self.window.settings.default_language

        with patch.object(TextHelperApp, "_activate_service", return_value=False) as mock_activate, patch(
            "src.ui.QMessageBox.critical"
        ) as mock_critical, patch("src.ui.save_config") as mock_save:
            self.window._apply_settings(payload)

        mock_activate.assert_called_once_with("new-key", "gemini-2.5-pro")
        mock_critical.assert_called_once()
        mock_save.assert_not_called()
        self.assertEqual(self.window.settings.default_language, original_language)
        self.assertEqual(self.window.config.api_key, "")
        self.assertEqual(self.window.status_label.text(), "Ready.")

    def test_apply_settings_persists_configuration(self):
        payload = {
            "api_key": "key-123",
            "default_language": "de",
            "model_name": "gemini-1.5-pro",
        }

        with patch.object(TextHelperApp, "_activate_service", return_value=True) as mock_activate, patch(
            "src.ui.save_config"
        ) as mock_save:
            self.window._apply_settings(payload)

        mock_activate.assert_called_once_with("key-123", "gemini-1.5-pro")
        mock_save.assert_called_once_with(self.window.config)
        self.assertEqual(self.window.config.api_key, "key-123")
        self.assertEqual(self.window.settings.default_language, "de")
        self.assertEqual(self.window.settings.model_name, "gemini-1.5-pro")
        self.assertEqual(self.window.config.settings.default_language, "de")
        self.assertEqual(self.window.config.settings.model_name, "gemini-1.5-pro")
        self.assertEqual(self.window.status_label.text(), "Settings saved.")

    def test_handle_settings_validation_wires_success_callback(self):
        payload = {
            "api_key": "api-key-1",
            "default_language": "cs",
            "model_name": "gemini-2.5-pro",
        }
        dialog = MagicMock()

        validators = []

        class DummyValidator:
            def __init__(self, api_key, model_name):
                self.api_key = api_key
                self.model_name = model_name
                self.success = DummySignal()
                self.failure = DummySignal()

        def make_validator(api_key, model_name):
            instance = DummyValidator(api_key, model_name)
            validators.append(instance)
            return instance

        with patch("src.ui.GeminiKeyValidator", side_effect=make_validator), patch.object(
            self.window, "_start_validator"
        ) as mock_start:
            self.window._handle_settings_validation(dialog, payload)

        self.assertEqual(len(validators), 1)
        validator = validators[0]
        self.assertEqual(validator.api_key, "api-key-1")
        self.assertEqual(validator.model_name, "gemini-2.5-pro")
        mock_start.assert_called_once_with(validator)

        validator.success.emit("api-key-1")
        dialog.mark_validation_success.assert_called_once_with(payload)
        self.assertEqual(self.window.status_label.text(), "API key validated.")

    def test_handle_settings_validation_wires_failure_callback(self):
        payload = {
            "api_key": "api-key-2",
            "default_language": "en",
            "model_name": "gemini-2.5-flash",
        }
        dialog = MagicMock()

        validators = []

        class DummyValidator:
            def __init__(self, api_key, model_name):
                self.api_key = api_key
                self.model_name = model_name
                self.success = DummySignal()
                self.failure = DummySignal()

        def make_validator(api_key, model_name):
            instance = DummyValidator(api_key, model_name)
            validators.append(instance)
            return instance

        with patch("src.ui.GeminiKeyValidator", side_effect=make_validator), patch.object(
            self.window, "_start_validator"
        ):
            self.window._handle_settings_validation(dialog, payload)

        validator = validators[0]
        validator.failure.emit("invalid key")
        dialog.mark_validation_failure.assert_called_once_with("invalid key")
        self.assertEqual(self.window.status_label.text(), "⚠️ invalid key")

    def test_activate_service_success_updates_state(self):
        service_instance = MagicMock(name="gemini_service_instance")

        with patch("src.ui.GeminiService", return_value=service_instance) as mock_service:
            result = self.window._activate_service("fresh-key", "gemini-2.5-pro")

        self.assertTrue(result)
        mock_service.assert_called_once_with("fresh-key", model_name="gemini-2.5-pro")
        self.assertIs(self.window.gemini_service, service_instance)
        self.assertEqual(self.window.api_key, "fresh-key")
        self.assertEqual(self.window.settings.model_name, "gemini-2.5-pro")

    def test_activate_service_failure_sets_status_and_clears_state(self):
        self.window.gemini_service = MagicMock()

        with patch(
            "src.ui.GeminiService", side_effect=GeminiAPIError("bad key")
        ) as mock_service:
            result = self.window._activate_service("bad", "model-x")

        self.assertFalse(result)
        mock_service.assert_called_once_with("bad", model_name="model-x")
        self.assertIsNone(self.window.gemini_service)
        self.assertEqual(self.window.status_label.text(), "⚠️ bad key")
        self.assertEqual(self.window.api_key, "")
        self.assertEqual(self.window.settings.model_name, "gemini-2.5-flash")

    def test_init_services_with_api_key_starts_validator(self):
        self.window.api_key = "stored-api"
        self.window.settings.model_name = "gemini-2.5-pro"
        fake_validator = MagicMock()

        with patch("src.ui.GeminiKeyValidator", return_value=fake_validator) as mock_validator, patch.object(
            self.window, "_start_validator"
        ) as mock_start:
            self.window._init_services()

        mock_validator.assert_called_once_with("stored-api", "gemini-2.5-pro")
        mock_start.assert_called_once_with(fake_validator)
        self.assertEqual(self.window.status_label.text(), "Validating stored API key…")

    def test_init_services_without_api_key_prompts_status(self):
        self.window.api_key = ""

        with patch.object(self.window, "open_settings") as mock_open_settings:
            self.window._init_services()

        self.assertEqual(self.window.status_label.text(), "API key required. Open settings to continue.")
        mock_open_settings.assert_not_called()

    def test_on_startup_key_failed_prompts_user(self):
        with patch("src.ui.QMessageBox.warning") as mock_warning, patch.object(
            self.window, "open_settings"
        ) as mock_open_settings:
            self.window._on_startup_key_failed("Invalid key")

        mock_warning.assert_called_once()
        mock_open_settings.assert_called_once_with(require_key=True)
        self.assertEqual(self.window.status_label.text(), "⚠️ Invalid key")

    def test_on_worker_error_appends_when_output_exists(self):
        self.window.output_edit.setPlainText("Initial result")

        with patch("src.ui.QMessageBox.critical"):
            self.window.on_worker_error("Gemini failed again")

        output_lines = self.window.output_edit.toPlainText().splitlines()
        self.assertEqual(output_lines[0], "Initial result")
        self.assertEqual(output_lines[-1], "⚠️ Gemini failed again")
        self.assertEqual(self.window.status_label.text(), "⚠️ Gemini failed again")

    def test_update_output_sets_streaming_status_and_appends(self):
        self.window.output_edit.clear()

        self.window.update_output("First chunk ")
        self.window.update_output("Second chunk")

        self.assertEqual(self.window.output_edit.toPlainText(), "First chunk Second chunk")
        self.assertEqual(self.window.status_label.text(), "Streaming response…")

    def test_open_settings_requires_key_shows_error_and_closes(self):
        self.window.gemini_service = None
        self.window.api_key = ""
        original_close = self.window.close
        close_mock = MagicMock()
        self.window.close = close_mock
        self.addCleanup(lambda: setattr(self.window, "close", original_close))

        class DummySettingsDialog:
            def __init__(self, *args, **kwargs):
                self.validation_requested = DummySignal()
                self.final_settings = None

            def exec(self):
                return QDialog.DialogCode.Rejected

        dialog_instance = DummySettingsDialog()

        with patch("src.ui.SettingsDialog", return_value=dialog_instance) as mock_dialog, patch(
            "src.ui.QMessageBox.critical"
        ) as mock_critical:
            self.window.open_settings(require_key=True)

        mock_dialog.assert_called_once_with(settings=self.window.settings, api_key="", parent=self.window)
        mock_critical.assert_called_once()
        close_mock.assert_called_once()

if __name__ == "__main__":
    unittest.main()
