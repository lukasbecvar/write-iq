#!/usr/bin/python3
import unittest

from src.models import (
    DEFAULT_MODEL_NAME,
    UserSettings,
    AppConfig,
    Language
)

class LanguageTests(unittest.TestCase):
    def test_from_code_returns_matching_language(self):
        self.assertEqual(Language.from_code("cs"), Language.CZECH)

    def test_from_code_is_case_insensitive(self):
        self.assertEqual(Language.from_code("EN"), Language.ENGLISH)

    def test_from_code_falls_back_to_english(self):
        self.assertEqual(Language.from_code("unknown"), Language.ENGLISH)

class UserSettingsTests(unittest.TestCase):
    def test_from_dict_uses_defaults_when_missing(self):
        settings = UserSettings.from_dict({})
        self.assertEqual(settings.default_language, Language.ENGLISH.code)
        self.assertEqual(settings.model_name, DEFAULT_MODEL_NAME)

    def test_from_dict_reads_values(self):
        payload = {"default_language": "cs", "model_name": "gemini-1.5-pro"}
        settings = UserSettings.from_dict(payload)
        self.assertEqual(settings.default_language, "cs")
        self.assertEqual(settings.model_name, "gemini-1.5-pro")

    def test_to_dict_round_trip(self):
        settings = UserSettings(default_language="de", model_name="custom-model")
        self.assertEqual(
            settings.to_dict(),
            {"default_language": "de", "model_name": "custom-model"}
        )

class AppConfigTests(unittest.TestCase):
    def test_from_dict_with_missing_data_returns_defaults(self):
        config = AppConfig.from_dict(None)
        self.assertEqual(config.api_key, "")
        self.assertIsInstance(config.settings, UserSettings)

    def test_from_dict_loads_nested_settings(self):
        config = AppConfig.from_dict(
            {
                "api_key": "abc123",
                "settings": {"default_language": "fr", "model_name": "gemini-1.5-pro"}
            }
        )
        self.assertEqual(config.api_key, "abc123")
        self.assertEqual(config.settings.default_language, "fr")
        self.assertEqual(config.settings.model_name, "gemini-1.5-pro")

    def test_to_dict_serializes_configuration(self):
        config = AppConfig(api_key="xyz", settings=UserSettings(default_language="es"))
        self.assertEqual(
            config.to_dict(),
            {
                "api_key": "xyz",
                "settings": {
                    "default_language": "es",
                    "model_name": DEFAULT_MODEL_NAME
                }
            }
        )

if __name__ == "__main__":
    unittest.main()
