"""
Spotify API client wrapper using Spotipy.
Handles authentication and data fetching.
"""

import spotipy
from spotipy.oauth2 import SpotifyOAuth
from spotipy.exceptions import SpotifyException
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime, timedelta
import time
import re
import json
from pathlib import Path

from config import (
    SPOTIFY_CLIENT_ID,
    SPOTIFY_CLIENT_SECRET,
    SPOTIFY_REDIRECT_URI,
    SPOTIFY_SCOPES,
    DEFAULT_BACKUP_DIR
)
from models import Track, Playlist
from models.playlist import LikedSongs


class RateLimitInfo:
    """Information about rate limiting status."""
    def __init__(self):
        self.is_limited = False
        self.retry_after_seconds = 0
        self.available_at: Optional[datetime] = None
        self.error_message = ""
    
    def set_limited(self, retry_after: int, message: str = ""):
        self.is_limited = True
        self.retry_after_seconds = retry_after
        self.available_at = datetime.now() + timedelta(seconds=retry_after)
        self.error_message = message
    
    def clear(self):
        self.is_limited = False
        self.retry_after_seconds = 0
        self.available_at = None
        self.error_message = ""
    
    @property
    def available_at_formatted(self) -> str:
        if self.available_at:
            return self.available_at.strftime("%H:%M:%S on %Y-%m-%d")
        return "Unknown"


