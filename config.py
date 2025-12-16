"""
Configuration settings for Spotify Backup Tool.
You need to create a Spotify Developer Application at:
https://developer.spotify.com/dashboard/applications

Set your credentials here or as environment variables.
"""

import os
    
# Spotify API Credentials
# Get these from https://developer.spotify.com/dashboard/applications
SPOTIFY_CLIENT_ID = os.environ.get('SPOTIFY_CLIENT_ID', 'your_client_id')
SPOTIFY_CLIENT_SECRET = os.environ.get('SPOTIFY_CLIENT_SECRET', 'your_client_secret')
SPOTIFY_REDIRECT_URI = os.environ.get('SPOTIFY_REDIRECT_URI', 'http://127.0.0.1:8080/spotiup')

# Scopes needed for the application
SPOTIFY_SCOPES = [
    'user-library-read',      # Read liked songs
    'playlist-read-private',  # Read private playlists
    'playlist-read-collaborative',  # Read collaborative playlists
]


# Default backup location
DEFAULT_BACKUP_DIR = os.path.join(os.path.expanduser('./'), 'SpotifyBackup')

# Application settings
APP_NAME = "SpotiUp"
APP_VERSION = "1.0.0"