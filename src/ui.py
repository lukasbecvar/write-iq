"""
Defines the main user interface for the WriteIQ application.
"""

from __future__ import annotations

import sys
import logging
from enum import Enum
from typing import Optional

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QTextEdit,
    QComboBox,
    QDialog,
    QWidget,
    QFrame,
    QLabel
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QCloseEvent
from src.config import AppConfig, save_config
from src.constants import DEFAULT_LANGUAGE_CODE, LANGUAGE_OPTIONS
from src.dialogs import SettingsDialog
from src.models import Language, UserSettings
from src.prompts import build_grammar_prompt, build_translation_prompt
from src.ui_state import UIStateManager
from src.services.gemini_service import (
    GeminiStreamWorker,
    GeminiKeyValidator,
    GeminiAPIError,
    GeminiService
)

class AppMode(str, Enum):
    GRAMMAR = "fix"
    TRANSLATE = "translate"

class TextHelperApp(QWidget):
    """
    The main application window for WriteIQ.
    """

    def __init__(self, config: AppConfig):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.config: AppConfig = config
        self.settings: UserSettings = config.settings or UserSettings()
        self.api_key: str = (config.api_key or "").strip()
        self.gemini_service: Optional[GeminiService] = None
        self.worker: Optional[GeminiStreamWorker] = None
        self._key_validator: Optional[GeminiKeyValidator] = None
        self.mode: AppMode = AppMode.GRAMMAR
        self._last_error_message: Optional[str] = None

        self.setWindowTitle("WriteIQ")
        self.setWindowIcon(QIcon("src/assets/icon.png"))
        self.resize(650, 700)

        self._init_ui()
        self.apply_styles()
        self._tighten_scrollbars(self.input_edit)
        self._tighten_scrollbars(self.output_edit)
        self.update_mode_visuals()
        self.center_on_screen()

        QTimer.singleShot(0, self._init_services)

    def _init_services(self) -> None:
        if self.api_key:
            self._set_status("Validating stored API key…")
            validator = GeminiKeyValidator(self.api_key, self.settings.model_name)
            validator.success.connect(self._on_startup_key_validated)
            validator.failure.connect(self._on_startup_key_failed)
            self._start_validator(validator)
            self.logger.info(
                "Validating stored API key with model %s",
                self.settings.model_name,
            )
        else:
            self._set_status("API key required. Open settings to continue.")
            QTimer.singleShot(100, lambda: self.open_settings(require_key=True))

    def _init_ui(self):
        """Initializes the UI elements of the application."""
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(20, 20, 20, 20)
        self.layout.setSpacing(12)

        # header
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)

        self.settings_btn = QPushButton("⚙️ Settings")
        self.settings_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.settings_btn.setFixedHeight(26)
        self.settings_btn.setStyleSheet(
            """
            QPushButton {
                background: transparent;
                color: rgba(200, 200, 200, 0.5);
                border: 1px solid #3a3a3a;
                border-radius: 5px;
                font-size: 12px;
                padding: 3px 8px;
            }
            QPushButton:hover { color: white; border-color: #555; }
        """
        )
        self.settings_btn.clicked.connect(self.open_settings)

        header_layout.addStretch()
        header_layout.addWidget(self.settings_btn)
        self.layout.addLayout(header_layout)

        # mode buttons
        self.mode_frame = QFrame()
        self.mode_layout = QHBoxLayout(self.mode_frame)
        self.mode_layout.setContentsMargins(0, 0, 0, 0)
        self.mode_layout.setSpacing(10)

        self.btn_fix = QPushButton("📝 Grammar")
        self.btn_translate = QPushButton("🌍 Translate")
        self.mode_layout.addWidget(self.btn_fix)
        self.mode_layout.addWidget(self.btn_translate)
        self.layout.addWidget(self.mode_frame)

        self.btn_fix.clicked.connect(self.on_mode_fix)
        self.btn_translate.clicked.connect(self.on_mode_translate)

        # language selector
        self.lang_layout = QHBoxLayout()
        self.lang_label = QLabel("Translate to:")
        self.lang_combo = QComboBox()
        for label, code in LANGUAGE_OPTIONS:
            self.lang_combo.addItem(label, userData=code)
        self.lang_combo.currentIndexChanged.connect(self._on_language_changed)
        self.lang_layout.addWidget(self.lang_label)
        self.lang_layout.addWidget(self.lang_combo)
        self.layout.addLayout(self.lang_layout)
        self.lang_label.hide()
        self.lang_combo.hide()

        # input
        self.input_edit = QTextEdit()
        self.input_edit.setPlaceholderText("Enter text here...")
        self.layout.addWidget(self.input_edit)

        # output header
        out_head = QHBoxLayout()
        out_head.addWidget(QLabel("Output:"))
        out_head.addStretch()
        self.copy_btn = QPushButton("📋 Copy")
        self.copy_btn.setFixedWidth(90)
        self.copy_btn.clicked.connect(self.copy_output)
        out_head.addWidget(self.copy_btn)
        self.layout.addLayout(out_head)

        # output
        self.output_edit = QTextEdit()
        self.output_edit.setReadOnly(True)
        self.output_edit.setPlaceholderText("Result will appear here...")
        self.layout.addWidget(self.output_edit)

        # submit controls
        submit_layout = QHBoxLayout()
        self.submit_btn = QPushButton("▶ Process")
        self.submit_btn.clicked.connect(self.on_submit)
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.clicked.connect(self.clear_all)
        submit_layout.addWidget(self.clear_btn)
        submit_layout.addWidget(self.submit_btn)
        self.layout.addLayout(submit_layout)

        # status
        self.status_label = QLabel()
        self.status_label.setObjectName("statusLabel")
        self.status_label.setStyleSheet("color: rgba(255, 255, 255, 0.6); font-size: 12px;")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.layout.addWidget(self.status_label)

        # initial state
        self.ui_state = UIStateManager(self.submit_btn, self.clear_btn, self.copy_btn, self.status_label)
        self._apply_user_settings()
        self.logger.debug(
            "Initialized UI with language=%s, model=%s",
            self.settings.default_language,
            self.settings.model_name,
        )

    def _apply_user_settings(self) -> None:
        self._set_language_selection(self.settings.default_language or DEFAULT_LANGUAGE_CODE)
        self.ui_state.set_ready()

    def _set_language_selection(self, language_code: str) -> None:
        index = self.lang_combo.findData(language_code)
        if index != -1:
            self.lang_combo.setCurrentIndex(index)
        else:
            fallback_index = self.lang_combo.findData(DEFAULT_LANGUAGE_CODE)
            if fallback_index != -1:
                self.lang_combo.setCurrentIndex(fallback_index)

    def _set_status(self, message: str) -> None:
        self.ui_state.set_status(message)

    def _start_validator(self, validator: GeminiKeyValidator) -> None:
        if self._key_validator and self._key_validator.isRunning():
            self._key_validator.requestInterruption()
        self._key_validator = validator

        def _cleanup():
            validator.deleteLater()
            if self._key_validator is validator:
                self._key_validator = None

        validator.finished.connect(_cleanup)
        validator.start()

    def _on_startup_key_validated(self, api_key: str) -> None:
        if self._activate_service(api_key, self.settings.model_name):
            self._set_status("Ready.")
            self.logger.info("Gemini service ready with model %s", self.settings.model_name)

    def _on_startup_key_failed(self, message: str) -> None:
        self._set_status(f"⚠️ {message}")
        QMessageBox.warning(
            self,
            "API Key Required",
            "The stored Gemini API key is invalid or expired. Please provide a new key.",
        )
        self.open_settings(require_key=True)
        self.logger.warning("Stored API key validation failed: %s", message)

    def _activate_service(self, api_key: str, model_name: str) -> bool:
        try:
            service = GeminiService(api_key, model_name=model_name)
        except GeminiAPIError as exc:
            self.gemini_service = None
            self._set_status(f"⚠️ {exc}")
            self.logger.error("Failed to initialize Gemini service: %s", exc)
            return False
        self.gemini_service = service
        self.api_key = api_key
        self.settings.model_name = model_name
        self.logger.debug("Gemini service activated with model %s", model_name)
        return True

    def _apply_settings(self, settings: dict) -> None:
        new_api_key = settings["api_key"]
        new_language = settings["default_language"]
        new_model = settings["model_name"]

        if (
            new_api_key != self.api_key
            or new_model != self.settings.model_name
            or not self.gemini_service
        ):
            if not self._activate_service(new_api_key, new_model):
                QMessageBox.critical(self, "Gemini Error", "Unable to initialize Gemini with the provided key.")
                return

        self.settings.default_language = new_language
        self.config.settings.default_language = new_language
        self.config.settings.model_name = new_model
        self._set_language_selection(new_language)

        self.config.api_key = new_api_key
        save_config(self.config)

        self._set_status("Settings saved.")
        self.logger.info(
            "Settings updated (language=%s, model=%s)",
            new_language,
            new_model,
        )

    def _handle_settings_validation(self, dialog: SettingsDialog, settings: dict) -> None:
        validator = GeminiKeyValidator(settings["api_key"], settings["model_name"])
        validator.success.connect(
            lambda key: self._on_settings_validation_success(dialog, settings, key)
        )
        validator.failure.connect(lambda message: self._on_settings_validation_failure(dialog, message))
        self._start_validator(validator)

    def _on_settings_validation_success(self, dialog: SettingsDialog, settings: dict, _: str) -> None:
        dialog.mark_validation_success(settings)
        self._set_status("API key validated.")
        self.logger.info("API key validated for model %s", settings["model_name"])

    def _on_settings_validation_failure(self, dialog: SettingsDialog, message: str) -> None:
        dialog.mark_validation_failure(message)
        self._set_status(f"⚠️ {message}")
        self.logger.warning("API key validation failed: %s", message)

    def clear_all(self):
        """Clears both the input and output text fields."""
        self.input_edit.clear()
        self.output_edit.clear()
        self.ui_state.mark_cleared()
        self.logger.debug("Cleared input/output editors")

    def _tighten_scrollbars(self, edit: QTextEdit):
        """Ensure scrollbars are flush to the border (no gaps)."""
        edit.setViewportMargins(0, 0, 0, 0)
        edit.document().setDocumentMargin(8)
        edit.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        edit.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

    def center_on_screen(self):
        """Centers the window on the primary screen."""
        screen = QApplication.primaryScreen()
        if not screen:
            return
        screen_geometry = screen.availableGeometry()
        x = (screen_geometry.width() - self.width()) // 2
        y = (screen_geometry.height() - self.height()) // 2
        self.move(x, y)

    def apply_styles(self):
        """Applies the dark theme stylesheet to the application."""
        try:
            with open("src/styles/dark_theme.qss", "r") as f:
                self.setStyleSheet(f.read())
        except FileNotFoundError:
            print("Stylesheet not found, using default styles.")

    def open_settings(self, require_key: bool = False):
        """Opens the settings dialog and updates the configuration if changed."""
        dialog = SettingsDialog(settings=self.settings, api_key=self.api_key, parent=self)
        dialog.validation_requested.connect(
            lambda payload: self._handle_settings_validation(dialog, payload)
        )

        result = dialog.exec()
        if result == QDialog.DialogCode.Accepted and dialog.final_settings:
            self._apply_settings(dialog.final_settings)
            return

        if require_key and (not self.gemini_service or not self.api_key):
            QMessageBox.critical(
                self,
                "API Key Required",
                "WriteIQ cannot run without a valid Gemini API key.",
            )
            self.close()
            self.logger.info("Application closed because API key was not provided")

    def update_mode_visuals(self):
        """Updates the visual style of the mode buttons to indicate the active mode."""
        inactive = "background-color: #2d2d2d; color: #bbb; border: 1px solid #3a3a3a;"
        active = "background-color: #0078d4; color: white; border: none;"
        if self.mode == AppMode.GRAMMAR:
            self.btn_fix.setStyleSheet(active)
            self.btn_translate.setStyleSheet(inactive)
        else:
            self.btn_translate.setStyleSheet(active)
            self.btn_fix.setStyleSheet(inactive)

    def on_mode_fix(self):
        """Switches the application to Grammar mode."""
        self.mode = AppMode.GRAMMAR
        self.lang_label.hide()
        self.lang_combo.hide()
        self.update_mode_visuals()
        self._set_status("Grammar mode active.")
        self.logger.debug("Mode switched to grammar")

    def on_mode_translate(self):
        """Switches the application to Translate mode."""
        self.mode = AppMode.TRANSLATE
        self.lang_label.show()
        self.lang_combo.show()
        self.update_mode_visuals()
        target_language = Language.from_code(self.lang_combo.currentData())
        self._set_status(f"Translate mode to {target_language.label}.")
        self.logger.debug("Mode switched to translate (%s)", target_language.code)

    def _build_prompt(self, text: str) -> str:
        if self.mode == AppMode.GRAMMAR:
            return build_grammar_prompt(text)

        target_language = Language.from_code(self.lang_combo.currentData())
        return build_translation_prompt(text, target_language)

    def _on_language_changed(self) -> None:
        if self.mode == AppMode.TRANSLATE:
            target_language = Language.from_code(self.lang_combo.currentData())
            self._set_status(f"Translate mode to {target_language.label}.")
            self.logger.debug("Translation language changed to %s", target_language.code)

    def on_submit(self):
        """Submits the input text to the Gemini API for processing."""
        self._last_error_message = None
        if not self.gemini_service:
            QMessageBox.warning(
                self,
                "Gemini Unavailable",
                "A valid Gemini API key is required before processing text.",
            )
            self.open_settings(require_key=True)
            self.logger.warning("Attempted submit without active Gemini service")
            return

        if self.worker and self.worker.isRunning():
            QMessageBox.information(self, "Processing", "The previous request is still running.")
            self.logger.debug("Submit ignored; worker already running")
            return

        text = self.input_edit.toPlainText().strip()
        if not text:
            self.output_edit.setPlainText("⚠️ No input text.")
            self.reset_copy_btn()
            self.logger.debug("Submit aborted due to empty input")
            return

        self.logger.info("Submitting request mode=%s length=%d", self.mode.value, len(text))

        prompt = self._build_prompt(text)

        self.ui_state.start_processing()
        self.output_edit.clear()
        self._set_status("Working with Gemini…")

        worker = self.gemini_service.get_stream_worker(prompt)
        worker.partial.connect(self.update_output)
        worker.error.connect(self.on_worker_error)
        worker.finished.connect(self.on_finished)
        self.worker = worker
        worker.start()

    def update_output(self, text: str):
        """
        Updates the output text field with the streamed response from the API.

        Args:
            text: The partial response from the API.
        """
        first_chunk = not bool(self.output_edit.toPlainText())
        if first_chunk:
            self._set_status("Streaming response…")
        cursor = self.output_edit.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        cursor.insertText(text)
        self.output_edit.ensureCursorVisible()

    def on_worker_error(self, message: str) -> None:
        self._last_error_message = message
        self._set_status(f"⚠️ {message}")
        if not self.output_edit.toPlainText().strip():
            self.output_edit.setPlainText(f"⚠️ {message}")
        else:
            self.output_edit.append(f"\n⚠️ {message}")
        QMessageBox.critical(self, "Gemini Error", message)
        self.logger.error("Gemini worker error: %s", message)

    def on_finished(self):
        """Called when the Gemini API call is finished."""
        if self.worker:
            self.worker.deleteLater()
            self.worker = None

        has_output = bool(self.output_edit.toPlainText().strip())

        if self._last_error_message:
            status_message = f"⚠️ {self._last_error_message}"
        elif has_output:
            status_message = "Completed."
        else:
            status_message = "No response received."

        self.ui_state.set_ready(status_message, copy_available=has_output)
        self.logger.info("Processing finished (output=%s)", has_output)
        self._last_error_message = None

    def copy_output(self):
        """Copies the output text to the clipboard."""
        text = self.output_edit.toPlainText().strip()
        if text:
            QApplication.clipboard().setText(text)
            self.ui_state.mark_copy_success()
            QTimer.singleShot(1200, self.reset_copy_btn)
            self.logger.debug("Output copied to clipboard (%d chars)", len(text))
        else:
            self.ui_state.reset_copy_button(False)
            self.logger.debug("Copy attempted with empty output")

    def reset_copy_btn(self):
        """Resets the text of the copy button."""
        has_text = bool(self.output_edit.toPlainText().strip())
        self.ui_state.reset_copy_button(has_text)

    def closeEvent(self, event: QCloseEvent) -> None:
        if self.worker and self.worker.isRunning():
            self.worker.requestInterruption()
            self.worker.wait(1500)
        self.worker = None
        if self._key_validator and self._key_validator.isRunning():
            self._key_validator.requestInterruption()
            self._key_validator.wait(500)
        self._key_validator = None
        self.logger.debug("Application closing")
        super().closeEvent(event)
