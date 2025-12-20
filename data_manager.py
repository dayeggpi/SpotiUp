"""
Data manager for saving, loading, and updating backup data.
Handles JSON serialization and incremental updates.
"""

import json
import os
import csv
import shutil
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path

from models import Track, Playlist
from models.playlist import LikedSongs, PlaylistFolder


class DataManager:
    """Manages backup data storage and incremental updates."""
    
    def __init__(self, backup_dir: str):
        """
        Initialize the data manager.
        
        Args:
            backup_dir: Directory to store backup files
        """
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # File paths
        self.main_backup_file = self.backup_dir / "spotify_backup.json"
        self.liked_songs_file = self.backup_dir / "liked_songs.json"
        self.folders_file = self.backup_dir / "folders.json"
        self.history_dir = self.backup_dir / "history"
        self.history_dir.mkdir(exist_ok=True)
    
    def save_full_backup(self, data: Dict[str, Any]) -> str:
        """
        Save a complete backup of all data.
        
        Args:
            data: Dictionary containing playlists, liked songs, user info
            
        Returns:
            Path to the saved file
        """
        # Create backup structure
        backup_data = {
            'version': '1.0',
            'exported_at': datetime.utcnow().isoformat() + 'Z',
            'user': data.get('user', {}),
            'playlists': [],
            'playlist_count': 0,
            'total_tracks': 0,
        }
        
        # Process playlists - convert Playlist objects to dicts
        playlists = data.get('playlists', [])
        total_tracks = 0
        
        print(f"DEBUG: Saving {len(playlists)} playlists...")  # Debug line
        
        for playlist in playlists:
            if isinstance(playlist, Playlist):
                playlist_dict = playlist.to_dict()
            elif isinstance(playlist, dict):
                playlist_dict = playlist
            else:
                print(f"DEBUG: Unknown playlist type: {type(playlist)}")  # Debug line
                continue
                
            backup_data['playlists'].append(playlist_dict)
            track_count = len(playlist_dict.get('tracks', []))
            total_tracks += track_count
            print(f"DEBUG: Saved playlist '{playlist_dict.get('name')}' with {track_count} tracks")  # Debug line
        
        backup_data['playlist_count'] = len(backup_data['playlists'])
        backup_data['total_tracks'] = total_tracks
        
        print(f"DEBUG: Total playlists to save: {backup_data['playlist_count']}")  # Debug line
        print(f"DEBUG: Total tracks to save: {backup_data['total_tracks']}")  # Debug line
        
        # Save main backup
        self._save_json(self.main_backup_file, backup_data)
        print(f"DEBUG: Saved main backup to {self.main_backup_file}")  # Debug line
        
        # Save liked songs separately
        liked_songs = data.get('liked_songs')
        if liked_songs:
            if isinstance(liked_songs, LikedSongs):
                liked_dict = liked_songs.to_dict()
            elif isinstance(liked_songs, dict):
                liked_dict = liked_songs
            else:
                liked_dict = {'tracks': [], 'total_tracks': 0}
                
            self._save_json(self.liked_songs_file, {
                'version': '1.0',
                'exported_at': datetime.utcnow().isoformat() + 'Z',
                'liked_songs': liked_dict
            })
            print(f"DEBUG: Saved liked songs to {self.liked_songs_file}")  # Debug line
        
        # Create timestamped history backup
        self._create_history_backup()
        
        return str(self.main_backup_file)
    
    def load_backup(self) -> Optional[Dict[str, Any]]:
        """
        Load the current backup data.
        
        Returns:
            Dictionary with backup data or None if not found
        """
        if not self.main_backup_file.exists():
            return None
        
        data = self._load_json(self.main_backup_file)
        
        # Load liked songs
        if self.liked_songs_file.exists():
            liked_data = self._load_json(self.liked_songs_file)
            data['liked_songs'] = liked_data.get('liked_songs', {})
        
        # Load folders
        if self.folders_file.exists():
            folders_data = self._load_json(self.folders_file)
            data['folders'] = folders_data.get('folders', [])
        
        return data
    
    def get_playlists(self) -> List[Playlist]:
        """Load and return playlists as Playlist objects."""
        data = self.load_backup()
        if not data:
            return []
        
        playlists = []
        for p_dict in data.get('playlists', []):
            try:
                playlists.append(Playlist.from_dict(p_dict))
            except Exception as e:
                print(f"Error loading playlist: {e}")
        return playlists
    
    def get_liked_songs(self) -> Optional[LikedSongs]:
        """Load and return liked songs."""
        if not self.liked_songs_file.exists():
            return None
        
        data = self._load_json(self.liked_songs_file)
        liked_dict = data.get('liked_songs', {})
        return LikedSongs.from_dict(liked_dict)
    
    def update_incremental(
        self,
        new_playlists: List,
        new_liked_songs: Optional[Any] = None,
        old_snapshot_ids: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Perform incremental update, only updating changed playlists.
        
        Args:
            new_playlists: List of playlists fetched from Spotify
            new_liked_songs: New liked songs data
            old_snapshot_ids: Previous snapshot IDs for comparison
            
        Returns:
            Dictionary with update statistics
        """
        stats = {
            'playlists_added': 0,
            'playlists_updated': 0,
            'playlists_removed': 0,
            'tracks_added': 0,
            'tracks_removed': 0,
        }
        
        # Load existing data
        existing_data = self.load_backup()
        if not existing_data:
            # No existing data, do full save
            self.save_full_backup({
                'playlists': new_playlists,
                'liked_songs': new_liked_songs,
            })
            return stats
        
        existing_playlists = {
            p['playlist_id']: p for p in existing_data.get('playlists', [])
        }
        
        # Track changes
        updated_playlists = []
        new_playlist_ids = set()
        
        for playlist in new_playlists:
            # Convert to dict if needed
            if isinstance(playlist, Playlist):
                playlist_dict = playlist.to_dict()
            else:
                playlist_dict = playlist
                
            playlist_id = playlist_dict.get('playlist_id', '')
            new_playlist_ids.add(playlist_id)
            
            if playlist_id in existing_playlists:
                old_playlist = existing_playlists[playlist_id]
                
                # Check if playlist was updated (using snapshot_id)
                old_snapshot = old_playlist.get('snapshot_id', '')
                new_snapshot = playlist_dict.get('snapshot_id', '')
                
                if old_snapshot != new_snapshot:
                    # Playlist was modified
                    stats['playlists_updated'] += 1
                    
                    # Calculate track changes
                    old_track_ids = {t.get('track_id', '') for t in old_playlist.get('tracks', [])}
                    new_track_ids = {t.get('track_id', '') for t in playlist_dict.get('tracks', [])}
                    
                    stats['tracks_added'] += len(new_track_ids - old_track_ids)
                    stats['tracks_removed'] += len(old_track_ids - new_track_ids)
                    
                    updated_playlists.append(playlist_dict)
                else:
                    # No changes, keep existing
                    updated_playlists.append(old_playlist)
            else:
                # New playlist
                stats['playlists_added'] += 1
                stats['tracks_added'] += len(playlist_dict.get('tracks', []))
                updated_playlists.append(playlist_dict)
        
        # Check for removed playlists
        removed_ids = set(existing_playlists.keys()) - new_playlist_ids
        stats['playlists_removed'] = len(removed_ids)
        for removed_id in removed_ids:
            stats['tracks_removed'] += len(existing_playlists[removed_id].get('tracks', []))
        
        # Update liked songs
        if new_liked_songs:
            existing_liked = existing_data.get('liked_songs', {})
            if isinstance(existing_liked, dict):
                old_liked_ids = {t.get('track_id', '') for t in existing_liked.get('tracks', [])}
            else:
                old_liked_ids = set()
            
            if isinstance(new_liked_songs, LikedSongs):
                new_liked_ids = {t.track_id for t in new_liked_songs.tracks}
            elif isinstance(new_liked_songs, dict):
                new_liked_ids = {t.get('track_id', '') for t in new_liked_songs.get('tracks', [])}
            else:
                new_liked_ids = set()
            
            stats['tracks_added'] += len(new_liked_ids - old_liked_ids)
            stats['tracks_removed'] += len(old_liked_ids - new_liked_ids)
        
        # Save updated data
        existing_data['playlists'] = updated_playlists
        existing_data['exported_at'] = datetime.utcnow().isoformat() + 'Z'
        existing_data['playlist_count'] = len(updated_playlists)
        existing_data['total_tracks'] = sum(
            len(p.get('tracks', [])) for p in updated_playlists
        )
        
        self._save_json(self.main_backup_file, existing_data)
        
        if new_liked_songs:
            if isinstance(new_liked_songs, LikedSongs):
                liked_dict = new_liked_songs.to_dict()
            elif isinstance(new_liked_songs, dict):
                liked_dict = new_liked_songs
            else:
                liked_dict = {'tracks': [], 'total_tracks': 0}
                
            self._save_json(self.liked_songs_file, {
                'version': '1.0',
                'exported_at': datetime.utcnow().isoformat() + 'Z',
                'liked_songs': liked_dict
            })
        
        # Create history entry
        self._save_update_log(stats)
        
        return stats

    def update_selected_playlists(self, refreshed_playlists: List) -> Dict[str, Any]:
        """
        Update only selected playlists in the backup.

        Args:
            refreshed_playlists: List of refreshed Playlist objects

        Returns:
            Dictionary with update statistics
        """
        stats = {
            'playlists_updated': 0,
            'tracks_added': 0,
            'tracks_removed': 0,
            'tracks_updated': 0,
        }

        # Load existing data
        existing_data = self.load_backup()
        if not existing_data:
            # No existing data, can't update
            return stats

        existing_playlists = {
            p['playlist_id']: p for p in existing_data.get('playlists', [])
        }

        # Update the refreshed playlists
        for playlist in refreshed_playlists:
            # Convert to dict if needed
            if isinstance(playlist, Playlist):
                playlist_dict = playlist.to_dict()
            else:
                playlist_dict = playlist

            playlist_id = playlist_dict.get('playlist_id', '')

            if playlist_id in existing_playlists:
                old_playlist = existing_playlists[playlist_id]

                # Calculate track changes
                old_track_ids = {t.get('track_id', '') for t in old_playlist.get('tracks', [])}
                new_track_ids = {t.get('track_id', '') for t in playlist_dict.get('tracks', [])}

                stats['tracks_added'] += len(new_track_ids - old_track_ids)
                stats['tracks_removed'] += len(old_track_ids - new_track_ids)
                stats['tracks_updated'] += len(new_track_ids & old_track_ids)
                stats['playlists_updated'] += 1

                # Update the playlist
                existing_playlists[playlist_id] = playlist_dict

        # Rebuild the playlists list maintaining order
        updated_playlists = []
        for p in existing_data.get('playlists', []):
            playlist_id = p.get('playlist_id', '')
            if playlist_id in existing_playlists:
                updated_playlists.append(existing_playlists[playlist_id])
            else:
                updated_playlists.append(p)

        # Save updated data
        existing_data['playlists'] = updated_playlists
        existing_data['exported_at'] = datetime.utcnow().isoformat() + 'Z'
        existing_data['total_tracks'] = sum(
            len(p.get('tracks', [])) for p in updated_playlists
        )

        self._save_json(self.main_backup_file, existing_data)

        # Create history entry
        self._save_update_log({
            'type': 'selective_refresh',
            **stats
        })

        return stats

    def save_folders(self, folders: List[PlaylistFolder]):
        """Save folder organization."""
        folders_data = {
            'version': '1.0',
            'updated_at': datetime.utcnow().isoformat() + 'Z',
            'folders': [f.to_dict() for f in folders]
        }
        self._save_json(self.folders_file, folders_data)
    
    def get_folders(self) -> List[PlaylistFolder]:
        """Load folder organization."""
        if not self.folders_file.exists():
            return []
        
        data = self._load_json(self.folders_file)
        return [PlaylistFolder.from_dict(f) for f in data.get('folders', [])]
    
    def search_tracks(
        self,
        query: str,
        search_in: str = 'all'
    ) -> List[Tuple[str, Track]]:
        """
        Search for tracks across all playlists.
        
        Args:
            query: Search query string
            search_in: Where to search ('all', 'playlists', 'liked')
            
        Returns:
            List of (playlist_name, Track) tuples
        """
        results = []
        query = query.lower()
        
        if search_in in ('all', 'playlists'):
            for playlist in self.get_playlists():
                for track in playlist.tracks:
                    if self._track_matches(track, query):
                        results.append((playlist.name, track))
        
        if search_in in ('all', 'liked'):
            liked = self.get_liked_songs()
            if liked:
                for track in liked.tracks:
                    if self._track_matches(track, query):
                        results.append(('Liked Songs', track))
        
        return results
        
    def _track_matches(self, track: Track, query: str) -> bool:
        """Check if a track matches the search query."""
        try:
            searchable = []
            
            # Safely get track name
            if track.name:
                searchable.append(track.name.lower())
            
            # Safely get artists string
            try:
                artists_str = track.artists_string
                if artists_str:
                    searchable.append(artists_str.lower())
            except (TypeError, AttributeError):
                pass
            
            # Safely get album name
            if track.album_name:
                searchable.append(track.album_name.lower())
            
            # Safely get genres
            if track.genres:
                for genre in track.genres:
                    if genre:
                        searchable.append(genre.lower())
            
            return any(query in s for s in searchable if s)
        except Exception as e:
            print(f"DEBUG: Error matching track: {e}")
            return False
    
    def search_playlists(self, query: str) -> List[Playlist]:
        """Search for playlists by name or description."""
        query = query.lower()
        results = []
        
        for playlist in self.get_playlists():
            if query in playlist.name.lower():
                results.append(playlist)
            elif playlist.description and query in playlist.description.lower():
                results.append(playlist)
        
        return results
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about the backup."""
        data = self.load_backup()
        if not data:
            return {}
        
        playlists = data.get('playlists', [])
        liked = data.get('liked_songs', {})
        
        # Handle liked songs as dict or object
        if isinstance(liked, dict):
            liked_tracks = liked.get('tracks', [])
        elif isinstance(liked, LikedSongs):
            liked_tracks = [t.to_dict() for t in liked.tracks]
        else:
            liked_tracks = []
        
        # Collect all unique tracks and artists
        all_tracks = set()
        all_artists = set()
        all_albums = set()
        all_genres = set()
        total_duration = 0
        
        for playlist in playlists:
            for track in playlist.get('tracks', []):
                all_tracks.add(track.get('track_id', ''))
                all_artists.update(track.get('artists', []))
                all_albums.add(track.get('album_name', ''))
                all_genres.update(track.get('genres', []))
                total_duration += track.get('duration_ms', 0)
        
        for track in liked_tracks:
            all_tracks.add(track.get('track_id', ''))
            all_artists.update(track.get('artists', []))
            all_albums.add(track.get('album_name', ''))
            all_genres.update(track.get('genres', []))
            total_duration += track.get('duration_ms', 0)
        
        return {
            'playlist_count': len(playlists),
            'liked_songs_count': len(liked_tracks),
            'unique_tracks': len(all_tracks),
            'unique_artists': len(all_artists),
            'unique_albums': len(all_albums),
            'genres_found': len(all_genres),
            'total_duration_hours': round(total_duration / (1000 * 60 * 60), 2),
            'last_backup': data.get('exported_at'),
        }
        
    def export_to_csv(self, file_path: Optional[str] = None) -> Optional[str]:
        """Export all data to CSV format."""
        data = self.load_backup()
        if not data:
            return None
        
        if file_path is None:
            file_path = self.backup_dir / f"spotify_export_{datetime.now().strftime('%Y%m%d')}.csv"
        
        file_path = Path(file_path)
        
        with open(file_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # Header
            writer.writerow([
                'Source', 'Playlist Name', 'Track Name', 'Artists', 'Album',
                'Duration (ms)', 'Added At', 'Spotify URI', 'Is Local'
            ])
            
            # Playlist tracks
            for playlist in data.get('playlists', []):
                if isinstance(playlist, dict):
                    playlist_name = playlist.get('name', 'Unknown')
                    tracks = playlist.get('tracks', [])
                else:
                    playlist_name = playlist.name
                    tracks = playlist.tracks
                
                for track in tracks:
                    if isinstance(track, dict):
                        # Filter out None values from artists list
                        artists = track.get('artists', [])
                        artists_str = ', '.join([a for a in artists if a]) if artists else ''
                        
                        writer.writerow([
                            'Playlist',
                            playlist_name,
                            track.get('name', ''),
                            artists_str,
                            track.get('album_name', ''),
                            track.get('duration_ms', 0),
                            track.get('added_at', ''),
                            track.get('uri', ''),
                            track.get('is_local', False)
                        ])
                    else:
                        # Track object - filter out None values from artists list
                        artists_str = ', '.join([a for a in track.artists if a]) if track.artists else ''
                        
                        writer.writerow([
                            'Playlist',
                            playlist_name,
                            track.name or '',
                            artists_str,
                            track.album_name or '',
                            track.duration_ms,
                            track.added_at or '',
                            track.uri or '',
                            track.is_local
                        ])
            
            # Liked songs
            liked_songs = data.get('liked_songs', {})
            if liked_songs:
                if isinstance(liked_songs, dict):
                    tracks = liked_songs.get('tracks', [])
                else:
                    tracks = liked_songs.tracks
                
                for track in tracks:
                    if isinstance(track, dict):
                        artists = track.get('artists', [])
                        artists_str = ', '.join([a for a in artists if a]) if artists else ''
                        
                        writer.writerow([
                            'Liked Songs',
                            'Liked Songs',
                            track.get('name', ''),
                            artists_str,
                            track.get('album_name', ''),
                            track.get('duration_ms', 0),
                            track.get('added_at', ''),
                            track.get('uri', ''),
                            track.get('is_local', False)
                        ])
                    else:
                        artists_str = ', '.join([a for a in track.artists if a]) if track.artists else ''
                        
                        writer.writerow([
                            'Liked Songs',
                            'Liked Songs',
                            track.name or '',
                            artists_str,
                            track.album_name or '',
                            track.duration_ms,
                            track.added_at or '',
                            track.uri or '',
                            track.is_local
                        ])
        
        return str(file_path)
    
    def _format_duration(self, duration_ms: int) -> str:
        """Format duration in MM:SS."""
        total_seconds = duration_ms // 1000
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        return f"{minutes}:{seconds:02d}"
    
    def _save_json(self, path: Path, data: Dict[str, Any]):
        """Save data to JSON file with pretty printing."""
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def _load_json(self, path: Path) -> Dict[str, Any]:
        """Load data from JSON file."""
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _create_history_backup(self):
        """Create a timestamped backup in history folder."""
        if self.main_backup_file.exists():
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            history_file = self.history_dir / f"backup_{timestamp}.json"
            shutil.copy(self.main_backup_file, history_file)
            
            # Keep only last 10 history files
            history_files = sorted(self.history_dir.glob('backup_*.json'))
            for old_file in history_files[:-10]:
                old_file.unlink()
    
    def _save_update_log(self, stats: Dict[str, Any]):
        """Save update statistics to log file."""
        log_file = self.backup_dir / "update_log.json"
        
        logs = []
        if log_file.exists():
            with open(log_file, 'r') as f:
                logs = json.load(f)
        
        logs.append({
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'stats': stats
        })
        
        # Keep last 100 entries
        logs = logs[-100:]
        
        with open(log_file, 'w') as f:
            json.dump(logs, f, indent=2)