#!/usr/bin/python3
import os
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from src.constants import DEFAULT_LANGUAGE_CODE, MODEL_OPTIONS
from PyQt6.QtWidgets import QApplication, QDialog
from src.dialogs import SettingsDialog
from src.models import UserSettings

class SettingsDialogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._app = QApplication.instance() or QApplication([])

    def setUp(self):
        settings = UserSettings(default_language="cs", model_name=MODEL_OPTIONS[1][0])
        self.dialog = SettingsDialog(settings=settings, api_key="existing-key", parent=None)
        self.addCleanup(self.dialog.close)

    def test_set_settings_falls_back_to_defaults(self):
        self.dialog.set_settings(UserSettings(default_language="xx", model_name="unknown"), "  new-key  ")
        self.assertEqual(self.dialog.api_key_input.text(), "  new-key  ")
        self.assertEqual(self.dialog.lang_combo.currentData(), DEFAULT_LANGUAGE_CODE)
        self.assertEqual(self.dialog.model_combo.currentData(), MODEL_OPTIONS[0][0])

    def test_get_settings_returns_trimmed_payload(self):
        self.dialog.api_key_input.setText("  updated-key  ")
        self.dialog.lang_combo.setCurrentIndex(2)
        self.dialog.model_combo.setCurrentIndex(1)

        expected_language = self.dialog.lang_combo.currentData()
        expected_model = self.dialog.model_combo.currentData()

        payload = self.dialog.get_settings()

        self.assertEqual(payload["api_key"], "updated-key")
        self.assertEqual(payload["default_language"], expected_language)
        self.assertEqual(payload["model_name"], expected_model)

    def test_on_save_clicked_without_api_key_shows_warning(self):
        self.dialog.api_key_input.clear()
        with patch("src.dialogs.QMessageBox.warning") as mock_warning:
            self.dialog._on_save_clicked()
        mock_warning.assert_called_once()
        self.assertIsNone(self.dialog.final_settings)

    def test_on_save_clicked_emits_validation_and_toggles_busy_state(self):
        captured = []
        self.dialog.validation_requested.connect(lambda payload: captured.append(payload))
        self.dialog.api_key_input.setText("new-key")
        self.dialog.lang_combo.setCurrentIndex(0)
        self.dialog.model_combo.setCurrentIndex(0)

        self.dialog._on_save_clicked()

        self.assertEqual(len(captured), 1)
        payload = captured[0]
        self.assertFalse(self.dialog.api_key_input.isEnabled())
        self.assertFalse(self.dialog.lang_combo.isEnabled())
        self.assertFalse(self.dialog.model_combo.isEnabled())
        self.assertFalse(self.dialog.save_btn.isEnabled())
        self.assertTrue(self.dialog.status_label.text().startswith("Validating API key"))
        self.assertEqual(payload["api_key"], "new-key")

        self.dialog.mark_validation_failure("bad key")
        self.assertTrue(self.dialog.api_key_input.isEnabled())
        self.assertEqual(self.dialog.status_label.text(), "⚠️ bad key")

    def test_mark_validation_success_records_final_settings(self):
        payload = {"api_key": "key-123", "default_language": "cs", "model_name": MODEL_OPTIONS[0][0]}
        with patch.object(QDialog, "accept") as mock_accept:
            self.dialog.mark_validation_success(payload)

        self.assertIs(self.dialog.final_settings, payload)
        self.assertEqual(self.dialog.status_label.text(), "✅ API key validated.")
        mock_accept.assert_called_once()

if __name__ == "__main__":
    unittest.main()
