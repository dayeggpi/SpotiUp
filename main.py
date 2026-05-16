#!/usr/bin/env python3
"""
Spotify Playlist Backup Tool
Main entry point for the application.
"""

import sys
import os

# Add the project directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import Qt

from gui import MainWindow
from config import APP_NAME


def get_resource_path(relative_path: str) -> str:
    """Resolve resource path for both dev and PyInstaller frozen builds."""
    if getattr(sys, 'frozen', False):
        base = sys._MEIPASS
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, relative_path)


def main():
    """Main entry point."""
    # Must be set before QApplication is created
    if sys.platform == 'win32':
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('com.magik.spotiup')
        except Exception:
            pass

    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName("dayeggpi")
    app.setStyle("Fusion")

    # Prefer .ico on Windows for proper taskbar icon
    icon_file = 'icon.ico' if sys.platform == 'win32' else 'icon.png'
    icon_path = get_resource_path(os.path.join('assets', icon_file))
    if not os.path.exists(icon_path):
        icon_path = get_resource_path(os.path.join('assets', 'icon.png'))

    if os.path.exists(icon_path):
        app_icon = QIcon(icon_path)
        app.setWindowIcon(app_icon)

    window = MainWindow()

    if os.path.exists(icon_path):
        window.setWindowIcon(QIcon(icon_path))

    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()