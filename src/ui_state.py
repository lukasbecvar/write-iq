"""
Helpers for managing UI state transitions in the WriteIQ main window.
"""

from __future__ import annotations

from PyQt6.QtWidgets import QLabel, QPushButton

class UIStateManager:
    """Centralizes updates to status labels and action buttons."""

    def __init__(self, submit_btn: QPushButton, clear_btn: QPushButton, copy_btn: QPushButton, status_label: QLabel):
        self._submit_btn = submit_btn
        self._clear_btn = clear_btn
        self._copy_btn = copy_btn
        self._status_label = status_label
        self._submit_default_text = submit_btn.text()
        self._copy_default_text = copy_btn.text()

    def set_status(self, message: str) -> None:
        self._status_label.setText(message)

    def start_processing(self) -> None:
        self._submit_btn.setText("⏳ Generating…")
        self._submit_btn.setEnabled(False)
        self._clear_btn.setEnabled(False)
        self._copy_btn.setEnabled(False)

    def set_ready(self, message: str = "Ready.", *, copy_available: bool = False) -> None:
        self._submit_btn.setText(self._submit_default_text)
        self._submit_btn.setEnabled(True)
        self._clear_btn.setEnabled(True)
        self._copy_btn.setText(self._copy_default_text)
        self._copy_btn.setEnabled(copy_available)
        self._status_label.setText(message)

    def mark_cleared(self) -> None:
        self.set_ready(message="Cleared.", copy_available=False)

    def mark_copy_success(self) -> None:
        self._copy_btn.setText("✅ Copied")
        self._copy_btn.setEnabled(False)

    def reset_copy_button(self, copy_available: bool) -> None:
        self._copy_btn.setText(self._copy_default_text)
        self._copy_btn.setEnabled(copy_available)
