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


def ensure_ico_exists(png_path, ico_path):
    """Create ICO file from PNG if it doesn't exist (for Windows taskbar)."""
    if os.path.exists(ico_path):
        return True

    if not os.path.exists(png_path):
        return False

    try:
        # Load PNG and create ICO with multiple sizes
        pixmap = QPixmap(png_path)
        if pixmap.isNull():
            return False

        # Scale to 256x256 (largest common size for ICO)
        scaled = pixmap.scaled(
            QSize(256, 256),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )

        # Save as ICO
        success = scaled.save(ico_path, "ICO")
        if success:
            print(f"Created {ico_path} from {png_path}")
        return success
    except Exception as e:
        print(f"Error creating ICO file: {e}")
        return False


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
    icon_png = os.path.join(assets_dir, 'icon.png')
    icon_ico = os.path.join(assets_dir, 'icon.ico')

    # On Windows, ensure ICO exists and use it for better taskbar support
    if sys.platform == 'win32':
        ensure_ico_exists(icon_png, icon_ico)
        icon_path = icon_ico if os.path.exists(icon_ico) else icon_png
    else:
        icon_path = icon_png

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