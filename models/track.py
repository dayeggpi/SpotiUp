"""
Track data model for Spotify tracks.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional, List, Dict, Any
import json


@dataclass
class Track:
    """Represents a Spotify track with all relevant metadata."""
    
    # Core identifiers
    track_id: str
    uri: str
    
    # Track information
    name: str
    artists: List[str]
    album_name: str
    album_id: str
    
    # Timing information
    duration_ms: int
    added_at: Optional[str] = None  # ISO format datetime string
    
    # Additional metadata
    track_number: int = 0
    disc_number: int = 1
    explicit: bool = False
    popularity: int = 0
    
    # Audio features (optional, requires additional API call)
    genres: List[str] = field(default_factory=list)
    
    # Release information
    release_date: Optional[str] = None
    
    # External links
    external_urls: Dict[str, str] = field(default_factory=dict)
    preview_url: Optional[str] = None
    
    # Local track flag
    is_local: bool = False
    
    # Additional details for future extension
    extra_details: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Clean up data after initialization."""
        # Ensure artists is a list of non-None strings
        if self.artists is None:
            self.artists = []
        else:
            self.artists = [a for a in self.artists if a is not None]
        
        # Ensure genres is a list of non-None strings
        if self.genres is None:
            self.genres = []
        else:
            self.genres = [g for g in self.genres if g is not None]
        
        # Ensure external_urls is a dict
        if self.external_urls is None:
            self.external_urls = {}
        
        # Ensure extra_details is a dict
        if self.extra_details is None:
            self.extra_details = {}
        
        # Ensure name is not None
        if self.name is None:
            self.name = "Unknown Track"
        
        # Ensure album_name is not None
        if self.album_name is None:
            self.album_name = "Unknown Album"
        
        # Ensure track_id is not None
        if self.track_id is None:
            self.track_id = ""
        
        # Ensure uri is not None
        if self.uri is None:
            self.uri = ""
        
        # Ensure album_id is not None
        if self.album_id is None:
            self.album_id = ""
    
    @property
    def duration_formatted(self) -> str:
        """Return duration as MM:SS format."""
        total_seconds = (self.duration_ms or 0) // 1000
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        return f"{minutes}:{seconds:02d}"
    
    @property
    def artists_string(self) -> str:
        """Return artists as comma-separated string."""
        if not self.artists:
            return "Unknown Artist"
        # Filter out None values just in case
        valid_artists = [a for a in self.artists if a]
        return ", ".join(valid_artists) if valid_artists else "Unknown Artist"
    
    @property
    def added_datetime(self) -> Optional[datetime]:
        """Parse added_at string to datetime object."""
        if self.added_at:
            try:
                return datetime.fromisoformat(self.added_at.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                return None
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert track to dictionary for JSON serialization."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Track':
        """Create Track instance from dictionary."""
        # Clean up artists list before creating instance
        artists = data.get('artists', [])
        if artists is None:
            artists = []
        else:
            artists = [a for a in artists if a is not None]
        data['artists'] = artists
        
        # Clean up genres list
        genres = data.get('genres', [])
        if genres is None:
            genres = []
        else:
            genres = [g for g in genres if g is not None]
        data['genres'] = genres
        
        # Provide defaults for required fields
        defaults = {
            'track_id': '',
            'uri': '',
            'name': 'Unknown Track',
            'artists': [],
            'album_name': 'Unknown Album',
            'album_id': '',
            'duration_ms': 0,
            'added_at': None,
            'track_number': 0,
            'disc_number': 1,
            'explicit': False,
            'popularity': 0,
            'genres': [],
            'release_date': None,
            'external_urls': {},
            'preview_url': None,
            'is_local': False,
            'extra_details': {},
        }
        
        # Merge defaults with provided data
        for key, default_value in defaults.items():
            if key not in data or data[key] is None:
                if key not in ['added_at', 'release_date', 'preview_url']:  # These can be None
                    data[key] = default_value
        
        # Only pass known fields to avoid errors
        known_fields = set(defaults.keys())
        filtered_data = {k: v for k, v in data.items() if k in known_fields}
        
        return cls(**filtered_data)
    
    @classmethod
    def from_spotify_track(cls, track_data: Dict[str, Any], added_at: Optional[str] = None) -> Optional['Track']:
        """
        Create Track instance from Spotify API response.
        
        Args:
            track_data: The 'track' object from Spotify API
            added_at: When the track was added (from playlist item)
        """
        if track_data is None:
            return None
            
        # Handle local tracks
        is_local = track_data.get('is_local', False)
        
        # Extract artists - filter out None values
        artists_data = track_data.get('artists', []) or []
        artists = []
        for artist in artists_data:
            if artist and isinstance(artist, dict):
                name = artist.get('name')
                if name:
                    artists.append(name)
            elif artist and isinstance(artist, str):
                artists.append(artist)
        
        # If no valid artists, use placeholder
        if not artists:
            artists = ["Unknown Artist"]
        
        # Extract album info
        album = track_data.get('album') or {}
        
        return cls(
            track_id=track_data.get('id') or '',
            uri=track_data.get('uri') or '',
            name=track_data.get('name') or 'Unknown Track',
            artists=artists,
            album_name=album.get('name') or 'Unknown Album',
            album_id=album.get('id') or '',
            duration_ms=track_data.get('duration_ms') or 0,
            added_at=added_at,
            track_number=track_data.get('track_number') or 0,
            disc_number=track_data.get('disc_number') or 1,
            explicit=track_data.get('explicit') or False,
            popularity=track_data.get('popularity') or 0,
            release_date=album.get('release_date'),
            external_urls=track_data.get('external_urls') or {},
            preview_url=track_data.get('preview_url'),
            is_local=is_local,
        )
    
    def __eq__(self, other):
        if isinstance(other, Track):
            return self.track_id == other.track_id and self.uri == other.uri
        return False
    
    def __hash__(self):
        return hash((self.track_id, self.uri))