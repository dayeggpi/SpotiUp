#!/usr/bin/env python3
"""
Create a proper multi-resolution ICO file for Windows taskbar.
This script requires PIL/Pillow: pip install Pillow
"""
import os
import sys

def create_ico_with_pillow():
    """Create ICO using PIL/Pillow (preferred method)."""
    try:
        from PIL import Image

        script_dir = os.path.dirname(os.path.abspath(__file__))
        png_path = os.path.join(script_dir, "assets", "icon.png")
        ico_path = os.path.join(script_dir, "assets", "icon.ico")

        if not os.path.exists(png_path):
            print(f"Error: {png_path} not found")
            return False

        # Open the PNG image
        img = Image.open(png_path)

        # Convert to RGBA if needed
        if img.mode != 'RGBA':
            img = img.convert('RGBA')

        # Create ICO with multiple sizes (required for Windows)
        icon_sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]

        print(f"Creating multi-resolution ICO from {png_path}...")
        img.save(ico_path, format='ICO', sizes=icon_sizes)

        print(f"✓ Successfully created {ico_path}")
        print(f"  Contains sizes: {', '.join([f'{w}x{h}' for w, h in icon_sizes])}")
        return True

    except ImportError:
        print("Error: PIL/Pillow is not installed")
        print("Install it with: pip install Pillow")
        print("\nAlternatively, use an online converter:")
        print("1. Go to https://convertio.co/png-ico/")
        print("2. Upload assets/icon.png")
        print("3. Download the ICO file")
        print("4. Save it as assets/icon.ico")
        return False
    except Exception as e:
        print(f"Error creating ICO: {e}")
        return False

def create_ico_with_pyqt():
    """Fallback: Create ICO using PyQt6 (may not work well on Windows)."""
    try:
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtGui import QPixmap, QIcon
        from PyQt6.QtCore import QSize

        app = QApplication(sys.argv)

        script_dir = os.path.dirname(os.path.abspath(__file__))
        png_path = os.path.join(script_dir, "assets", "icon.png")
        ico_path = os.path.join(script_dir, "assets", "icon.ico")

        if not os.path.exists(png_path):
            print(f"Error: {png_path} not found")
            return False

        print(f"Creating ICO from {png_path} using PyQt6...")
        print("Warning: PyQt6 method may not create optimal ICO files for Windows")

        # Load and create icon with multiple sizes
        icon = QIcon(png_path)
        sizes = [16, 32, 48, 64, 128, 256]

        # Get the largest pixmap and save as ICO
        pixmap = icon.pixmap(QSize(256, 256))
        success = pixmap.save(ico_path, "ICO")

        if success:
            print(f"✓ Created {ico_path} (basic ICO)")
            print("Note: For best results, use PIL/Pillow method or online converter")
            return True
        else:
            print(f"✗ Failed to create {ico_path}")
            return False

    except ImportError:
        print("Error: PyQt6 is not available")
        return False
    except Exception as e:
        print(f"Error creating ICO: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("Windows Taskbar Icon Generator")
    print("=" * 60)
    print()

    # Try PIL/Pillow first (recommended)
    if create_ico_with_pillow():
        print("\n✓ ICO file created successfully!")
        print("The app should now display the icon in the Windows taskbar.")
        sys.exit(0)

    print("\n" + "-" * 60)
    print("Trying fallback method with PyQt6...")
    print("-" * 60)
    print()

    # Fallback to PyQt6
    if create_ico_with_pyqt():
        print("\n✓ ICO file created (basic)")
        print("If the taskbar icon still doesn't work, please use an online converter.")
        sys.exit(0)

    print("\n✗ Failed to create ICO file")
    print("\nManual instructions:")
    print("1. Install Pillow: pip install Pillow")
    print("2. Run this script again")
    print("\nOR use an online converter:")
    print("1. Go to https://convertio.co/png-ico/ or https://www.icoconverter.com/")
    print("2. Upload assets/icon.png")
    print("3. Select multiple sizes: 16x16, 32x32, 48x48, 256x256")
    print("4. Download and save as assets/icon.ico")
    sys.exit(1)