class BackupProgress:
    """Tracks backup progress for resume capability."""
    def __init__(self, backup_dir: str = DEFAULT_BACKUP_DIR):
        self.backup_dir = Path(backup_dir)
        self.progress_file = self.backup_dir / ".backup_progress.json"
        
        # Progress state
        self.playlists_to_process: List[Dict[str, Any]] = []
        self.playlists_completed: List[str] = []  # playlist IDs
        self.current_playlist_id: Optional[str] = None
        self.current_playlist_offset: int = 0
        self.liked_songs_completed: bool = False
        self.liked_songs_offset: int = 0
        self.partial_data: Dict[str, Any] = {}
        self.was_interrupted: bool = False
        self.rate_limit_info: Optional[Dict[str, Any]] = None
    
    def save(self):
        """Save progress to file."""
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        data = {
            'playlists_to_process': self.playlists_to_process,
            'playlists_completed': self.playlists_completed,
            'current_playlist_id': self.current_playlist_id,
            'current_playlist_offset': self.current_playlist_offset,
            'liked_songs_completed': self.liked_songs_completed,
            'liked_songs_offset': self.liked_songs_offset,
            'was_interrupted': self.was_interrupted,
            'rate_limit_info': self.rate_limit_info,
            'saved_at': datetime.now().isoformat()
        }
        with open(self.progress_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def load(self) -> bool:
        """Load progress from file. Returns True if progress was loaded."""
        if not self.progress_file.exists():
            return False
        try:
            with open(self.progress_file, 'r') as f:
                data = json.load(f)
            self.playlists_to_process = data.get('playlists_to_process', [])
            self.playlists_completed = data.get('playlists_completed', [])
            self.current_playlist_id = data.get('current_playlist_id')
            self.current_playlist_offset = data.get('current_playlist_offset', 0)
            self.liked_songs_completed = data.get('liked_songs_completed', False)
            self.liked_songs_offset = data.get('liked_songs_offset', 0)
            self.was_interrupted = data.get('was_interrupted', False)
            self.rate_limit_info = data.get('rate_limit_info')
            return True
        except Exception:
            return False
    
    def clear(self):
        """Clear progress file."""
        if self.progress_file.exists():
            self.progress_file.unlink()
        self.__init__(str(self.backup_dir))
    
    def has_pending_work(self) -> bool:
        """Check if there's pending work from a previous interrupted backup."""
        return self.was_interrupted and (
            len(self.playlists_completed) < len(self.playlists_to_process) or
            not self.liked_songs_completed
        )


class SpotifyClient:
    """Wrapper for Spotipy to fetch user's playlists and tracks."""
    
    def __init__(self, progress_callback: Optional[Callable[[str, int, int], None]] = None,
                 backup_dir: str = DEFAULT_BACKUP_DIR):
        self.sp = None
        self.user_id = None
        self.progress_callback = progress_callback
        self._artist_genres_cache: Dict[str, List[str]] = {}
        self.rate_limit_info = RateLimitInfo()
        self.backup_progress = BackupProgress(backup_dir)
        self._auth_manager = None
        
    def _report_progress(self, message: str, current: int = 0, total: int = 0):
        """Report progress if callback is set."""
        if self.progress_callback:
            self.progress_callback(message, current, total)
    
    def _parse_retry_after(self, error_message: str) -> int:
        """Parse retry-after seconds from error message."""
        # Try to find pattern like "Retry will occur after: 65624 s"
        match = re.search(r'Retry will occur after:\s*(\d+)\s*s', error_message)
        if match:
            return int(match.group(1))
        
        # Try to find pattern like "retry after X seconds"
        match = re.search(r'retry after\s*(\d+)\s*second', error_message, re.IGNORECASE)
        if match:
            return int(match.group(1))
        
        # Default to 1 hour if we can't parse
        return 3600
    
    def _handle_spotify_error(self, e: Exception, context: str = "") -> bool:
        """
        Handle Spotify API errors.
        Returns True if the error was a rate limit (and info was set).
        """
        error_str = str(e)
        
        # Check for rate limit (429)
        if isinstance(e, SpotifyException):
            if e.http_status == 429:
                retry_after = self._parse_retry_after(error_str)
                self.rate_limit_info.set_limited(retry_after, f"Rate limited during {context}")
                self._report_progress(
                    f"⚠️ Rate limit reached. Available at: {self.rate_limit_info.available_at_formatted}"
                )
                return True
            elif e.http_status == 401:
                # Token expired - try to refresh
                self._report_progress("Token expired, attempting refresh...")
                if self._refresh_token():
                    return False  # Token refreshed, can retry
                else:
                    self.rate_limit_info.set_limited(0, "Authentication failed - please reconnect")
                    return True
        
        # Check for rate limit in error message
        if 'rate' in error_str.lower() and 'limit' in error_str.lower():
            retry_after = self._parse_retry_after(error_str)
            self.rate_limit_info.set_limited(retry_after, f"Rate limited during {context}")
            return True
        
        # Check for token expiry
        if 'expired' in error_str.lower() or '401' in error_str:
            if self._refresh_token():
                return False
            self.rate_limit_info.set_limited(0, "Token expired - please reconnect")
            return True
        
        return False
    
    def _refresh_token(self) -> bool:
        """Attempt to refresh the access token."""
        try:
            if self._auth_manager:
                token_info = self._auth_manager.refresh_access_token(
                    self._auth_manager.get_cached_token()['refresh_token']
                )
                if token_info:
                    self.sp = spotipy.Spotify(auth_manager=self._auth_manager)
                    self._report_progress("Token refreshed successfully")
                    return True
        except Exception as e:
            self._report_progress(f"Token refresh failed: {str(e)}")
        return False
    
    def authenticate(self) -> bool:
        """Authenticate with Spotify using OAuth."""
        try:
            self._auth_manager = SpotifyOAuth(
                client_id=SPOTIFY_CLIENT_ID,
                client_secret=SPOTIFY_CLIENT_SECRET,
                redirect_uri=SPOTIFY_REDIRECT_URI,
                scope=' '.join(SPOTIFY_SCOPES),
                open_browser=True
            )
            
            self.sp = spotipy.Spotify(auth_manager=self._auth_manager)
            
            user_info = self.sp.current_user()
            self.user_id = user_info['id']
            self._report_progress(f"Authenticated as: {user_info.get('display_name', self.user_id)}")
            
            # Clear any previous rate limit
            self.rate_limit_info.clear()
            
            return True
            
        except Exception as e:
            self._report_progress(f"Authentication failed: {str(e)}")
            return False
    
    def is_authenticated(self) -> bool:
        """Check if client is authenticated."""
        return self.sp is not None and self.user_id is not None
    
    def is_rate_limited(self) -> bool:
        """Check if we're currently rate limited."""
        if not self.rate_limit_info.is_limited:
            return False
        
        # Check if rate limit has expired
        if self.rate_limit_info.available_at and datetime.now() >= self.rate_limit_info.available_at:
            self.rate_limit_info.clear()
            return False
        
        return True
    
    def get_rate_limit_status(self) -> Dict[str, Any]:
        """Get current rate limit status."""
        return {
            'is_limited': self.rate_limit_info.is_limited,
            'retry_after_seconds': self.rate_limit_info.retry_after_seconds,
            'available_at': self.rate_limit_info.available_at_formatted if self.rate_limit_info.available_at else None,
            'message': self.rate_limit_info.error_message
        }
    
    def get_user_info(self) -> Dict[str, Any]:
        """Get current user's information."""
        if not self.is_authenticated():
            return {}
        return self.sp.current_user()
        
    def get_all_playlists(self, include_spotify_playlists: bool = True,
                          include_collab_playlists: bool = True) -> List[Playlist]:
        """
        Fetch all playlists for the current user.
        """
        if not self.is_authenticated():
            self._report_progress("Not authenticated!")
            return []
        
        if self.is_rate_limited():
            self._report_progress(f"Rate limited until {self.rate_limit_info.available_at_formatted}")
            return []
        
        playlists = []
        seen_ids = set()
        offset = 0
        limit = 50
        
        self._report_progress("Fetching playlists...")
        
        while True:
            try:
                results = self.sp.current_user_playlists(limit=limit, offset=offset)
                
                if not results or not results.get('items'):
                    break
                
                for item in results['items']:
                    if item is None:
                        continue
                    
                    playlist_id = item.get('id')
                    if not playlist_id or playlist_id in seen_ids:
                        continue
                    
                    seen_ids.add(playlist_id)
                    
                    owner_id = item.get('owner', {}).get('id', '')
                    owner_id_lower = owner_id.lower()
                    
                    is_spotify_playlist = owner_id_lower == 'spotify'
                    is_owned_by_user = (owner_id == self.user_id)
                    is_collaborative = item.get('collaborative', False)
                    
                    self._report_progress(
                        f"Found: {item.get('name')} (owner: {owner_id})",
                        len(playlists) + 1,
                        results.get('total', 0)
                    )
                    
                    if is_spotify_playlist and not include_spotify_playlists:
                        continue
                    
                    if is_collaborative and not include_collab_playlists:
                        self._report_progress(f"Skipping collaborative playlist: {item.get('name')}")
                        continue
                    
                    playlist = Playlist.from_spotify_playlist(item)
                    playlist.extra_details['is_spotify_created'] = is_spotify_playlist
                    playlist.extra_details['is_owned_by_user'] = is_owned_by_user
                    playlist.extra_details['is_followed'] = not is_owned_by_user
                    
                    playlists.append(playlist)
                
                if results.get('next') is None:
                    break
                    
                offset += limit
                time.sleep(0.1)
                
            except Exception as e:
                if self._handle_spotify_error(e, "fetching playlists"):
                    break
                self._report_progress(f"Error fetching playlists: {str(e)}")
                import traceback
                traceback.print_exc()
                break
        
        self._report_progress(f"Found {len(playlists)} playlists total")
        return playlists
    
    def get_playlist_tracks(self, playlist_id: str, playlist_name: str = "", 
                            fetch_genres: bool = False, start_offset: int = 0) -> tuple[List[Track], bool, int]:
        """
        Fetch all tracks from a specific playlist.
        
        Returns:
            Tuple of (tracks, completed, last_offset)
            - tracks: List of fetched tracks
            - completed: True if all tracks were fetched
            - last_offset: The offset where we stopped (for resume)
        """
        if not self.is_authenticated():
            return [], False, 0
        
        if self.is_rate_limited():
            return [], False, start_offset
        
        tracks = []
        offset = start_offset
        limit = 100
        
        while True:
            try:
                results = self.sp.playlist_tracks(
                    playlist_id,
                    limit=limit,
                    offset=offset,
                    fields='items(added_at,added_by,track(id,uri,name,artists,album,duration_ms,track_number,disc_number,explicit,popularity,external_urls,preview_url,is_local)),next,total'
                )
                
                if not results or not results.get('items'):
                    break
                
                for item in results['items']:
                    if item is None:
                        continue
                    track_data = item.get('track')
                    if track_data is None:
                        continue
                    
                    track = Track.from_spotify_track(
                        track_data,
                        added_at=item.get('added_at')
                    )
                    if track:
                        added_by = item.get('added_by', {})
                        if added_by:
                            track.extra_details['added_by'] = added_by.get('id', '')
                        
                        if fetch_genres and track.artists:
                            track.genres = self._get_artist_genres(track_data.get('artists', []))
                        tracks.append(track)
                
                self._report_progress(
                    f"Fetching {playlist_name}: {len(tracks) + start_offset} tracks...",
                    len(tracks) + start_offset,
                    results.get('total', 0)
                )
                
                if results.get('next') is None:
                    return tracks, True, offset + limit
                    
                offset += limit
                time.sleep(0.1)
                
            except Exception as e:
                if self._handle_spotify_error(e, f"fetching tracks for {playlist_name}"):
                    return tracks, False, offset
                self._report_progress(f"Error fetching tracks for {playlist_name}: {str(e)}")
                break
        
        return tracks, True, offset
    
    def get_liked_songs(self, fetch_genres: bool = False, start_offset: int = 0) -> tuple[LikedSongs, bool, int]:
        """
        Fetch liked/saved songs.
        
        Returns:
            Tuple of (liked_songs, completed, last_offset)
        """
        if not self.is_authenticated():
            return LikedSongs(), False, 0
        
        if self.is_rate_limited():
            return LikedSongs(), False, start_offset
        
        liked = LikedSongs()
        offset = start_offset
        limit = 50
        
        self._report_progress("Fetching liked songs...")
        
        while True:
            try:
                results = self.sp.current_user_saved_tracks(limit=limit, offset=offset)
                
                if not results or not results.get('items'):
                    break
                
                total = results.get('total', 0)
                liked.total_tracks = total
                
                for item in results['items']:
                    if item is None:
                        continue
                    track_data = item.get('track')
                    if track_data is None:
                        continue
                    
                    track = Track.from_spotify_track(
                        track_data,
                        added_at=item.get('added_at')
                    )
                    if track:
                        if fetch_genres and track.artists:
                            track.genres = self._get_artist_genres(track_data.get('artists', []))
                        liked.tracks.append(track)
                
                self._report_progress(
                    f"Fetched {len(liked.tracks)} liked songs...",
                    len(liked.tracks),
                    total
                )
                
                if results.get('next') is None:
                    liked.last_synced = datetime.utcnow().isoformat() + 'Z'
                    return liked, True, offset + limit
                    
                offset += limit
                time.sleep(0.1)
                
            except Exception as e:
                if self._handle_spotify_error(e, "fetching liked songs"):
                    return liked, False, offset
                self._report_progress(f"Error fetching liked songs: {str(e)}")
                break
        
        liked.last_synced = datetime.utcnow().isoformat() + 'Z'
        return liked, True, offset
    
    def _get_artist_genres(self, artists: List[Dict[str, Any]]) -> List[str]:
        """Get genres from artist information with caching."""
        genres = set()
        
        for artist in artists[:3]:
            artist_id = artist.get('id')
            if not artist_id:
                continue
                
            if artist_id in self._artist_genres_cache:
                genres.update(self._artist_genres_cache[artist_id])
            else:
                try:
                    artist_info = self.sp.artist(artist_id)
                    artist_genres = artist_info.get('genres', [])
                    self._artist_genres_cache[artist_id] = artist_genres
                    genres.update(artist_genres)
                    time.sleep(0.05)
                except Exception as e:
                    if self._handle_spotify_error(e, "fetching artist genres"):
                        break
        
        return list(genres)
    
    def fetch_all_data(self, fetch_genres: bool = False, include_spotify_playlists: bool = True,
                       include_collab_playlists: bool = True, resume: bool = True) -> Dict[str, Any]:
        """
        Fetch all playlists with tracks and liked songs.
        Supports resuming from interrupted backups.
        
        Args:
            fetch_genres: Whether to fetch genre info
            include_spotify_playlists: Include Spotify-created playlists
            include_collab_playlists: Include collaborative playlists
            resume: Whether to try resuming from a previous interrupted backup
            
        Returns:
            Dictionary with all user data, or partial data if rate limited
        """
        if not self.is_authenticated():
            self._report_progress("Not authenticated!")
            return {}
        
        if self.is_rate_limited():
            self._report_progress(f"⚠️ Currently rate limited. Available at: {self.rate_limit_info.available_at_formatted}")
            return {'rate_limited': True, 'rate_limit_info': self.get_rate_limit_status()}
        
        user_info = self.get_user_info()
        self._report_progress(f"Fetching data for user: {user_info.get('display_name', user_info.get('id'))}")
        
        # Check for resume
        should_resume = resume and self.backup_progress.load() and self.backup_progress.has_pending_work()
        
        completed_playlists: List[Playlist] = []
        
        if should_resume:
            self._report_progress("📥 Resuming interrupted backup...")
            
            # Load already completed playlists from partial backup
            partial_backup_file = self.backup_progress.backup_dir / ".partial_backup.json"
            if partial_backup_file.exists():
                try:
                    with open(partial_backup_file, 'r') as f:
                        partial_data = json.load(f)
                    for p_dict in partial_data.get('playlists', []):
                        completed_playlists.append(Playlist.from_dict(p_dict))
                    self._report_progress(f"Loaded {len(completed_playlists)} previously completed playlists")
                except Exception as e:
                    self._report_progress(f"Could not load partial backup: {e}")
            
            playlists_to_process = [
                p for p in self.backup_progress.playlists_to_process 
                if p['id'] not in self.backup_progress.playlists_completed
            ]
        else:
            # Fresh start
            self.backup_progress.clear()
            
            # Get all playlists
            playlists = self.get_all_playlists(include_spotify_playlists, include_collab_playlists)
            
            if self.is_rate_limited():
                self._report_progress("Rate limited while fetching playlist list")
                return {'rate_limited': True, 'rate_limit_info': self.get_rate_limit_status()}
            
            playlists_to_process = [{'id': p.playlist_id, 'name': p.name} for p in playlists]
            self.backup_progress.playlists_to_process = playlists_to_process
            
            # Store playlist metadata
            for playlist in playlists:
                if playlist.playlist_id not in [p.playlist_id for p in completed_playlists]:
                    completed_playlists.append(playlist)
        
        self._report_progress(f"Processing {len(playlists_to_process)} playlists...")
        
        # Fetch tracks for each playlist
        total_playlists = len(playlists_to_process)
        
        for i, playlist_info in enumerate(playlists_to_process):
            playlist_id = playlist_info['id']
            playlist_name = playlist_info['name']
            
            # Find the playlist object
            target_playlist = None
            for p in completed_playlists:
                if p.playlist_id == playlist_id:
                    target_playlist = p
                    break
            
            if not target_playlist:
                continue
            
            self.backup_progress.current_playlist_id = playlist_id
            
            # Get start offset (for resume)
            start_offset = 0
            if should_resume and playlist_id == self.backup_progress.current_playlist_id:
                start_offset = self.backup_progress.current_playlist_offset
            
            self._report_progress(
                f"Fetching tracks for playlist {i+1}/{total_playlists}: {playlist_name}",
                i + 1,
                total_playlists
            )
            
            tracks, completed, last_offset = self.get_playlist_tracks(
                playlist_id, 
                playlist_name,
                fetch_genres,
                start_offset
            )
            
            # Merge tracks if resuming
            if start_offset > 0:
                target_playlist.tracks.extend(tracks)
            else:
                target_playlist.tracks = tracks
            
            if not completed:
                # Rate limited - save progress and return partial data
                self.backup_progress.current_playlist_offset = last_offset
                self.backup_progress.was_interrupted = True
                self.backup_progress.rate_limit_info = self.get_rate_limit_status()
                self.backup_progress.save()
                
                # Save partial backup
                self._save_partial_backup(completed_playlists, user_info)
                
                self._report_progress(
                    f"⚠️ Backup interrupted (rate limited). Progress saved. "
                    f"Available at: {self.rate_limit_info.available_at_formatted}"
                )
                
                return {
                    'rate_limited': True,
                    'rate_limit_info': self.get_rate_limit_status(),
                    'partial': True,
                    'playlists_completed': len(self.backup_progress.playlists_completed),
                    'playlists_total': len(self.backup_progress.playlists_to_process),
                    'can_resume': True
                }
            
            target_playlist.last_synced = datetime.utcnow().isoformat() + 'Z'
            self.backup_progress.playlists_completed.append(playlist_id)
            self.backup_progress.current_playlist_offset = 0
            self.backup_progress.save()
            
            self._report_progress(
                f"Playlist '{playlist_name}': {len(target_playlist.tracks)} tracks fetched",
                i + 1,
                total_playlists
            )
            
            time.sleep(0.2)
        
        # Get liked songs
        if not self.backup_progress.liked_songs_completed:
            self._report_progress("Fetching liked songs...")
            
            liked_songs, completed, last_offset = self.get_liked_songs(
                fetch_genres,
                self.backup_progress.liked_songs_offset
            )
            
            if not completed:
                self.backup_progress.liked_songs_offset = last_offset
                self.backup_progress.was_interrupted = True
                self.backup_progress.rate_limit_info = self.get_rate_limit_status()
                self.backup_progress.save()
                
                self._save_partial_backup(completed_playlists, user_info, liked_songs)
                
                self._report_progress(
                    f"⚠️ Backup interrupted during liked songs. Progress saved. "
                    f"Available at: {self.rate_limit_info.available_at_formatted}"
                )
                
                return {
                    'rate_limited': True,
                    'rate_limit_info': self.get_rate_limit_status(),
                    'partial': True,
                    'can_resume': True
                }
            
            self.backup_progress.liked_songs_completed = True
        else:
            # Load liked songs from partial backup
            partial_backup_file = self.backup_progress.backup_dir / ".partial_backup.json"
            if partial_backup_file.exists():
                with open(partial_backup_file, 'r') as f:
                    partial_data = json.load(f)
                liked_songs = LikedSongs.from_dict(partial_data.get('liked_songs', {}))
            else:
                liked_songs = LikedSongs()
        
        # Backup complete - clear progress
        self.backup_progress.clear()
        
        # Remove partial backup file
        partial_backup_file = self.backup_progress.backup_dir / ".partial_backup.json"
        if partial_backup_file.exists():
            partial_backup_file.unlink()
        
        self._report_progress(f"Backup complete! {len(completed_playlists)} playlists, {len(liked_songs.tracks)} liked songs")
        
        return {
            'user': {
                'id': user_info.get('id'),
                'display_name': user_info.get('display_name'),
                'email': user_info.get('email'),
            },
            'playlists': completed_playlists,
            'liked_songs': liked_songs,
            'fetched_at': datetime.utcnow().isoformat() + 'Z'
        }
    
    def _save_partial_backup(self, playlists: List[Playlist], user_info: Dict, 
                             liked_songs: Optional[LikedSongs] = None):
        """Save partial backup for resume."""
        partial_backup_file = self.backup_progress.backup_dir / ".partial_backup.json"
        
        data = {
            'user': {
                'id': user_info.get('id'),
                'display_name': user_info.get('display_name'),
                'email': user_info.get('email'),
            },
            'playlists': [p.to_dict() for p in playlists],
            'liked_songs': liked_songs.to_dict() if liked_songs else {},
            'saved_at': datetime.utcnow().isoformat() + 'Z'
        }
        
        self.backup_progress.backup_dir.mkdir(parents=True, exist_ok=True)
        with open(partial_backup_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def refresh_selected_playlists(self, playlist_data: List[Dict[str, str]],
                                   fetch_genres: bool = False) -> Dict[str, Any]:
        """
        Refresh only selected playlists.

        Args:
            playlist_data: List of dicts with 'id' and 'name' keys
            fetch_genres: Whether to fetch genre info

        Returns:
            Dictionary with refreshed playlists
        """
        if not self.is_authenticated():
            self._report_progress("Not authenticated!")
            return {}

        if self.is_rate_limited():
            self._report_progress(f"⚠️ Currently rate limited. Available at: {self.rate_limit_info.available_at_formatted}")
            return {'rate_limited': True, 'rate_limit_info': self.get_rate_limit_status()}

        user_info = self.get_user_info()
        self._report_progress(f"Refreshing {len(playlist_data)} selected playlist(s)...")

        refreshed_playlists: List[Playlist] = []
        total_playlists = len(playlist_data)

        for i, p_data in enumerate(playlist_data):
            playlist_id = p_data['id']
            playlist_name = p_data['name']

            self._report_progress(
                f"Fetching playlist {i+1}/{total_playlists}: {playlist_name}",
                i + 1,
                total_playlists
            )

            # Fetch playlist metadata
            try:
                playlist_info = self.sp.playlist(playlist_id)
                playlist = Playlist.from_spotify_playlist(playlist_info)

                # Fetch all tracks for this playlist
                tracks, completed, _ = self.get_playlist_tracks(
                    playlist_id,
                    playlist_name,
                    fetch_genres,
                    start_offset=0
                )

                if not completed:
                    # Rate limited
                    self._report_progress(
                        f"⚠️ Refresh interrupted (rate limited). "
                        f"Available at: {self.rate_limit_info.available_at_formatted}"
                    )
                    return {
                        'rate_limited': True,
                        'rate_limit_info': self.get_rate_limit_status(),
                        'partial': True,
                        'playlists_completed': i,
                        'playlists_total': total_playlists
                    }

                playlist.tracks = tracks
                playlist.last_synced = datetime.utcnow().isoformat() + 'Z'
                refreshed_playlists.append(playlist)

                self._report_progress(
                    f"Playlist '{playlist_name}': {len(tracks)} tracks fetched",
                    i + 1,
                    total_playlists
                )

            except Exception as e:
                if self._handle_spotify_error(e, f"refreshing playlist {playlist_name}"):
                    return {
                        'rate_limited': True,
                        'rate_limit_info': self.get_rate_limit_status()
                    }
                self._report_progress(f"Error refreshing playlist {playlist_name}: {str(e)}")
                continue

        self._report_progress(f"Refresh complete! {len(refreshed_playlists)} playlist(s) updated")

        return {
            'user': {
                'id': user_info.get('id'),
                'display_name': user_info.get('display_name'),
                'email': user_info.get('email'),
            },
            'playlists': refreshed_playlists,
            'refreshed_at': datetime.utcnow().isoformat() + 'Z'
        }

    def get_playlist_snapshot_ids(self) -> Dict[str, str]:
        """Get snapshot IDs for all playlists (for incremental updates)."""
        if not self.is_authenticated():
            return {}
        
        snapshots = {}
        offset = 0
        limit = 50
        
        while True:
            try:
                results = self.sp.current_user_playlists(limit=limit, offset=offset)
                
                if not results or not results.get('items'):
                    break
                
                for item in results['items']:
                    if item:
                        snapshots[item['id']] = item.get('snapshot_id', '')
                
                if results.get('next') is None:
                    break
                    
                offset += limit
                
            except Exception as e:
                if self._handle_spotify_error(e, "fetching snapshots"):
                    break
        
        return snapshots
    
    def can_resume_backup(self) -> bool:
        """Check if there's an interrupted backup that can be resumed."""
        return self.backup_progress.load() and self.backup_progress.has_pending_work()
    
    def get_resume_info(self) -> Dict[str, Any]:
        """Get information about resumable backup."""
        if not self.backup_progress.load():
            return {'can_resume': False}
        
        return {
            'can_resume': self.backup_progress.has_pending_work(),
            'playlists_completed': len(self.backup_progress.playlists_completed),
            'playlists_total': len(self.backup_progress.playlists_to_process),
            'liked_songs_completed': self.backup_progress.liked_songs_completed,
            'rate_limit_info': self.backup_progress.rate_limit_info
        }