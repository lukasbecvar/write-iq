#!/usr/bin/python3
import json
import unittest
from pathlib import Path
from unittest.mock import patch
from src.models import UserSettings
from tempfile import TemporaryDirectory

from src.config import (
    _read_config_file,
    load_config,
    save_config,
    AppConfig
)

class ConfigTests(unittest.TestCase):
    def test_read_config_file_returns_none_for_missing_path(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            self.assertIsNone(_read_config_file(path))

    def test_read_config_file_handles_invalid_json(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            path.write_text("{invalid json", encoding="utf-8")
            self.assertIsNone(_read_config_file(path))

    def test_load_config_returns_defaults_when_file_absent(self):
        with TemporaryDirectory() as tmp:
            config_dir = Path(tmp)
            config_file = config_dir / "config.json"
            with patch("src.config.CONFIG_DIR", config_dir), patch("src.config.CONFIG_FILE", config_file):
                config = load_config()
            self.assertEqual(config.api_key, "")
            self.assertIsInstance(config.settings, UserSettings)

    def test_load_config_reads_existing_file(self):
        with TemporaryDirectory() as tmp:
            config_dir = Path(tmp)
            config_file = config_dir / "config.json"
            payload = {
                "api_key": "stored-key",
                "settings": {"default_language": "de", "model_name": "gemini-1.5-pro"},
            }
            config_dir.mkdir(parents=True, exist_ok=True)
            config_file.write_text(json.dumps(payload), encoding="utf-8")
            with patch("src.config.CONFIG_DIR", config_dir), patch("src.config.CONFIG_FILE", config_file):
                config = load_config()
            self.assertEqual(config.api_key, "stored-key")
            self.assertEqual(config.settings.default_language, "de")
            self.assertEqual(config.settings.model_name, "gemini-1.5-pro")

    def test_save_config_writes_json_payload(self):
        with TemporaryDirectory() as tmp:
            config_dir = Path(tmp)
            config_file = config_dir / "config.json"
            config = AppConfig(api_key="new-key", settings=UserSettings(default_language="fr"))
            with patch("src.config.CONFIG_DIR", config_dir), patch("src.config.CONFIG_FILE", config_file):
                save_config(config)
            written = json.loads(config_file.read_text(encoding="utf-8"))
            self.assertEqual(written["api_key"], "new-key")
            self.assertEqual(written["settings"]["default_language"], "fr")

if __name__ == "__main__":
    unittest.main()
