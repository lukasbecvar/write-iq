"""
Handles loading and saving the application's configuration.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict
from src.models import AppConfig
from PyQt6.QtCore import QStandardPaths

# configuration file location
CONFIG_DIR = Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.ConfigLocation)) / "write-iq"
CONFIG_FILE = CONFIG_DIR / "config.json"

def _read_config_file(path: Path) -> Dict[str, Any] | None:
    try:
        raw = path.read_text(encoding="utf-8")
        return json.loads(raw)
    except FileNotFoundError:
        return None
    except (OSError, ValueError):
        return None

def load_config() -> AppConfig:
    """
    Loads the application configuration from disk.
    """
    data = _read_config_file(CONFIG_FILE)
    return AppConfig.from_dict(data)


def save_config(config: AppConfig) -> None:
    """
    Saves the given configuration to disk.
    """
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(config.to_dict(), indent=2), encoding="utf-8")
