"""
Core data models and value objects used across the WriteIQ application.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict
from dataclasses import dataclass, field

DEFAULT_MODEL_NAME = "gemini-2.5-flash"

class Language(Enum):
    """
    Enumeration of supported languages.
    """

    ENGLISH = ("en", "English")
    CZECH = ("cs", "Czech")
    GERMAN = ("de", "German")
    FRENCH = ("fr", "French")
    SPANISH = ("es", "Spanish")
    ITALIAN = ("it", "Italian")
    POLISH = ("pl", "Polish")
    PORTUGUESE = ("pt", "Portuguese")
    RUSSIAN = ("ru", "Russian")
    JAPANESE = ("ja", "Japanese")
    CHINESE = ("zh", "Chinese")

    def __init__(self, code: str, label: str):
        self.code = code
        self.label = label

    def to_combo_tuple(self) -> tuple[str, str]:
        return self.label, self.code

    @classmethod
    def from_code(cls, code: str | None) -> "Language":
        normalized = (code or "").lower()
        for language in cls:
            if language.code == normalized:
                return language
        return cls.ENGLISH

@dataclass
class UserSettings:
    """
    Stores user-facing configuration values persisted across sessions.
    """

    default_language: str = Language.ENGLISH.code
    model_name: str = DEFAULT_MODEL_NAME

    @classmethod
    def from_dict(cls, data: Dict[str, Any] | None) -> "UserSettings":
        if not data:
            return cls()
        return cls(
            default_language=data.get("default_language", cls().default_language),
            model_name=data.get("model_name", cls().model_name),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "default_language": self.default_language,
            "model_name": self.model_name,
        }

@dataclass
class AppConfig:
    """
    Root configuration object stored on disk.
    """

    api_key: str = ""
    settings: UserSettings = field(default_factory=UserSettings)

    @classmethod
    def from_dict(cls, data: Dict[str, Any] | None) -> "AppConfig":
        if not data:
            return cls()
        settings = UserSettings.from_dict(data.get("settings"))
        return cls(api_key=data.get("api_key", ""), settings=settings)

    def to_dict(self) -> Dict[str, Any]:
        return {"api_key": self.api_key, "settings": self.settings.to_dict()}
