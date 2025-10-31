"""Application-wide logging configuration."""

from __future__ import annotations

import logging
from pathlib import Path
from logging.handlers import RotatingFileHandler
from src.config import CONFIG_DIR

LOG_FILE = CONFIG_DIR / "write-iq.log"

def init_logging(level: int = logging.INFO) -> Path:
    """
    Configures root logging with both console and rotating file handlers.

    Returns the path to the log file.
    """
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    root_logger = logging.getLogger()
    if root_logger.handlers:
        return LOG_FILE

    root_logger.setLevel(level)

    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    file_handler = RotatingFileHandler(LOG_FILE, maxBytes=512_000, backupCount=3, encoding="utf-8")
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    root_logger.debug("Logging initialized. Log file: %s", LOG_FILE)

    return LOG_FILE
