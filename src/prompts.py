"""
Utilities for constructing prompts sent to Gemini.
"""

from __future__ import annotations
from src.models import Language

def build_grammar_prompt(text: str) -> str:
    """
    Returns a system prompt instructing Gemini to correct grammar while preserving tone.
    """
    return (
        "You are an expert proofreader. "
        "Correct grammar, punctuation, and spelling while preserving the original tone. "
        "Return only the corrected text without explanations.\n\n"
        f"{text}"
    )

def build_translation_prompt(text: str, target_language: Language) -> str:
    """
    Returns a prompt instructing Gemini to translate text into the selected language.
    """
    return (
        f"Translate the following text into {target_language.label} ({target_language.code.upper()}). "
        "Detect the source language automatically, preserve tone, and keep formatting when possible. "
        "Return only the translated text.\n\n"
        f"{text}"
    )
