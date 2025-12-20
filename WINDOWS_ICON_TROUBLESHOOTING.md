# Windows Taskbar Icon Troubleshooting

If the app icon still doesn't appear in the Windows taskbar after creating the ICO file, try these steps:

## Step 1: Ensure ICO File Exists

Make sure `assets/icon.ico` exists:
- Run: `python create_icon.py`
- OR convert manually using an online tool

## Step 2: Clear Windows Icon Cache

Windows caches taskbar icons. You need to clear this cache:

### Method 1: Using Command Prompt (Easiest)

1. Close SpotiUp if it's running
2. Open Command Prompt as Administrator
3. Run these commands:

```cmd
cd /d %userprofile%\AppData\Local
attrib -h IconCache.db
del IconCache.db
attrib -h iconcache_*.db
del iconcache_*.db
```

4. Restart Windows Explorer:
   - Press `Ctrl+Shift+Esc` to open Task Manager
   - Find "Windows Explorer"
   - Right-click → "Restart"

5. Run SpotiUp again: `python main.py`

### Method 2: Using File Explorer

1. Close SpotiUp if it's running
2. Open File Explorer
3. Go to: `C:\Users\<YourUsername>\AppData\Local`
   - If you don't see AppData, enable "Hidden items" in View tab
4. Delete these files:
   - `IconCache.db`
   - All files starting with `iconcache_`
5. Restart Windows Explorer (see Method 1 step 4)
6. Run SpotiUp again

### Method 3: Restart Computer

Sometimes the simplest solution:
1. Close all applications
2. Restart your computer
3. Run SpotiUp again: `python main.py`

## Step 3: Verify ICO File is Valid

If the icon still doesn't show, the ICO file might be corrupted:

### Test the ICO file:
1. Navigate to `assets/icon.ico` in File Explorer
2. Right-click → Properties
3. You should see a preview of the icon
4. If no preview appears, the ICO is invalid

### Create a new ICO file:
- Use an online converter: https://convertio.co/png-ico/
- Upload `assets/icon.png`
- **Important:** Select these sizes in the converter:
  - 16x16
  - 32x32
  - 48x48
  - 256x256
- Download and save as `assets/icon.ico`

## Step 4: Check Application Behavior

When you run `python main.py`, you should see:
```
✓ Taskbar icon set via Windows API
```

If you see errors or warnings, the ICO file might not be loaded correctly.

## Step 5: Try Running as Frozen Executable (Optional)

If none of the above works, the issue might be that Windows groups Python scripts under `python.exe`.

You can create a standalone executable using PyInstaller:

```cmd
pip install pyinstaller
pyinstaller --onefile --windowed --icon=assets/icon.ico --name=SpotiUp main.py
```

The executable will be in the `dist/` folder and should show the icon correctly.

## Common Issues

### Issue: "WARNING: Windows taskbar icon not configured"
- **Fix:** Run `python create_icon.py` to generate the ICO file

### Issue: Icon shows in window but not taskbar
- **Fix:** Clear Windows icon cache (see Step 2)

### Issue: Icon shows as default Python icon
- **Fix:** The AppUserModelID is set incorrectly. This should be fixed in the latest version.

### Issue: "Could not set icon via Windows API"
- **Fix:** Make sure the ICO file path has no special characters or spaces
- Try moving the entire project to a simpler path like `C:\SpotiUp\`

## Still Not Working?

If you've tried all the above and it still doesn't work:

1. Check that you're using Python 3.8+ (run `python --version`)
2. Make sure PyQt6 is up to date (run `pip install --upgrade PyQt6`)
3. Try the PyInstaller method to create a standalone executable
4. Report the issue with details about your Windows version and Python version
