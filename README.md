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
- Note your Client ID and Client Secret
- Add http://localhost:8888/callback to the Redirect URIs

### 3. Run

```bash
python main.py
```

## ToDo

- [ ] Fix app icon in taskbar
- [ ] Double check if API rate limiting is properly handled
- [ ] Add ability to backup "by Spotify" playlists saved into user's playlists
