# SpotiUp

A Python GUI application to backup your Spotify playlists and liked songs to JSON format.

## Features

- **Full Backup**: Save all your playlists and liked songs
- **Incremental Updates**: Only update changed playlists
- **Search**: Search across all tracks, artists, albums, and playlists
- **Folder Organization**: Organize playlists into virtual folders
- **Export**: Export to CSV format
- **Human-Readable**: All data stored in JSON format, readable without the app

## Installation

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Create Spotify Developer Application

- Go to Spotify Developer Dashboard
- Create a new application
- Note your Client ID and Client Secret (edit config.py accordingly)
- Add http://localhost:8888/callback to the Redirect URIs

### 3. Windows Icon Setup (Optional but Recommended)

**⚠️ Important for Windows users:** The icon won't show in the taskbar when running `python main.py` due to Windows limitations. See [**TASKBAR_ICON_SOLUTION.md**](TASKBAR_ICON_SOLUTION.md) for working solutions.

**Quick fix - Build standalone EXE (recommended):**
```bash
pip install Pillow
python create_icon.py
python build_exe.py
# Then run: dist\SpotiUp.exe
```

For other methods (VBS launcher, shortcuts, etc.), see the [complete guide](TASKBAR_ICON_SOLUTION.md).

### 4. Run

```bash
python main.py
```

Then click connect (which should open a browser to login/approve the Spotify App <> API connection). Troubles connecting ? delete .cache file and try again.

## ToDo

- [x] Fix app icon in taskbar (run `create_icon.py` to generate proper ICO file)
- [ ] Double check if API rate limiting is properly handled
- [ ] ~Add ability to backup "by Spotify" playlists saved into user's playlists~ (seems Web API doesn't allow this anymore)

## GUI
<img width="1202" height="832" alt="spotiup" src="https://github.com/user-attachments/assets/5e1ccafc-38ce-491e-93dd-28ccb2816703" />
