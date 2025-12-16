"""
Playlist view widget for displaying playlists and tracks.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QTreeWidget,
    QTreeWidgetItem, QTableWidget, QTableWidgetItem, QHeaderView,
    QLabel, QComboBox, QPushButton, QMenu, QAbstractItemView,
    QMessageBox, QApplication, QInputDialog, QLineEdit
)
from PyQt6.QtCore import Qt, pyqtSignal, QUrl
from PyQt6.QtGui import QAction, QDesktopServices
from typing import List, Optional, Dict, Set
import subprocess
import platform
import webbrowser

from models import Track, Playlist
from models.playlist import LikedSongs, PlaylistFolder
from data_manager import DataManager


class PlaylistView(QWidget):
    """Widget for viewing playlists and their tracks."""
    
    folder_changed = pyqtSignal(str, str)  # playlist_id, new_folder
    folders_updated = pyqtSignal()  # When folder structure changes
    
    def __init__(self, data_manager: DataManager, parent=None):
        super().__init__(parent)
        self.data_manager = data_manager
        self._playlists: List[Playlist] = []
        self._liked_songs: Optional[LikedSongs] = None
        self._current_playlist: Optional[Playlist] = None
        self._current_tracks: List[Track] = []
        self._custom_folders: Set[str] = set()  # Store empty custom folders
        
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left panel - Playlist tree
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        # Header with sort options
        header_layout = QHBoxLayout()
        header_layout.addWidget(QLabel("<b>Playlists</b>"))
        header_layout.addStretch()
        
        add_folder_btn = QPushButton("+📁")
        add_folder_btn.setToolTip("Create new folder")
        add_folder_btn.setMaximumWidth(40)
        add_folder_btn.clicked.connect(self._create_new_folder)
        header_layout.addWidget(add_folder_btn)
        
        left_layout.addLayout(header_layout)
        
        # Playlist sort options
        sort_layout = QHBoxLayout()
        sort_layout.addWidget(QLabel("Sort:"))
        
        self.playlist_sort_combo = QComboBox()
        self.playlist_sort_combo.addItems([
            "Default",
            "Name (A-Z)",
            "Name (Z-A)",
            "Track Count (High-Low)",
            "Track Count (Low-High)",
            "Owner",
            "My Playlists First",
            "Duration (Longest)",
            "Duration (Shortest)",
        ])
        self.playlist_sort_combo.currentIndexChanged.connect(self._on_playlist_sort_changed)
        self.playlist_sort_combo.setMaximumWidth(150)
        sort_layout.addWidget(self.playlist_sort_combo)
        sort_layout.addStretch()
        
        left_layout.addLayout(sort_layout)
        
        # Filter for showing/hiding Spotify playlists
        filter_layout = QHBoxLayout()
        self.show_spotify_cb = QPushButton("🎵 Spotify")
        self.show_spotify_cb.setCheckable(True)
        self.show_spotify_cb.setChecked(True)
        self.show_spotify_cb.setToolTip("Show/Hide Spotify-created playlists")
        self.show_spotify_cb.setMaximumWidth(80)
        self.show_spotify_cb.clicked.connect(self._build_playlist_tree)
        filter_layout.addWidget(self.show_spotify_cb)
        
        self.show_others_cb = QPushButton("👥 Others")
        self.show_others_cb.setCheckable(True)
        self.show_others_cb.setChecked(True)
        self.show_others_cb.setToolTip("Show/Hide playlists by other users")
        self.show_others_cb.setMaximumWidth(80)
        self.show_others_cb.clicked.connect(self._build_playlist_tree)
        filter_layout.addWidget(self.show_others_cb)
        
        filter_layout.addStretch()
        left_layout.addLayout(filter_layout)
        
        self.playlist_tree = QTreeWidget()
        self.playlist_tree.setHeaderHidden(True)
        self.playlist_tree.itemClicked.connect(self._on_playlist_selected)
        self.playlist_tree.itemDoubleClicked.connect(self._on_playlist_double_clicked)
        self.playlist_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.playlist_tree.customContextMenuRequested.connect(self._show_playlist_context_menu)
        self.playlist_tree.setDragEnabled(True)
        self.playlist_tree.setAcceptDrops(True)
        self.playlist_tree.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        
        left_layout.addWidget(self.playlist_tree)
        
        # Playlist count label
        self.playlist_count_label = QLabel("")
        self.playlist_count_label.setStyleSheet("color: gray; font-size: 10px;")
        left_layout.addWidget(self.playlist_count_label)
        
        splitter.addWidget(left_panel)
        
        # Right panel - Track list
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        info_layout = QHBoxLayout()
        self.playlist_info_label = QLabel("Select a playlist")
        info_layout.addWidget(self.playlist_info_label)
        info_layout.addStretch()
        
        info_layout.addWidget(QLabel("Sort:"))
        self.sort_combo = QComboBox()
        self.sort_combo.addItems([
            "Default Order",
            "Added Date (Newest)", "Added Date (Oldest)",
            "Track Name (A-Z)", "Track Name (Z-A)",
            "Artist (A-Z)", "Artist (Z-A)",
            "Album (A-Z)", "Duration", "Popularity"
        ])
        self.sort_combo.currentIndexChanged.connect(self._on_sort_changed)
        info_layout.addWidget(self.sort_combo)
        
        right_layout.addLayout(info_layout)
        
        self.tracks_table = QTableWidget()
        self.tracks_table.setColumnCount(7)
        self.tracks_table.setHorizontalHeaderLabels([
            "#", "Track", "Artist", "Album", "Duration", "Added", "Popularity"
        ])
        
        header = self.tracks_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        
        self.tracks_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tracks_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tracks_table.setAlternatingRowColors(True)
        
        self.tracks_table.doubleClicked.connect(self._on_track_double_clicked)
        self.tracks_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tracks_table.customContextMenuRequested.connect(self._show_track_context_menu)
        
        right_layout.addWidget(self.tracks_table)
        
        help_label = QLabel(
            "<i>💡 Double-click track to open in Spotify at that position | "
            "Right-click for more options</i>"
        )
        help_label.setStyleSheet("color: gray; font-size: 10px;")
        help_label.setWordWrap(True)
        right_layout.addWidget(help_label)
        
        splitter.addWidget(right_panel)
        splitter.setSizes([300, 700])
        
        layout.addWidget(splitter)
    
    def load_data(self):
        """Load playlists and liked songs from data manager."""
        self._playlists = self.data_manager.get_playlists()
        self._liked_songs = self.data_manager.get_liked_songs()
        self._load_custom_folders()
        self._build_playlist_tree()
    
    def _load_custom_folders(self):
        """Load custom folders from backup."""
        data = self.data_manager.load_backup()
        if data and 'custom_folders' in data:
            self._custom_folders = set(data['custom_folders'])
        else:
            self._custom_folders = set()
    
    def _save_custom_folders(self):
        """Save custom folders to backup."""
        data = self.data_manager.load_backup()
        if data:
            data['custom_folders'] = list(self._custom_folders)
            self.data_manager._save_json(self.data_manager.main_backup_file, data)
    
    def _get_sorted_playlists(self) -> List[Playlist]:
        """Get playlists sorted according to current sort mode."""
        playlists = list(self._playlists)
        
        data = self.data_manager.load_backup()
        user_id = data.get('user', {}).get('id', '') if data else ''
        
        sort_index = self.playlist_sort_combo.currentIndex()
        
        if sort_index == 0:  # Default
            pass
        elif sort_index == 1:  # Name A-Z
            playlists.sort(key=lambda p: p.name.lower())
        elif sort_index == 2:  # Name Z-A
            playlists.sort(key=lambda p: p.name.lower(), reverse=True)
        elif sort_index == 3:  # Track Count High-Low
            playlists.sort(key=lambda p: p.track_count, reverse=True)
        elif sort_index == 4:  # Track Count Low-High
            playlists.sort(key=lambda p: p.track_count)
        elif sort_index == 5:  # Owner
            playlists.sort(key=lambda p: p.owner_name.lower())
        elif sort_index == 6:  # My Playlists First
            playlists.sort(key=lambda p: (
                0 if p.owner_id == user_id else 1,
                p.name.lower()
            ))
        elif sort_index == 7:  # Duration Longest
            playlists.sort(key=lambda p: p.total_duration_ms, reverse=True)
        elif sort_index == 8:  # Duration Shortest
            playlists.sort(key=lambda p: p.total_duration_ms)
        
        return playlists
    
    def _on_playlist_sort_changed(self, index: int):
        """Handle playlist sort option change."""
        self._build_playlist_tree()
    
    def _build_playlist_tree(self):
        """Build the playlist tree view with folder structure."""
        self.playlist_tree.clear()
        
        # Add Liked Songs at top
        if self._liked_songs:
            liked_item = QTreeWidgetItem(["❤️ Liked Songs"])
            liked_item.setData(0, Qt.ItemDataRole.UserRole, ('liked', None))
            self.playlist_tree.addTopLevelItem(liked_item)
        
        # Get user ID
        data = self.data_manager.load_backup()
        user_id = data.get('user', {}).get('id', '') if data else ''
        
        # Filter and sort playlists
        show_spotify = self.show_spotify_cb.isChecked()
        show_others = self.show_others_cb.isChecked()
        
        sorted_playlists = self._get_sorted_playlists()
        filtered_playlists = []
        
        for playlist in sorted_playlists:
            owner_id = playlist.owner_id.lower()
            is_spotify = owner_id == 'spotify'
            is_mine = playlist.owner_id == user_id
            is_other = not is_spotify and not is_mine
            
            # Apply filters
            if is_spotify and not show_spotify:
                continue
            if is_other and not show_others:
                continue
            
            filtered_playlists.append(playlist)
        
        # Build tree with folders
        folders: Dict[str, QTreeWidgetItem] = {}
        no_folder_playlists = []
        
        # First, create all custom folders (including empty ones)
        for folder_path in sorted(self._custom_folders):
            parts = folder_path.split('/')
            current_parent = None
            current_path = ""
            
            for part in parts:
                current_path = f"{current_path}/{part}" if current_path else part
                
                if current_path not in folders:
                    folder_item = QTreeWidgetItem([f"📁 {part}"])
                    folder_item.setData(0, Qt.ItemDataRole.UserRole, ('folder', current_path))
                    
                    if current_parent:
                        current_parent.addChild(folder_item)
                    else:
                        self.playlist_tree.addTopLevelItem(folder_item)
                    
                    folders[current_path] = folder_item
                
                current_parent = folders[current_path]
        
        # Now add playlists
        for playlist in filtered_playlists:
            folder_path = playlist.folder_path
            
            if folder_path:
                # Create folder hierarchy if not exists
                parts = folder_path.split('/')
                current_parent = None
                current_path = ""
                
                for part in parts:
                    current_path = f"{current_path}/{part}" if current_path else part
                    
                    if current_path not in folders:
                        folder_item = QTreeWidgetItem([f"📁 {part}"])
                        folder_item.setData(0, Qt.ItemDataRole.UserRole, ('folder', current_path))
                        
                        if current_parent:
                            current_parent.addChild(folder_item)
                        else:
                            self.playlist_tree.addTopLevelItem(folder_item)
                        
                        folders[current_path] = folder_item
                    
                    current_parent = folders[current_path]
                
                playlist_item = self._create_playlist_item(playlist, user_id)
                current_parent.addChild(playlist_item)
            else:
                no_folder_playlists.append(playlist)
        
        for playlist in no_folder_playlists:
            item = self._create_playlist_item(playlist, user_id)
            self.playlist_tree.addTopLevelItem(item)
        
        self.playlist_tree.expandAll()
        
        # Update count label
        total = len(filtered_playlists)
        self.playlist_count_label.setText(f"{total} playlists shown")
    
    def _create_playlist_item(self, playlist: Playlist, user_id: str = "") -> QTreeWidgetItem:
        """Create a tree item for a playlist."""
        owner_id = playlist.owner_id.lower()
        is_spotify = owner_id == 'spotify'
        is_mine = playlist.owner_id == user_id
        
        if is_spotify:
            icon = "🎵"  # Spotify-created
        elif playlist.is_collaborative:
            icon = "👥"
        elif is_mine:
            icon = "📋" if playlist.is_public else "🔒"
        else:
            icon = "📌"  # Followed playlist
        
        item = QTreeWidgetItem([f"{icon} {playlist.name}"])
        item.setData(0, Qt.ItemDataRole.UserRole, ('playlist', playlist))
        
        owner_info = f"by {playlist.owner_name}"
        if is_spotify:
            owner_info = "by Spotify"
        elif is_mine:
            owner_info = "by You"
        
        item.setToolTip(
            0, 
            f"{playlist.name}\n"
            f"{playlist.track_count} tracks • {playlist.total_duration_formatted}\n"
            f"{owner_info}"
        )
        return item
    
    def _create_new_folder(self):
        """Create a new folder for organizing playlists."""
        folder_name, ok = QInputDialog.getText(
            self, "Create Folder", "Enter folder name:",
            QLineEdit.EchoMode.Normal
        )
        
        if ok and folder_name.strip():
            folder_path = folder_name.strip()
            self._custom_folders.add(folder_path)
            self._save_custom_folders()
            self._build_playlist_tree()
            
            # Show confirmation
            QMessageBox.information(
                self, "Folder Created",
                f"Folder '{folder_path}' created.\n\n"
                "Right-click on a playlist and select 'Move to Folder' to add playlists."
            )
    
    def _on_playlist_selected(self, item: QTreeWidgetItem, column: int):
        """Handle playlist selection."""
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return
        
        item_type, obj = data
        
        if item_type == 'liked':
            self._show_liked_songs()
        elif item_type == 'playlist':
            self._show_playlist(obj)
    
    def _on_playlist_double_clicked(self, item: QTreeWidgetItem, column: int):
        """Handle double-click on playlist to open in Spotify."""
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return
        
        item_type, obj = data
        
        if item_type == 'playlist' and obj:
            self._open_in_spotify_desktop(obj.uri)
    
    def _open_in_spotify_desktop(self, uri: str):
        """Open a Spotify URI in the desktop app."""
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
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not open Spotify: {e}")
            
    def _open_track_in_playlist_context(self, playlist: Playlist, track: Track, track_index: int):
        """
        Open Spotify with the playlist context at the specific track.
        Uses the web URL with play query parameter for better track highlighting.
        """
        if not playlist or not track:
            return
        
        if track.is_local:
            QMessageBox.information(
                self, "Local Track",
                "This is a local track and cannot be opened in Spotify."
            )
            return
        
        # Method 1: Try using the web URL with the specific track
        # Format: https://open.spotify.com/playlist/ID?si=xxx&highlight=spotify:track:ID
        playlist_id = playlist.playlist_id
        track_uri = track.uri
        
        # Build the web URL with highlight parameter
        web_url = f"https://open.spotify.com/playlist/{playlist_id}"
        if track_uri:
            # Add highlight parameter to scroll to track
            web_url = f"{web_url}?highlight={track_uri}"
        
        # Method 2: Alternative - try direct URI with offset
        # Unfortunately Spotify doesn't fully support offset in URI
        
        # Use webbrowser to open - this often triggers desktop app if installed
        try:
            webbrowser.open(web_url)
            
            # Show status message
            parent = self.parent()
            while parent:
                if hasattr(parent, 'statusbar'):
                    parent.statusbar.showMessage(
                        f"Opened playlist at track #{track_index + 1}: {track.name}"
                    )
                    break
                parent = parent.parent()
        except Exception as e:
            # Fallback: just open the playlist
            self._open_in_spotify_desktop(playlist.uri)
    
    def _uri_to_web_url(self, uri: str) -> Optional[str]:
        """Convert Spotify URI to web URL."""
        if not uri or not uri.startswith('spotify:'):
            return None
        
        parts = uri.split(':')
        if len(parts) >= 3:
            return f"https://open.spotify.com/{parts[1]}/{parts[2]}"
        return None
    
    def _show_playlist(self, playlist: Playlist):
        """Display tracks from a playlist."""
        self._current_playlist = playlist
        self.sort_combo.setCurrentIndex(0)
        
        owner_id = playlist.owner_id.lower()
        is_spotify = owner_id == 'spotify'
        owner_text = "Spotify" if is_spotify else playlist.owner_name
        
        self.playlist_info_label.setText(
            f"<b>{playlist.name}</b> • {playlist.track_count} tracks • "
            f"{playlist.total_duration_formatted} • by {owner_text}"
        )
        
        self._current_tracks = list(playlist.tracks)
        self._populate_tracks_table(self._current_tracks)
    
    def _show_liked_songs(self):
        """Display liked songs."""
        self._current_playlist = None
        self.sort_combo.setCurrentIndex(0)
        
        if not self._liked_songs:
            return
        
        self.playlist_info_label.setText(
            f"<b>Liked Songs</b> • {self._liked_songs.track_count} tracks"
        )
        
        self._current_tracks = list(self._liked_songs.tracks)
        self._populate_tracks_table(self._current_tracks)
    
    def _populate_tracks_table(self, tracks: List[Track]):
        """Populate the tracks table."""
        self.tracks_table.setRowCount(0)
        self.tracks_table.setSortingEnabled(False)
        
        for i, track in enumerate(tracks):
            row = self.tracks_table.rowCount()
            self.tracks_table.insertRow(row)
            
            num_item = QTableWidgetItem()
            num_item.setData(Qt.ItemDataRole.DisplayRole, i + 1)
            num_item.setData(Qt.ItemDataRole.UserRole, track)
            self.tracks_table.setItem(row, 0, num_item)
            
            name_text = track.name
            if track.explicit:
                name_text = f"🅴 {name_text}"
            if track.is_local:
                name_text = f"💾 {name_text}"
            self.tracks_table.setItem(row, 1, QTableWidgetItem(name_text))
            
            self.tracks_table.setItem(row, 2, QTableWidgetItem(track.artists_string))
            self.tracks_table.setItem(row, 3, QTableWidgetItem(track.album_name))
            self.tracks_table.setItem(row, 4, QTableWidgetItem(track.duration_formatted))
            
            added = track.added_at[:10] if track.added_at else ""
            self.tracks_table.setItem(row, 5, QTableWidgetItem(added))
            
            pop_item = QTableWidgetItem()
            pop_item.setData(Qt.ItemDataRole.DisplayRole, track.popularity)
            self.tracks_table.setItem(row, 6, pop_item)
        
        self.tracks_table.setSortingEnabled(True)
    
    def navigate_to_playlist_track(self, playlist_id: str, track_id: str):
        """Navigate to a specific track in a specific playlist."""
        target_playlist = None
        track_index = -1
        
        if playlist_id == "liked" and self._liked_songs:
            self._show_liked_songs()
            track_index = self._liked_songs.get_track_index(track_id)
        else:
            for playlist in self._playlists:
                if playlist.playlist_id == playlist_id:
                    target_playlist = playlist
                    break
            
            if target_playlist:
                self._show_playlist(target_playlist)
                track_index = target_playlist.get_track_index(track_id)
                self._select_playlist_in_tree(playlist_id)
        
        if track_index >= 0:
            self.tracks_table.selectRow(track_index)
            self.tracks_table.scrollTo(
                self.tracks_table.model().index(track_index, 0),
                QAbstractItemView.ScrollHint.PositionAtCenter
            )
    
    def _select_playlist_in_tree(self, playlist_id: str):
        """Select a playlist in the tree by its ID."""
        def find_and_select(item: QTreeWidgetItem) -> bool:
            data = item.data(0, Qt.ItemDataRole.UserRole)
            if data:
                item_type, obj = data
                if item_type == 'playlist' and obj and obj.playlist_id == playlist_id:
                    self.playlist_tree.setCurrentItem(item)
                    return True
            
            for i in range(item.childCount()):
                if find_and_select(item.child(i)):
                    return True
            return False
        
        for i in range(self.playlist_tree.topLevelItemCount()):
            if find_and_select(self.playlist_tree.topLevelItem(i)):
                break
                    
    # def _on_track_double_clicked(self, index):
        # """Handle double-click on track - open track in Spotify desktop."""
        # row = index.row()
        # track = self._get_track_at_row(row)
        
        # if not track:
            # return
        
        # if track.is_local:
            # QMessageBox.information(
                # self, "Local Track",
                # "This is a local track and cannot be opened in Spotify."
            # )
            # return
        
        # # Simply open the track URI - same as search widget does
        # if track.uri:
            # self._open_in_spotify_desktop(track.uri)

    def _on_track_double_clicked(self, index):
        """Handle double-click on track - open track in Spotify desktop."""
        row = index.row()
        track = self._get_track_at_row(row)
        
        if not track:
            return
        
        # DEBUG: Show what we have
        print(f"DEBUG Track URI: {track.uri}")
        print(f"DEBUG Track ID: {track.track_id}")
        print(f"DEBUG Track type: {type(track)}")
        
        QMessageBox.information(
            self, "Debug",
            f"URI: {track.uri}\nID: {track.track_id}"
        )
        
        if track.is_local:
            QMessageBox.information(
                self, "Local Track",
                "This is a local track and cannot be opened in Spotify."
            )
            return
        
        if track.uri:
            self._open_in_spotify_desktop(track.uri)
        
    def _get_track_at_row(self, row: int) -> Optional[Track]:
        """Get the Track object stored at the given row."""
        item = self.tracks_table.item(row, 0)
        if item:
            return item.data(Qt.ItemDataRole.UserRole)
        return None
    
    def _show_track_context_menu(self, position):
        """Show context menu for track."""
        row = self.tracks_table.rowAt(position.y())
        if row < 0:
            return
        
        track = self._get_track_at_row(row)
        if not track:
            return
        
        menu = QMenu(self)
        
        # Open at track in playlist
        if self._current_playlist:
            track_index = self._current_playlist.get_track_index(track.track_id)
            open_at_track_action = QAction("🎵 Open Playlist at This Track", self)
            open_at_track_action.triggered.connect(
                lambda: self._open_track_in_playlist_context(self._current_playlist, track, track_index)
            )
            menu.addAction(open_at_track_action)
            
            open_playlist_action = QAction("🎵 Open Playlist in Spotify", self)
            open_playlist_action.triggered.connect(
                lambda: self._open_in_spotify_desktop(self._current_playlist.uri)
            )
            menu.addAction(open_playlist_action)
        
        # Open track directly
        open_track_action = QAction("🎵 Open Track in Spotify", self)
        open_track_action.triggered.connect(
            lambda: self._open_in_spotify_desktop(track.uri)
        )
        menu.addAction(open_track_action)
        
        # Open in web
        web_url = track.external_urls.get('spotify') or self._uri_to_web_url(track.uri)
        if web_url:
            open_web_action = QAction("🌐 Open in Spotify Web", self)
            open_web_action.triggered.connect(
                lambda: QDesktopServices.openUrl(QUrl(web_url))
            )
            menu.addAction(open_web_action)
        
        menu.addSeparator()
        
        # Copy actions
        copy_link_action = QAction("📋 Copy Spotify Link", self)
        copy_link_action.triggered.connect(
            lambda: QApplication.clipboard().setText(web_url or track.uri or 'No link')
        )
        menu.addAction(copy_link_action)
        
        copy_name_action = QAction("📋 Copy \"Artist - Track\"", self)
        copy_name_action.triggered.connect(
            lambda: QApplication.clipboard().setText(f"{track.artists_string} - {track.name}")
        )
        menu.addAction(copy_name_action)
        
        menu.exec(self.tracks_table.mapToGlobal(position))
    
    def _on_sort_changed(self, index: int):
        """Handle track sort option change."""
        if not self._current_tracks:
            return
        
        if self._current_playlist:
            original_tracks = list(self._current_playlist.tracks)
        elif self._liked_songs:
            original_tracks = list(self._liked_songs.tracks)
        else:
            return
        
        if index == 0:
            tracks = original_tracks
        else:
            tracks = list(original_tracks)
            sort_options = [
                None,
                (lambda t: t.added_at or "", True),
                (lambda t: t.added_at or "", False),
                (lambda t: t.name.lower(), False),
                (lambda t: t.name.lower(), True),
                (lambda t: t.artists_string.lower(), False),
                (lambda t: t.artists_string.lower(), True),
                (lambda t: t.album_name.lower(), False),
                (lambda t: t.duration_ms, True),
                (lambda t: t.popularity, True),
            ]
            
            if index < len(sort_options) and sort_options[index]:
                key_func, reverse = sort_options[index]
                tracks.sort(key=key_func, reverse=reverse)
        
        self._current_tracks = tracks
        self._populate_tracks_table(tracks)
    
    def _show_playlist_context_menu(self, position):
        """Show context menu for playlist."""
        item = self.playlist_tree.itemAt(position)
        if not item:
            menu = QMenu(self)
            create_folder_action = QAction("📁 Create New Folder", self)
            create_folder_action.triggered.connect(self._create_new_folder)
            menu.addAction(create_folder_action)
            menu.exec(self.playlist_tree.mapToGlobal(position))
            return
        
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return
        
        item_type, obj = data
        
        menu = QMenu(self)
        
        if item_type == 'playlist' and obj:
            # Open in Spotify
            open_action = QAction("🎵 Open in Spotify", self)
            open_action.triggered.connect(lambda: self._open_in_spotify_desktop(obj.uri))
            menu.addAction(open_action)
            
            menu.addSeparator()
            
            # Copy link
            web_url = obj.external_urls.get('spotify') or self._uri_to_web_url(obj.uri)
            copy_link_action = QAction("📋 Copy Spotify Link", self)
            copy_link_action.triggered.connect(
                lambda: QApplication.clipboard().setText(web_url or obj.uri or 'No link')
            )
            menu.addAction(copy_link_action)
            
            menu.addSeparator()
            
            # Folder options
            folder_action = QAction("📁 Move to Folder...", self)
            folder_action.triggered.connect(lambda: self._set_playlist_folder(obj))
            menu.addAction(folder_action)
            
            if obj.folder_path:
                remove_folder_action = QAction("📁 Remove from Folder", self)
                remove_folder_action.triggered.connect(
                    lambda: self._remove_playlist_from_folder(obj)
                )
                menu.addAction(remove_folder_action)
            
            menu.addSeparator()
            
            # Info
            info_action = QAction("ℹ️ Playlist Info", self)
            info_action.triggered.connect(lambda: self._show_playlist_info(obj))
            menu.addAction(info_action)
        
        elif item_type == 'folder':
            # Create subfolder
            create_subfolder_action = QAction("📁 Create Subfolder", self)
            create_subfolder_action.triggered.connect(lambda: self._create_subfolder(obj))
            menu.addAction(create_subfolder_action)
            
            menu.addSeparator()
            
            rename_action = QAction("✏️ Rename Folder", self)
            rename_action.triggered.connect(lambda: self._rename_folder(obj, item))
            menu.addAction(rename_action)
            
            delete_action = QAction("🗑️ Delete Folder", self)
            delete_action.triggered.connect(lambda: self._delete_folder(obj))
            menu.addAction(delete_action)
        
        if menu.actions():
            menu.exec(self.playlist_tree.mapToGlobal(position))
    
    def _create_subfolder(self, parent_path: str):
        """Create a subfolder under an existing folder."""
        folder_name, ok = QInputDialog.getText(
            self, "Create Subfolder", "Enter subfolder name:",
            QLineEdit.EchoMode.Normal
        )
        
        if ok and folder_name.strip():
            new_path = f"{parent_path}/{folder_name.strip()}"
            self._custom_folders.add(new_path)
            self._save_custom_folders()
            self._build_playlist_tree()
    
    def _set_playlist_folder(self, playlist: Playlist):
        """Set or change folder for a playlist."""
        # Get existing folders
        existing_folders = list(self._custom_folders)
        
        # Also get folders from playlists
        for p in self._playlists:
            if p.folder_path:
                existing_folders.append(p.folder_path)
        
        existing_folders = sorted(set(existing_folders))
        
        # Show dialog with folder options
        items = ["(No Folder)"] + existing_folders + ["+ Create New Folder..."]
        
        current_index = 0
        if playlist.folder_path:
            try:
                current_index = existing_folders.index(playlist.folder_path) + 1
            except ValueError:
                pass
        
        folder, ok = QInputDialog.getItem(
            self, "Move to Folder",
            f"Select folder for '{playlist.name}':",
            items, current_index, False
        )
        
        if ok:
            if folder == "(No Folder)":
                new_folder = ""
            elif folder == "+ Create New Folder...":
                # Create new folder
                new_name, ok2 = QInputDialog.getText(
                    self, "Create Folder", "Enter folder name:",
                    QLineEdit.EchoMode.Normal
                )
                if ok2 and new_name.strip():
                    new_folder = new_name.strip()
                    self._custom_folders.add(new_folder)
                    self._save_custom_folders()
                else:
                    return
            else:
                new_folder = folder
            
            playlist.folder_path = new_folder if new_folder else None
            self.folder_changed.emit(playlist.playlist_id, new_folder)
            self._build_playlist_tree()
    
    def _remove_playlist_from_folder(self, playlist: Playlist):
        """Remove playlist from its current folder."""
        playlist.folder_path = None
        self.folder_changed.emit(playlist.playlist_id, "")
        self._build_playlist_tree()
    
    def _rename_folder(self, folder_path: str, item: QTreeWidgetItem):
        """Rename a folder."""
        current_name = folder_path.split('/')[-1] if '/' in folder_path else folder_path
        
        new_name, ok = QInputDialog.getText(
            self, "Rename Folder", "Enter new folder name:",
            QLineEdit.EchoMode.Normal, current_name
        )
        
        if ok and new_name.strip():
            old_path = folder_path
            if '/' in old_path:
                parent = '/'.join(old_path.split('/')[:-1])
                new_path = f"{parent}/{new_name.strip()}"
            else:
                new_path = new_name.strip()
            
            # Update custom folders
            if old_path in self._custom_folders:
                self._custom_folders.remove(old_path)
                self._custom_folders.add(new_path)
            
            # Update playlists in this folder
            for playlist in self._playlists:
                if playlist.folder_path and playlist.folder_path.startswith(old_path):
                    playlist.folder_path = playlist.folder_path.replace(old_path, new_path, 1)
                    self.folder_changed.emit(playlist.playlist_id, playlist.folder_path)
            
            self._save_custom_folders()
            self._build_playlist_tree()
    
    def _delete_folder(self, folder_path: str):
        """Delete a folder (moves playlists out of it)."""
        reply = QMessageBox.question(
            self, "Delete Folder",
            f"Delete folder '{folder_path}'?\n\nPlaylists will be moved out.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Remove from custom folders
            folders_to_remove = [f for f in self._custom_folders if f == folder_path or f.startswith(folder_path + '/')]
            for f in folders_to_remove:
                self._custom_folders.discard(f)
            
            # Update playlists
            for playlist in self._playlists:
                if playlist.folder_path and playlist.folder_path.startswith(folder_path):
                    playlist.folder_path = None
                    self.folder_changed.emit(playlist.playlist_id, "")
            
            self._save_custom_folders()
            self._build_playlist_tree()
    
    def _show_playlist_info(self, playlist: Playlist):
        """Show playlist info dialog."""
        owner_id = playlist.owner_id.lower()
        is_spotify = owner_id == 'spotify'
        
        data = self.data_manager.load_backup()
        user_id = data.get('user', {}).get('id', '') if data else ''
        is_mine = playlist.owner_id == user_id
        
        source = "Your playlist"
        if is_spotify:
            source = "Created by Spotify"
        elif not is_mine:
            source = f"Followed (by {playlist.owner_name})"
        
        info = f"""
        <h3>{playlist.name}</h3>
        <table cellpadding="5">
            <tr><td><b>Source:</b></td><td>{source}</td></tr>
            <tr><td><b>Owner:</b></td><td>{playlist.owner_name} ({playlist.owner_id})</td></tr>
            <tr><td><b>Tracks:</b></td><td>{playlist.track_count}</td></tr>
            <tr><td><b>Duration:</b></td><td>{playlist.total_duration_formatted}</td></tr>
            <tr><td><b>Public:</b></td><td>{'Yes' if playlist.is_public else 'No'}</td></tr>
            <tr><td><b>Collaborative:</b></td><td>{'Yes' if playlist.is_collaborative else 'No'}</td></tr>
            <tr><td><b>Folder:</b></td><td>{playlist.folder_path or 'None'}</td></tr>
        </table>
        <p><b>Description:</b><br>{playlist.description or 'No description'}</p>
        """
        QMessageBox.information(self, "Playlist Info", info)
    
    def refresh(self):
        """Refresh the view."""
        self.load_data()