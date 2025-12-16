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


def main():
    """Main entry point."""
    # Set Windows AppUserModelID FIRST
    if sys.platform == 'win32':
        try:
            import ctypes
            # Change this ID to something unique each time you test
            app_id = 'com.magik.spotiup'  # Changed ID
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
        except Exception:
            pass
    
    # Enable high DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName("dayeggpi")
    
    # Set style BEFORE icon
    app.setStyle("Fusion")
    
    # Set icon
    icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets', 'icon.png')
    if os.path.exists(icon_path):
        app_icon = QIcon(icon_path)
        app.setWindowIcon(app_icon)
    
    # Create and show main window
    window = MainWindow()
    
    # Set icon on window too
    if os.path.exists(icon_path):
        window.setWindowIcon(QIcon(icon_path))
    
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()