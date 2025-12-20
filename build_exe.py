#!/usr/bin/env python3
"""
Build a standalone Windows executable with proper icon.
This is the most reliable way to get the taskbar icon working on Windows.
"""
import os
import sys
import subprocess

def build_executable():
    """Build standalone executable using PyInstaller."""

    print("=" * 60)
    print("Building SpotiUp Standalone Executable")
    print("=" * 60)
    print()

    # Check if PyInstaller is installed
    try:
        import PyInstaller
        print("✓ PyInstaller is installed")
    except ImportError:
        print("Installing PyInstaller...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
        print("✓ PyInstaller installed")

    print()

    # Check for icon file
    icon_path = os.path.join("assets", "icon.ico")
    if not os.path.exists(icon_path):
        print("⚠ Warning: assets/icon.ico not found")
        print("Creating ICO file first...")

        # Try to create it
        try:
            subprocess.check_call([sys.executable, "create_icon.py"])
        except:
            print("✗ Failed to create ICO file")
            print("Please run: python create_icon.py")
            print("Or create it manually and place it in assets/icon.ico")
            return False

    print("✓ Icon file found")
    print()

    # Build command
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name=SpotiUp",
        "--onefile",
        "--windowed",  # No console window
        f"--icon={icon_path}",
        "--add-data=assets;assets",  # Include assets folder
        "main.py"
    ]

    print("Building executable...")
    print(f"Command: {' '.join(cmd)}")
    print()

    try:
        subprocess.check_call(cmd)
        print()
        print("=" * 60)
        print("✓ Build Complete!")
        print("=" * 60)
        print()
        print(f"Your executable is here: dist\\SpotiUp.exe")
        print()
        print("To use it:")
        print("1. Run: dist\\SpotiUp.exe")
        print("2. Right-click the taskbar icon → Pin to taskbar")
        print("3. The icon should now display correctly!")
        print()
        print("Note: You can move SpotiUp.exe anywhere you want.")
        print("The first time you run it, Windows Defender might scan it.")
        print()
        return True

    except subprocess.CalledProcessError as e:
        print()
        print("✗ Build failed")
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    if sys.platform != 'win32':
        print("This script is for Windows only.")
        print("On Linux/Mac, the icon should work fine with: python main.py")
        sys.exit(1)

    success = build_executable()
    sys.exit(0 if success else 1)
