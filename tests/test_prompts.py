#!/usr/bin/python3
import unittest
from src.models import Language
from src.prompts import build_grammar_prompt, build_translation_prompt

class PromptBuilderTests(unittest.TestCase):
    def test_build_grammar_prompt_includes_instructions_and_text(self):
        text = "Please fix me."
        prompt = build_grammar_prompt(text)
        self.assertIn("expert proofreader", prompt)
        self.assertTrue(prompt.strip().endswith(text))

    def test_build_translation_prompt_addresses_language(self):
        text = "Hello world"
        prompt = build_translation_prompt(text, Language.CZECH)
        self.assertIn("Translate the following text into Czech", prompt)
        self.assertIn("CS)", prompt)
        self.assertTrue(prompt.strip().endswith(text))

if __name__ == "__main__":
    unittest.main()
