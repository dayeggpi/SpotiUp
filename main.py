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


def set_windows_taskbar_icon(icon_path):
    """Set the taskbar icon using Windows API."""
    if sys.platform != 'win32':
        return

    try:
        import ctypes
        from ctypes import wintypes

        # Load the icon
        IMAGE_ICON = 1
        LR_LOADFROMFILE = 0x00000010
        LR_DEFAULTSIZE = 0x00000040

        # Convert to absolute path
        icon_path = os.path.abspath(icon_path)

        # Load the icon using Windows API
        hicon = ctypes.windll.user32.LoadImageW(
            None,
            icon_path,
            IMAGE_ICON,
            0, 0,
            LR_LOADFROMFILE | LR_DEFAULTSIZE
        )

        if hicon:
            # Get the window handle (we'll set it later after window is created)
            return hicon
    except Exception as e:
        print(f"Warning: Could not load icon via Windows API: {e}")

    return None


def main():
    """Main entry point."""
    # CRITICAL: Set Windows AppUserModelID BEFORE QApplication
    # This prevents Windows from grouping the app under python.exe
    if sys.platform == 'win32':
        try:
            import ctypes
            # Set unique AppUserModelID
            app_id = 'DayEggPi.SpotiUp.MusicBackup.1'
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
        except Exception as e:
            print(f"Warning: Could not set AppUserModelID: {e}")

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

    # Set application-wide icon (Qt level)
    if icon_path and os.path.exists(icon_path):
        app_icon = QIcon(icon_path)
        app.setWindowIcon(app_icon)

        # For Windows: Also try to load via Windows API
        if sys.platform == 'win32' and icon_path.endswith('.ico'):
            set_windows_taskbar_icon(icon_path)

    # Create and show main window
    window = MainWindow()

    # Set icon on window explicitly (important for Windows taskbar)
    if icon_path and os.path.exists(icon_path):
        window.setWindowIcon(QIcon(icon_path))

        # Windows-specific: Set icon using Windows API on the actual window
        if sys.platform == 'win32' and icon_path.endswith('.ico'):
            try:
                import ctypes
                from PyQt6.QtWidgets import QApplication

                # Get window handle
                hwnd = int(window.winId())

                # Load icon via Windows API
                IMAGE_ICON = 1
                LR_LOADFROMFILE = 0x00000010
                LR_DEFAULTSIZE = 0x00000040

                icon_abs_path = os.path.abspath(icon_path)

                # Load small and large icons
                hicon_small = ctypes.windll.user32.LoadImageW(
                    None, icon_abs_path, IMAGE_ICON,
                    16, 16, LR_LOADFROMFILE
                )
                hicon_large = ctypes.windll.user32.LoadImageW(
                    None, icon_abs_path, IMAGE_ICON,
                    32, 32, LR_LOADFROMFILE
                )

                # Send icon messages to window
                WM_SETICON = 0x0080
                ICON_SMALL = 0
                ICON_BIG = 1

                if hicon_small:
                    ctypes.windll.user32.SendMessageW(hwnd, WM_SETICON, ICON_SMALL, hicon_small)
                if hicon_large:
                    ctypes.windll.user32.SendMessageW(hwnd, WM_SETICON, ICON_BIG, hicon_large)

                print("✓ Taskbar icon set via Windows API")
            except Exception as e:
                print(f"Note: Could not set icon via Windows API: {e}")
    
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()