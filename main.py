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
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtCore import Qt, QSize

from gui import MainWindow
from config import APP_NAME


def setup_windows_icon(assets_dir):
    """Setup icon for Windows with proper ICO file."""
    icon_ico = os.path.join(assets_dir, 'icon.ico')
    icon_png = os.path.join(assets_dir, 'icon.png')

    # Check if ICO exists
    if os.path.exists(icon_ico):
        return icon_ico

    # ICO doesn't exist - print warning and use PNG as fallback
    print("\n" + "=" * 60)
    print("WARNING: Windows taskbar icon not configured")
    print("=" * 60)
    print("For the icon to display in the Windows taskbar, you need a .ico file.")
    print("\nQuick fix:")
    print("  1. Run: python create_icon.py")
    print("  2. This will create assets/icon.ico from your PNG")
    print("\nOR manually:")
    print("  1. Install Pillow: pip install Pillow")
    print("  2. Then run: python create_icon.py")
    print("=" * 60 + "\n")

    return icon_png if os.path.exists(icon_png) else None


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

    # Set icon (use ICO on Windows for proper taskbar display)
    assets_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets')

    # On Windows, use ICO for proper taskbar support
    if sys.platform == 'win32':
        icon_path = setup_windows_icon(assets_dir)
    else:
        # On Linux/Mac, PNG is fine
        icon_path = os.path.join(assets_dir, 'icon.png')

    # Set application-wide icon
    if icon_path and os.path.exists(icon_path):
        app_icon = QIcon(icon_path)
        app.setWindowIcon(app_icon)

    # Create and show main window
    window = MainWindow()

    # Set icon on window explicitly (important for Windows taskbar)
    if icon_path and os.path.exists(icon_path):
        window.setWindowIcon(QIcon(icon_path))
    
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()