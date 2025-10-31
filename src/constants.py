"""
Stores constant values used across the application.
"""

from __future__ import annotations

from src.models import Language, DEFAULT_MODEL_NAME

DEFAULT_LANGUAGE_CODE = Language.ENGLISH.code
LANGUAGE_OPTIONS = [language.to_combo_tuple() for language in Language]
LANGUAGE_LABEL_BY_CODE = {language.code: language.label for language in Language}

MODEL_OPTIONS = [
    (DEFAULT_MODEL_NAME, "Gemini 2.5 Flash (speed)"),
    ("gemini-1.5-pro", "Gemini 1.5 Pro (quality)"),
]

MODEL_LABEL_BY_NAME = {name: label for name, label in MODEL_OPTIONS}
