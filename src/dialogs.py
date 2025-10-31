"""
Defines the dialog boxes used in the WriteIQ application.
"""

from __future__ import annotations

from typing import Optional
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QLineEdit,
    QComboBox,
    QDialog,
    QLabel
)

from src.constants import (
    LANGUAGE_LABEL_BY_CODE,
    DEFAULT_LANGUAGE_CODE,
    MODEL_LABEL_BY_NAME,
    LANGUAGE_OPTIONS,
    MODEL_OPTIONS
)
from src.models import UserSettings

class SettingsDialog(QDialog):
    """
    Settings dialog allowing users to configure the Gemini API key and defaults.
    """

    validation_requested = pyqtSignal(dict)

    def __init__(self, settings: UserSettings, api_key: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setFixedSize(420, 320)
        self.setModal(True)

        self._initial_api_key = api_key.strip()
        self._final_settings: Optional[dict] = None

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(20, 20, 20, 20)
        self.layout.setSpacing(12)

        # api key input
        self.api_key_label = QLabel("Gemini API Key")
        self.api_key_input = QLineEdit()
        self.api_key_input.setPlaceholderText("Enter your Gemini API key...")
        self.layout.addWidget(self.api_key_label)
        self.layout.addWidget(self.api_key_input)

        # default language selector
        self.lang_label = QLabel("Default Translation Language")
        self.lang_combo = QComboBox()
        for label, code in LANGUAGE_OPTIONS:
            self.lang_combo.addItem(label, userData=code)
        self.layout.addWidget(self.lang_label)
        self.layout.addWidget(self.lang_combo)

        # model selector
        self.model_label = QLabel("Gemini Model")
        self.model_combo = QComboBox()
        for model_name, model_label in MODEL_OPTIONS:
            self.model_combo.addItem(model_label, userData=model_name)
        self.layout.addWidget(self.model_label)
        self.layout.addWidget(self.model_combo)

        # status area
        self.status_label = QLabel()
        self.status_label.setObjectName("settingsStatusLabel")
        self.status_label.setStyleSheet("color: rgba(255, 255, 255, 0.6); font-size: 12px;")
        self.layout.addWidget(self.status_label)

        # dialog buttons
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()
        self.save_btn = QPushButton("Save")
        self.cancel_btn = QPushButton("Cancel")
        buttons_layout.addWidget(self.save_btn)
        buttons_layout.addWidget(self.cancel_btn)
        self.layout.addLayout(buttons_layout)

        self.cancel_btn.clicked.connect(self.reject)
        self.save_btn.clicked.connect(self._on_save_clicked)
        self.set_settings(settings, api_key)

    @property
    def final_settings(self) -> Optional[dict]:
        return self._final_settings

    def set_settings(self, settings: UserSettings, api_key: str) -> None:
        self.status_label.clear()
        self.api_key_input.setText(api_key)
        language_code = settings.default_language or DEFAULT_LANGUAGE_CODE
        index = self.lang_combo.findData(language_code)
        if index != -1:
            self.lang_combo.setCurrentIndex(index)
        else:
            default_index = self.lang_combo.findData(DEFAULT_LANGUAGE_CODE)
            if default_index != -1:
                self.lang_combo.setCurrentIndex(default_index)

        model_index = self.model_combo.findData(settings.model_name)
        if model_index != -1:
            self.model_combo.setCurrentIndex(model_index)
        else:
            self.model_combo.setCurrentIndex(0)

    def get_settings(self) -> dict:
        return {
            "api_key": self.api_key_input.text().strip(),
            "default_language": self.lang_combo.currentData() or DEFAULT_LANGUAGE_CODE,
            "model_name": self.model_combo.currentData() or MODEL_OPTIONS[0][0],
        }

    def mark_validation_success(self, settings: dict) -> None:
        self._final_settings = settings
        self.status_label.setText("✅ API key validated.")
        super().accept()

    def mark_validation_failure(self, message: str) -> None:
        self._set_busy(False)
        self.status_label.setText(f"⚠️ {message}")

    def show_validation_in_progress(self) -> None:
        self._set_busy(True)
        if not self.status_label.text():
            self.status_label.setText("Validating API key…")

    def _set_busy(self, busy: bool) -> None:
        self.api_key_input.setEnabled(not busy)
        self.lang_combo.setEnabled(not busy)
        self.model_combo.setEnabled(not busy)
        self.save_btn.setEnabled(not busy)
        self.cancel_btn.setEnabled(not busy)

    def _on_save_clicked(self) -> None:
        settings = self.get_settings()
        api_key = settings["api_key"]
        if not api_key:
            QMessageBox.warning(self, "Missing API Key", "Please enter a Gemini API key.")
            self.api_key_input.setFocus()
            return

        if api_key == self._initial_api_key:
            if api_key:
                self.status_label.setText("")
                self._final_settings = settings
                super().accept()
                return

        human_label = LANGUAGE_LABEL_BY_CODE.get(settings["default_language"])
        model_label = MODEL_LABEL_BY_NAME.get(settings["model_name"], settings["model_name"])
        if human_label:
            self.status_label.setText(
                f"Validating API key for {human_label} translations on {model_label}…"
            )
        else:
            self.status_label.setText(f"Validating API key on {model_label}…")
        self.show_validation_in_progress()
        self.validation_requested.emit(settings)
