"""
Playlist and folder data models.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional, List, Dict, Any
from .track import Track


@dataclass
class Playlist:
    """Represents a Spotify playlist with all its tracks."""
    
    # Core identifiers
    playlist_id: str
    uri: str
    
    # Playlist information
    name: str
    description: Optional[str] = None
    owner_id: str = ""
    owner_name: str = ""
    
    # Playlist properties
    is_public: bool = True
    is_collaborative: bool = False
    
    # Folder information (for organization)
    folder_path: Optional[str] = None  # e.g., "Music/Rock/Classic"
    
    # Display order (for manual sorting)
    display_order: int = 0
    
    # Tracks
    tracks: List[Track] = field(default_factory=list)
    total_tracks: int = 0
    
    # Timestamps
    snapshot_id: str = ""  # Spotify's version identifier
    last_synced: Optional[str] = None
    
    # External links
    external_urls: Dict[str, str] = field(default_factory=dict)
    
    # Images
    images: List[Dict[str, Any]] = field(default_factory=list)
    
    # Additional metadata
    extra_details: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Clean up data after initialization."""
        if self.external_urls is None:
            self.external_urls = {}
        if self.images is None:
            self.images = []
        if self.extra_details is None:
            self.extra_details = {}
        if self.tracks is None:
            self.tracks = []
    
    @property
    def track_count(self) -> int:
        """Return actual number of tracks in the list."""
        return len(self.tracks)
    
    @property
    def total_duration_ms(self) -> int:
        """Calculate total duration of all tracks."""
        return sum(track.duration_ms for track in self.tracks)
    
    @property
    def total_duration_formatted(self) -> str:
        """Return total duration as HH:MM:SS format."""
        total_seconds = self.total_duration_ms // 1000
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        if hours > 0:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        return f"{minutes}:{seconds:02d}"
    
    def get_track_index(self, track_id: str) -> int:
        """Get the index of a track in the playlist by track_id."""
        for i, track in enumerate(self.tracks):
            if track.track_id == track_id:
                return i
        return -1
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert playlist to dictionary for JSON serialization."""
        data = {
            'playlist_id': self.playlist_id,
            'uri': self.uri,
            'name': self.name,
            'description': self.description,
            'owner_id': self.owner_id,
            'owner_name': self.owner_name,
            'is_public': self.is_public,
            'is_collaborative': self.is_collaborative,
            'folder_path': self.folder_path,
            'display_order': self.display_order,
            'total_tracks': self.total_tracks,
            'snapshot_id': self.snapshot_id,
            'last_synced': self.last_synced,
            'external_urls': self.external_urls,
            'images': self.images,
            'extra_details': self.extra_details,
            'tracks': [track.to_dict() for track in self.tracks]
        }
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Playlist':
        """Create Playlist instance from dictionary."""
        tracks_data = data.pop('tracks', [])
        
        # Provide defaults
        defaults = {
            'playlist_id': '',
            'uri': '',
            'name': 'Unknown Playlist',
            'description': None,
            'owner_id': '',
            'owner_name': '',
            'is_public': True,
            'is_collaborative': False,
            'folder_path': None,
            'display_order': 0,
            'total_tracks': 0,
            'snapshot_id': '',
            'last_synced': None,
            'external_urls': {},
            'images': [],
            'extra_details': {},
        }
        
        # Merge defaults
        for key, default_value in defaults.items():
            if key not in data:
                data[key] = default_value
        
        # Filter to known fields
        known_fields = set(defaults.keys())
        filtered_data = {k: v for k, v in data.items() if k in known_fields}
        
        playlist = cls(**filtered_data)
        playlist.tracks = [Track.from_dict(t) for t in tracks_data]
        return playlist
    
    @classmethod
    def from_spotify_playlist(cls, playlist_data: Dict[str, Any]) -> 'Playlist':
        """
        Create Playlist instance from Spotify API response.
        Note: Tracks are not included here, they should be fetched separately.
        """
        owner = playlist_data.get('owner', {}) or {}
        
        return cls(
            playlist_id=playlist_data.get('id') or '',
            uri=playlist_data.get('uri') or '',
            name=playlist_data.get('name') or 'Unknown Playlist',
            description=playlist_data.get('description'),
            owner_id=owner.get('id') or '',
            owner_name=owner.get('display_name') or '',
            is_public=playlist_data.get('public', True),
            is_collaborative=playlist_data.get('collaborative', False),
            total_tracks=playlist_data.get('tracks', {}).get('total', 0),
            snapshot_id=playlist_data.get('snapshot_id') or '',
            external_urls=playlist_data.get('external_urls') or {},
            images=playlist_data.get('images') or [],
        )
    
    def add_track(self, track: Track):
        """Add a track to the playlist."""
        if track not in self.tracks:
            self.tracks.append(track)
    
    def remove_track(self, track: Track):
        """Remove a track from the playlist."""
        if track in self.tracks:
            self.tracks.remove(track)
    
    def get_tracks_by_artist(self, artist_name: str) -> List[Track]:
        """Get all tracks by a specific artist."""
        return [t for t in self.tracks if artist_name.lower() in [a.lower() for a in t.artists]]
    
    def get_tracks_by_album(self, album_name: str) -> List[Track]:
        """Get all tracks from a specific album."""
        return [t for t in self.tracks if album_name.lower() in t.album_name.lower()]


@dataclass
class PlaylistFolder:
    """
    Represents a folder structure for organizing playlists.
    Note: Spotify API doesn't expose folder structure directly,
    this is for manual organization in the backup.
    """
    
    name: str
    path: str  # Full path like "Music/Rock"
    parent_path: Optional[str] = None
    playlists: List[str] = field(default_factory=list)  # List of playlist IDs
    subfolders: List['PlaylistFolder'] = field(default_factory=list)
    display_order: int = 0
    is_expanded: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert folder to dictionary."""
        return {
            'name': self.name,
            'path': self.path,
            'parent_path': self.parent_path,
            'playlists': self.playlists,
            'subfolders': [sf.to_dict() for sf in self.subfolders],
            'display_order': self.display_order,
            'is_expanded': self.is_expanded,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PlaylistFolder':
        """Create PlaylistFolder from dictionary."""
        subfolders_data = data.pop('subfolders', [])
        
        # Provide defaults
        if 'display_order' not in data:
            data['display_order'] = 0
        if 'is_expanded' not in data:
            data['is_expanded'] = True
        if 'playlists' not in data:
            data['playlists'] = []
        
        folder = cls(**data)
        folder.subfolders = [cls.from_dict(sf) for sf in subfolders_data]
        return folder


@dataclass
class LikedSongs:
    """Special container for the user's Liked Songs."""
    
    tracks: List[Track] = field(default_factory=list)
    total_tracks: int = 0
    last_synced: Optional[str] = None
    
    @property
    def track_count(self) -> int:
        return len(self.tracks)
    
    @property
    def total_duration_ms(self) -> int:
        return sum(track.duration_ms for track in self.tracks)
    
    def get_track_index(self, track_id: str) -> int:
        """Get the index of a track by track_id."""
        for i, track in enumerate(self.tracks):
            if track.track_id == track_id:
                return i
        return -1
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'tracks': [track.to_dict() for track in self.tracks],
            'total_tracks': self.total_tracks,
            'last_synced': self.last_synced
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LikedSongs':
        tracks_data = data.pop('tracks', [])
        liked = cls(**data)
        liked.tracks = [Track.from_dict(t) for t in tracks_data]
        return liked