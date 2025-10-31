#!/usr/bin/python3
import logging
import unittest
from pathlib import Path
from src import logging_setup
from unittest.mock import patch
from tempfile import TemporaryDirectory

class LoggingSetupTests(unittest.TestCase):
    def setUp(self):
        self.root_logger = logging.getLogger()
        self.original_level = self.root_logger.level
        self.original_handlers = self.root_logger.handlers[:]
        for handler in self.root_logger.handlers[:]:
            self.root_logger.removeHandler(handler)

    def tearDown(self):
        for handler in self.root_logger.handlers[:]:
            try:
                handler.close()
            finally:
                self.root_logger.removeHandler(handler)
        self.root_logger.setLevel(self.original_level)
        for handler in self.original_handlers:
            self.root_logger.addHandler(handler)

    def test_init_logging_creates_rotating_file_handler_once(self):
        with TemporaryDirectory() as tmp:
            config_dir = Path(tmp)
            log_file = config_dir / "write-iq.log"

            with patch("src.logging_setup.CONFIG_DIR", config_dir), patch(
                "src.logging_setup.LOG_FILE", log_file
            ):
                returned_path = logging_setup.init_logging(level=logging.DEBUG)

            self.assertEqual(returned_path, log_file)
            self.assertTrue(log_file.exists())

            first_handlers = self.root_logger.handlers[:]
            self.assertGreaterEqual(len(first_handlers), 2)

            with patch("src.logging_setup.CONFIG_DIR", config_dir), patch(
                "src.logging_setup.LOG_FILE", log_file
            ):
                returned_again = logging_setup.init_logging(level=logging.DEBUG)

            self.assertEqual(returned_again, log_file)
            self.assertEqual(self.root_logger.handlers, first_handlers)

    def test_init_logging_returns_early_when_handlers_present(self):
        with TemporaryDirectory() as tmp:
            config_dir = Path(tmp)
            log_file = config_dir / "write-iq.log"

            handler = logging.NullHandler()
            self.root_logger.addHandler(handler)

            with patch("src.logging_setup.CONFIG_DIR", config_dir), patch(
                "src.logging_setup.LOG_FILE", log_file
            ):
                returned_path = logging_setup.init_logging()

        self.assertEqual(returned_path, log_file)
        self.assertEqual(self.root_logger.handlers, [handler])

if __name__ == "__main__":
    unittest.main()
