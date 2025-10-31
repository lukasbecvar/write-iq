#!/usr/bin/python3
import unittest

from src.ui_state import UIStateManager

class DummyButton:
    def __init__(self, text):
        self._text = text
        self.enabled = True

    def setText(self, text):
        self._text = text

    def text(self):
        return self._text

    def setEnabled(self, value):
        self.enabled = value

    def isEnabled(self):
        return self.enabled

class DummyLabel:
    def __init__(self):
        self.text = ""

    def setText(self, text):
        self.text = text

class UIStateManagerTests(unittest.TestCase):
    def setUp(self):
        self.submit_btn = DummyButton("▶ Process")
        self.clear_btn = DummyButton("Clear")
        self.copy_btn = DummyButton("📋 Copy")
        self.status_label = DummyLabel()
        self.manager = UIStateManager(
            self.submit_btn,
            self.clear_btn,
            self.copy_btn,
            self.status_label,
        )

    def test_start_processing_updates_buttons(self):
        self.manager.start_processing()
        self.assertEqual(self.submit_btn.text(), "⏳ Generating…")
        self.assertFalse(self.submit_btn.isEnabled())
        self.assertFalse(self.clear_btn.isEnabled())
        self.assertFalse(self.copy_btn.isEnabled())

    def test_set_ready_restores_defaults(self):
        self.manager.start_processing()
        self.manager.set_ready("All done.", copy_available=True)
        self.assertEqual(self.submit_btn.text(), "▶ Process")
        self.assertTrue(self.submit_btn.isEnabled())
        self.assertTrue(self.clear_btn.isEnabled())
        self.assertTrue(self.copy_btn.isEnabled())
        self.assertEqual(self.status_label.text, "All done.")

    def test_mark_cleared_sets_message(self):
        self.manager.mark_cleared()
        self.assertEqual(self.status_label.text, "Cleared.")
        self.assertFalse(self.copy_btn.isEnabled())

    def test_mark_copy_success_disables_button(self):
        self.manager.mark_copy_success()
        self.assertEqual(self.copy_btn.text(), "✅ Copied")
        self.assertFalse(self.copy_btn.isEnabled())

    def test_reset_copy_button_applies_availability(self):
        self.manager.reset_copy_button(True)
        self.assertEqual(self.copy_btn.text(), "📋 Copy")
        self.assertTrue(self.copy_btn.isEnabled())
        self.manager.reset_copy_button(False)
        self.assertFalse(self.copy_btn.isEnabled())

if __name__ == "__main__":
    unittest.main()
