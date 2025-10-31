#!/usr/bin/python3
import unittest

from src.models import Language, DEFAULT_MODEL_NAME
from src.constants import (
    LANGUAGE_LABEL_BY_CODE,
    DEFAULT_LANGUAGE_CODE,
    MODEL_LABEL_BY_NAME,
    LANGUAGE_OPTIONS,
    MODEL_OPTIONS
)

class ConstantsTests(unittest.TestCase):
    def test_language_options_cover_enum_members(self):
        option_codes = {code for _, code in LANGUAGE_OPTIONS}
        enum_codes = {language.code for language in Language}
        self.assertEqual(option_codes, enum_codes)

    def test_default_language_matches_enum(self):
        self.assertEqual(DEFAULT_LANGUAGE_CODE, Language.ENGLISH.code)

    def test_language_label_lookup(self):
        self.assertEqual(LANGUAGE_LABEL_BY_CODE["cs"], "Czech")
        self.assertEqual(LANGUAGE_LABEL_BY_CODE[DEFAULT_LANGUAGE_CODE], "English")

    def test_model_options_have_lookup_entries(self):
        option_names = {name for name, _ in MODEL_OPTIONS}
        lookup_names = set(MODEL_LABEL_BY_NAME)
        self.assertEqual(option_names, lookup_names)
        self.assertIn(DEFAULT_MODEL_NAME, option_names)

if __name__ == "__main__":
    unittest.main()
