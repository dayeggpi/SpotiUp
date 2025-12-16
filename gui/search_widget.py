"""
Search widget for finding tracks and playlists.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton,
    QComboBox, QTableWidget, QTableWidgetItem, QHeaderView,
    QLabel, QAbstractItemView, QMenu
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QAction, QDesktopServices
from PyQt6.QtCore import QUrl
from typing import List, Tuple
import subprocess
import platform

from models import Track, Playlist
from data_manager import DataManager


class SearchWidget(QWidget):
    """Widget for searching tracks and playlists."""
    
    # Signals
    track_selected = pyqtSignal(str, str, object)  # playlist_id, track_id, Track
    playlist_selected = pyqtSignal(object)  # Playlist
    
    def __init__(self, data_manager: DataManager, parent=None):
        super().__init__(parent)
        self.data_manager = data_manager
        self._search_results = []
        
        self._setup_ui()
        
        self._search_timer = QTimer()
        self._search_timer.setSingleShot(True)
        self._search_timer.timeout.connect(self._do_search)
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Search controls
        search_layout = QHBoxLayout()
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search tracks, artists, albums, playlists...")
        self.search_input.textChanged.connect(self._on_search_text_changed)
        self.search_input.returnPressed.connect(self._do_search)
        search_layout.addWidget(self.search_input)
        
        self.search_type = QComboBox()
        self.search_type.addItems(["All", "Tracks Only", "Playlists Only", "Liked Songs Only"])
        self.search_type.currentIndexChanged.connect(self._do_search)
        search_layout.addWidget(self.search_type)
        
        self.search_btn = QPushButton("Search")
        self.search_btn.clicked.connect(self._do_search)
        search_layout.addWidget(self.search_btn)
        
        layout.addLayout(search_layout)
        
        # Results count
        self.results_label = QLabel("")
        layout.addWidget(self.results_label)
        
        # Help text - UPDATED
        help_label = QLabel(
            "<i>💡 Double-click to jump to playlist view | "
            "Right-click to open in Spotify</i>"
        )
        help_label.setStyleSheet("color: gray; font-size: 10px;")
        layout.addWidget(help_label)
        
        # Results table
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(7)
        self.results_table.setHorizontalHeaderLabels([
            "Type", "Source", "Track/Name", "Artist", "Album", "Duration", "Added"
        ])
        
        header = self.results_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        
        self.results_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.results_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.results_table.setSortingEnabled(True)
        self.results_table.setAlternatingRowColors(True)
        
        # CHANGED: Remove single-click handler, keep double-click for navigation
        # Single click does nothing now
        self.results_table.doubleClicked.connect(self._on_result_double_clicked)
        
        # Right-click for context menu (open in Spotify)
        self.results_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.results_table.customContextMenuRequested.connect(self._show_context_menu)
        
        layout.addWidget(self.results_table)
    
    def _on_search_text_changed(self, text: str):
        """Debounce search input."""
        self._search_timer.start(300)
    
    def _do_search(self):
        """Execute the search."""
        query = self.search_input.text().strip()
        if len(query) < 2:
            self.results_table.setRowCount(0)
            self.results_label.setText("")
            self._search_results = []
            return
        
        search_type = self.search_type.currentText()
        
        self.results_table.setRowCount(0)
        self._search_results = []
        
        # Search tracks
        if search_type in ("All", "Tracks Only", "Liked Songs Only"):
            search_in = 'all'
            if search_type == "Liked Songs Only":
                search_in = 'liked'
            elif search_type == "Tracks Only":
                search_in = 'playlists'
            
            track_results = self._search_tracks_with_ids(query, search_in)
            
            for playlist_id, playlist_name, track in track_results:
                self._add_track_result(playlist_id, playlist_name, track)
        
        # Search playlists
        if search_type in ("All", "Playlists Only"):
            playlist_results = self.data_manager.search_playlists(query)
            
            for playlist in playlist_results:
                self._add_playlist_result(playlist)
        
        self.results_label.setText(f"Found {self.results_table.rowCount()} results for '{query}'")
    
    def _search_tracks_with_ids(self, query: str, search_in: str) -> List[Tuple[str, str, Track]]:
        """Search tracks and return playlist_id along with results."""
        results = []
        query = query.lower()
        
        if search_in in ('all', 'playlists'):
            for playlist in self.data_manager.get_playlists():
                for track in playlist.tracks:
                    if self._track_matches(track, query):
                        results.append((playlist.playlist_id, playlist.name, track))
        
        if search_in in ('all', 'liked'):
            liked = self.data_manager.get_liked_songs()
            if liked:
                for track in liked.tracks:
                    if self._track_matches(track, query):
                        results.append(("liked", "Liked Songs", track))
        
        return results
    
    def _track_matches(self, track: Track, query: str) -> bool:
        """Check if a track matches the search query."""
        try:
            searchable = []
            
            if track.name:
                searchable.append(track.name.lower())
            
            try:
                if track.artists_string:
                    searchable.append(track.artists_string.lower())
            except:
                pass
            
            if track.album_name:
                searchable.append(track.album_name.lower())
            
            if track.genres:
                for genre in track.genres:
                    if genre:
                        searchable.append(genre.lower())
            
            return any(query in s for s in searchable if s)
        except:
            return False
    
    def _add_track_result(self, playlist_id: str, playlist_name: str, track: Track):
        """Add a track to the results table."""
        row = self.results_table.rowCount()
        self.results_table.insertRow(row)
        
        self.results_table.setItem(row, 0, QTableWidgetItem("🎵"))
        self.results_table.setItem(row, 1, QTableWidgetItem(playlist_name))
        
        name = track.name
        if track.explicit:
            name = f"🅴 {name}"
        self.results_table.setItem(row, 2, QTableWidgetItem(name))
        
        self.results_table.setItem(row, 3, QTableWidgetItem(track.artists_string))
        self.results_table.setItem(row, 4, QTableWidgetItem(track.album_name))
        self.results_table.setItem(row, 5, QTableWidgetItem(track.duration_formatted))
        
        added = track.added_at[:10] if track.added_at else ""
        self.results_table.setItem(row, 6, QTableWidgetItem(added))
        
        self._search_results.append(('track', playlist_id, playlist_name, track))
    
    def _add_playlist_result(self, playlist: Playlist):
        """Add a playlist to the results table."""
        row = self.results_table.rowCount()
        self.results_table.insertRow(row)
        
        self.results_table.setItem(row, 0, QTableWidgetItem("📋"))
        self.results_table.setItem(row, 1, QTableWidgetItem("—"))
        self.results_table.setItem(row, 2, QTableWidgetItem(playlist.name))
        self.results_table.setItem(row, 3, QTableWidgetItem(playlist.owner_name))
        self.results_table.setItem(row, 4, QTableWidgetItem(f"{playlist.track_count} tracks"))
        self.results_table.setItem(row, 5, QTableWidgetItem(playlist.total_duration_formatted))
        self.results_table.setItem(row, 6, QTableWidgetItem("—"))
        
        self._search_results.append(('playlist', playlist.playlist_id, None, playlist))
    
    def _on_result_double_clicked(self, index):
        """Handle double-click - navigate to playlist view."""
        row = index.row()
        if row >= len(self._search_results):
            return
        
        result_type, playlist_id, playlist_name, obj = self._search_results[row]
        
        if result_type == 'track':
            # Navigate to track in playlist
            self.track_selected.emit(playlist_id, obj.track_id, obj)
        else:
            # Navigate to playlist
            self.playlist_selected.emit(obj)
    
    def _show_context_menu(self, position):
        """Show right-click context menu."""
        row = self.results_table.rowAt(position.y())
        if row < 0 or row >= len(self._search_results):
            return
        
        result_type, playlist_id, playlist_name, obj = self._search_results[row]
        
        menu = QMenu(self)
        
        # Navigate action
        if result_type == 'track':
            navigate_action = QAction("📂 Go to Playlist", self)
            navigate_action.triggered.connect(
                lambda: self.track_selected.emit(playlist_id, obj.track_id, obj)
            )
            menu.addAction(navigate_action)
        else:
            navigate_action = QAction("📂 Show Playlist", self)
            navigate_action.triggered.connect(
                lambda: self.playlist_selected.emit(obj)
            )
            menu.addAction(navigate_action)
        
        menu.addSeparator()
        
        # Open in Spotify Desktop
        open_spotify_action = QAction("🖥️ Open in Spotify Desktop", self)
        open_spotify_action.triggered.connect(lambda: self._open_in_spotify(obj.uri))
        menu.addAction(open_spotify_action)
        
        # Open in Spotify Web
        web_url = self._uri_to_web_url(obj.uri)
        if web_url:
            open_web_action = QAction("🌐 Open in Spotify Web", self)
            open_web_action.triggered.connect(
                lambda: QDesktopServices.openUrl(QUrl(web_url))
            )
            menu.addAction(open_web_action)
        
        menu.addSeparator()
        
        # Copy actions
        if result_type == 'track':
            copy_name_action = QAction("📋 Copy \"Artist - Track\"", self)
            copy_name_action.triggered.connect(
                lambda: self._copy_to_clipboard(f"{obj.artists_string} - {obj.name}")
            )
            menu.addAction(copy_name_action)
        
        copy_link_action = QAction("📋 Copy Spotify Link", self)
        copy_link_action.triggered.connect(
            lambda: self._copy_to_clipboard(web_url or obj.uri or 'No link')
        )
        menu.addAction(copy_link_action)
        
        menu.exec(self.results_table.mapToGlobal(position))
    
    def _open_in_spotify(self, uri: str):
        """Open URI in Spotify desktop app."""
        if not uri:
            return
        
        system = platform.system()
        try:
            if system == "Windows":
                subprocess.run(['cmd', '/c', 'start', '', uri], shell=False)
            elif system == "Darwin":
                subprocess.run(['open', uri])
            else:
                subprocess.run(['xdg-open', uri])
        except:
            pass
    
    def _uri_to_web_url(self, uri: str) -> str:
        """Convert Spotify URI to web URL."""
        if not uri or not uri.startswith('spotify:'):
            return ""
        
        parts = uri.split(':')
        if len(parts) >= 3:
            return f"https://open.spotify.com/{parts[1]}/{parts[2]}"
        return ""
    
    def _copy_to_clipboard(self, text: str):
        """Copy text to clipboard."""
        from PyQt6.QtWidgets import QApplication
        QApplication.clipboard().setText(text)
    
    def clear(self):
        """Clear search results."""
        self.search_input.clear()
        self.results_table.setRowCount(0)
        self.results_label.setText("")
        self._search_results = []