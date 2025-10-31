#!/usr/bin/python3
"""
Main entry point for the WriteIQ application.

This script initializes the PyQt6 application, loads the configuration,
and displays the main application window.
"""

import sys
import logging
from pathlib import Path
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon
from src.ui import TextHelperApp
from src.config import load_config
from PyQt6.QtWidgets import QApplication
from src.logging_setup import init_logging

def _enable_high_dpi():
    """
    Enables high-DPI related application attributes when available (Qt 6 drops some flags).
    """
    enable_scaling = getattr(Qt.ApplicationAttribute, "AA_EnableHighDpiScaling", None)
    if enable_scaling is not None:
        QApplication.setAttribute(enable_scaling, True)

    use_hdpi_pixmaps = getattr(Qt.ApplicationAttribute, "AA_UseHighDpiPixmaps", None)
    if use_hdpi_pixmaps is not None:
        QApplication.setAttribute(use_hdpi_pixmaps, True)

if __name__ == "__main__":
    """Initializes and runs the WriteIQ application."""
    _enable_high_dpi()
    log_path = init_logging()
    logging.getLogger(__name__).info("WriteIQ starting (logs: %s)", log_path)
    app = QApplication(sys.argv)
    app.setApplicationName("WriteIQ")
    app.setOrganizationName("WriteIQ")

    icon_path = Path("src/assets/icon.png")
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    # load configuration
    config = load_config()

    # create and show the main window
    w = TextHelperApp(config=config)
    w.show()

    # start application event loop
    sys.exit(app.exec())
