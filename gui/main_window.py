"""
Main application window.
"""
from datetime import datetime
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QPushButton, QToolBar, QStatusBar, QMessageBox, QFileDialog,
    QApplication, QLabel, QCheckBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSettings
from PyQt6.QtGui import QAction, QIcon
from typing import Optional, Dict, Any
import json
import os

from config import APP_NAME, APP_VERSION, DEFAULT_BACKUP_DIR
from spotify_client import SpotifyClient
from data_manager import DataManager
from models.playlist import LikedSongs
from models import Playlist
from .playlist_view import PlaylistView
from .search_widget import SearchWidget
from .dialogs import (
    ProgressDialog, SettingsDialog, StatisticsDialog, UpdateResultDialog
)


class BackupWorker(QThread):
    """Worker thread for backup operations."""
    
    progress = pyqtSignal(str, int, int)
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)
    rate_limited = pyqtSignal(dict)  # New signal for rate limit
    
    def __init__(self, client: SpotifyClient, fetch_genres: bool = False, 
                 include_spotify_playlists: bool = True, include_collab_playlists: bool = True,
                 resume: bool = False):
        super().__init__()
        self.client = client
        self.fetch_genres = fetch_genres
        self.include_spotify_playlists = include_spotify_playlists
        self.include_collab_playlists = include_collab_playlists
        self.resume = resume
        self._cancelled = False
    
    def run(self):
        try:
            self.client.progress_callback = self._report_progress
            data = self.client.fetch_all_data(
                self.fetch_genres, 
                self.include_spotify_playlists,
                self.include_collab_playlists,
                self.resume
            )
            
            if self._cancelled:
                return
            
            # Check if rate limited
            if data.get('rate_limited'):
                self.rate_limited.emit(data)
            else:
                self.finished.emit(data)
        except Exception as e:
            import traceback
            self.error.emit(f"{str(e)}\n\n{traceback.format_exc()}")
    
    def _report_progress(self, message: str, current: int, total: int):
        if not self._cancelled:
            self.progress.emit(message, current, total)
    
    def cancel(self):
        self._cancelled = True




class SelectiveRefreshWorker(QThread):
    """Worker thread for selective playlist refresh operations."""

    progress = pyqtSignal(str, int, int)
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)
    rate_limited = pyqtSignal(dict)

    def __init__(self, client: SpotifyClient, playlist_ids: list,
                 fetch_genres: bool = False):
        super().__init__()
        self.client = client
        self.playlist_ids = playlist_ids
        self.fetch_genres = fetch_genres
        self._cancelled = False

    def run(self):
        try:
            self.client.progress_callback = self._report_progress
            data = self.client.refresh_selected_playlists(
                self.playlist_ids,
                self.fetch_genres
            )

            if self._cancelled:
                return

            # Check if rate limited
            if data.get('rate_limited'):
                self.rate_limited.emit(data)
            else:
                self.finished.emit(data)
        except Exception as e:
            import traceback
            self.error.emit(f"{str(e)}\n\n{traceback.format_exc()}")

    def _report_progress(self, message: str, current: int, total: int):
        if not self._cancelled:
            self.progress.emit(message, current, total)

    def cancel(self):
        self._cancelled = True


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self):
        super().__init__()
        
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        self.setMinimumSize(1200, 800)

        # # Just set the window icon (app icon already set in main)
        # icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets', 'icon.ico')
        # if os.path.exists(icon_path):
            # self.setWindowIcon(QIcon(icon_path))        

        # Apply theme/stylesheet
        self._apply_theme()
       
        self.settings = QSettings("SpotifyBackup", "SpotifyBackupTool")
        self._load_settings()
        
        self.spotify_client = SpotifyClient()
        self.data_manager = DataManager(self._settings.get('backup_dir', DEFAULT_BACKUP_DIR))
        
        self._setup_ui()
        self._setup_menubar()
        self._setup_toolbar()
        self._setup_statusbar()
        
        self._load_existing_data()

    def _apply_theme(self):
        """Apply custom theme/colors to the application."""
        # Spotify-inspired dark theme
        stylesheet = """
        QMainWindow, QWidget {
            background-color: #191414;
            color: #FFFFFF;
        }
        
        QTableWidget {
            background-color: #121212;
            alternate-background-color: #1a1a1a;
            color: #FFFFFF;
            gridline-color: #282828;
            selection-background-color: #1DB954;
            selection-color: #FFFFFF;
        }
        
        QTableWidget::item:hover {
            background-color: #282828;
        }
        
        QHeaderView::section {
            background-color: #282828;
            color: #B3B3B3;
            padding: 5px;
            border: none;
            border-bottom: 1px solid #404040;
        }
        
        QTreeWidget {
            background-color: #121212;
            color: #FFFFFF;
            border: none;
        }
        
        QTreeWidget::item:hover {
            background-color: #282828;
        }
        
        QTreeWidget::item:selected {
            background-color: #1DB954;
            color: #FFFFFF;
        }
        
        QPushButton {
            background-color: #1DB954;
            color: #FFFFFF;
            border: none;
            padding: 8px 16px;
            border-radius: 20px;
            font-weight: bold;
        }
        
        QPushButton:hover {
            background-color: #1ed760;
        }
        
        QPushButton:pressed {
            background-color: #169c46;
        }
        
        QPushButton:disabled {
            background-color: #535353;
            color: #B3B3B3;
        }
        
        QPushButton:checkable {
            background-color: #282828;
        }
        
        QPushButton:checkable:checked {
            background-color: #1DB954;
        }
        
        QLineEdit {
            background-color: #282828;
            color: #FFFFFF;
            border: none;
            padding: 8px;
            border-radius: 4px;
        }
        
        QLineEdit:focus {
            border: 1px solid #1DB954;
        }
        
        QComboBox {
            background-color: #282828;
            color: #FFFFFF;
            border: none;
            padding: 6px 12px;
            border-radius: 4px;
        }
        
        QComboBox::drop-down {
            border: none;
        }
        
        QComboBox QAbstractItemView {
            background-color: #282828;
            color: #FFFFFF;
            selection-background-color: #1DB954;
        }
        
        QTabWidget::pane {
            border: none;
            background-color: #191414;
        }
        
        QTabBar::tab {
            background-color: #282828;
            color: #B3B3B3;
            padding: 10px 20px;
            margin-right: 2px;
            border-top-left-radius: 4px;
            border-top-right-radius: 4px;
        }
        
        QTabBar::tab:selected {
            background-color: #1DB954;
            color: #FFFFFF;
        }
        
        QTabBar::tab:hover:!selected {
            background-color: #404040;
        }
        
        QToolBar {
            background-color: #282828;
            border: none;
            spacing: 10px;
            padding: 5px;
        }
        
        QStatusBar {
            background-color: #282828;
            color: #B3B3B3;
        }
        
        QMenuBar {
            background-color: #191414;
            color: #FFFFFF;
        }
        
        QMenuBar::item:selected {
            background-color: #282828;
        }
        
        QMenu {
            background-color: #282828;
            color: #FFFFFF;
            border: 1px solid #404040;
        }
        
        QMenu::item:selected {
            background-color: #1DB954;
        }
        
        QMessageBox {
            background-color: #191414;
            color: #FFFFFF;
        }
        
        QLabel {
            color: #FFFFFF;
        }
        
        QSplitter::handle {
            background-color: #282828;
        }
        
        QScrollBar:vertical {
            background-color: #191414;
            width: 12px;
            border: none;
        }
        
        QScrollBar::handle:vertical {
            background-color: #535353;
            border-radius: 6px;
            min-height: 20px;
        }
        
        QScrollBar::handle:vertical:hover {
            background-color: #B3B3B3;
        }
        
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            height: 0px;
        }
        
        QScrollBar:horizontal {
            background-color: #191414;
            height: 12px;
            border: none;
        }
        
        QScrollBar::handle:horizontal {
            background-color: #535353;
            border-radius: 6px;
            min-width: 20px;
        }
        
        QScrollBar::handle:horizontal:hover {
            background-color: #B3B3B3;
        }
        
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
            width: 0px;
        }
        """
        
        self.setStyleSheet(stylesheet)
    
    def _load_settings(self):
        """Load application settings."""
        self._settings = {
            'backup_dir': self.settings.value('backup_dir', DEFAULT_BACKUP_DIR),
            'fetch_genres': self.settings.value('fetch_genres', False, type=bool),
            'auto_backup': self.settings.value('auto_backup', False, type=bool),
            'include_spotify_playlists': self.settings.value('include_spotify_playlists', True, type=bool),
            'include_collab_playlists': self.settings.value('include_collab_playlists', True, type=bool),
        }
    
    def _save_settings(self):
        """Save application settings."""
        for key, value in self._settings.items():
            self.settings.setValue(key, value)
    

    def _setup_ui(self):
        """Setup the main UI."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        
        # Connection status
        self.connection_label = QLabel("Not connected to Spotify")
        self.connection_label.setStyleSheet("color: red; font-weight: bold;")
        layout.addWidget(self.connection_label)
        
        # Rate limit status (new)
        self.rate_limit_label = QLabel("")
        self.rate_limit_label.setStyleSheet("color: orange; font-weight: bold;")
        self.rate_limit_label.setVisible(False)
        layout.addWidget(self.rate_limit_label)
        
        # Tab widget
        self.tabs = QTabWidget()
        
        # Playlists tab
        self.playlist_view = PlaylistView(self.data_manager)
        self.playlist_view.folder_changed.connect(self._on_folder_changed)
        self.tabs.addTab(self.playlist_view, "Playlists")
        
        # Search tab
        self.search_widget = SearchWidget(self.data_manager)
        self.search_widget.track_selected.connect(self._on_search_track_selected)
        self.search_widget.playlist_selected.connect(self._on_search_playlist_selected)
        self.tabs.addTab(self.search_widget, "Search")
        
        layout.addWidget(self.tabs)
    
    def _setup_menubar(self):
        """Setup the menu bar."""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("File")
        
        connect_action = QAction("Connect to Spotify", self)
        connect_action.triggered.connect(self._connect_spotify)
        file_menu.addAction(connect_action)
        
        file_menu.addSeparator()
        
        backup_action = QAction("Full Backup", self)
        backup_action.setShortcut("Ctrl+B")
        backup_action.triggered.connect(self._do_full_backup)
        file_menu.addAction(backup_action)
        
        update_action = QAction("Incremental Update", self)
        update_action.setShortcut("Ctrl+U")
        update_action.triggered.connect(self._do_incremental_update)
        file_menu.addAction(update_action)

        refresh_selected_action = QAction("Refresh Selected Playlists", self)
        refresh_selected_action.setShortcut("Ctrl+R")
        refresh_selected_action.triggered.connect(self._do_selective_refresh)
        file_menu.addAction(refresh_selected_action)

        file_menu.addSeparator()
        
        export_csv_action = QAction("Export to CSV", self)
        export_csv_action.triggered.connect(self._export_to_csv)
        file_menu.addAction(export_csv_action)
        
        open_folder_action = QAction("Open Backup Folder", self)
        open_folder_action.triggered.connect(self._open_backup_folder)
        file_menu.addAction(open_folder_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("Exit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # View menu
        view_menu = menubar.addMenu("View")
        
        refresh_action = QAction("Refresh", self)
        refresh_action.setShortcut("F5")
        refresh_action.triggered.connect(self._refresh_view)
        view_menu.addAction(refresh_action)
        
        stats_action = QAction("Statistics", self)
        stats_action.triggered.connect(self._show_statistics)
        view_menu.addAction(stats_action)
        
        # Tools menu
        tools_menu = menubar.addMenu("Tools")
        
        settings_action = QAction("Settings", self)
        settings_action.triggered.connect(self._show_settings)
        tools_menu.addAction(settings_action)
        
        # Help menu
        help_menu = menubar.addMenu("Help")
        
        about_action = QAction("About", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)
    
    def _setup_toolbar(self):
        """Setup the toolbar."""
        toolbar = QToolBar()
        self.addToolBar(toolbar)
        
        connect_btn = QPushButton("Connect")
        connect_btn.clicked.connect(self._connect_spotify)
        toolbar.addWidget(connect_btn)
        
        toolbar.addSeparator()
        
        backup_btn = QPushButton("Full Backup")
        backup_btn.clicked.connect(self._do_full_backup)
        toolbar.addWidget(backup_btn)
        
        update_btn = QPushButton("Update")
        update_btn.clicked.connect(self._do_incremental_update)
        toolbar.addWidget(update_btn)

        refresh_selected_btn = QPushButton("Refresh Selected")
        refresh_selected_btn.clicked.connect(self._do_selective_refresh)
        toolbar.addWidget(refresh_selected_btn)

        toolbar.addSeparator()
        
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self._refresh_view)
        toolbar.addWidget(refresh_btn)
        
        toolbar.addWidget(QLabel("🎵 = Spotify, 📋 = Your public, 🔒 = Your private, 👥 = Collaborative, 📌 = Followed"))
    
    def _setup_statusbar(self):
        """Setup the status bar."""
        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)
        self.statusbar.showMessage("Ready")
    
    def _load_existing_data(self):
        """Load existing backup data."""
        data = self.data_manager.load_backup()
        if data:
            self.playlist_view.load_data()
            self.statusbar.showMessage(
                f"Loaded backup from {data.get('exported_at', 'unknown date')}"
            )
    
    def _connect_spotify(self):
        """Connect to Spotify."""
        self.statusbar.showMessage("Connecting to Spotify...")
        
        if self.spotify_client.authenticate():
            user = self.spotify_client.get_user_info()
            self.connection_label.setText(
                f"Connected as: {user.get('display_name', user.get('id'))}"
            )
            self.connection_label.setStyleSheet("color: green; font-weight: bold;")
            self.statusbar.showMessage("Connected to Spotify")
        else:
            QMessageBox.critical(
                self, "Connection Error",
                "Failed to connect to Spotify. Please check your credentials."
            )
            self.statusbar.showMessage("Connection failed")

    def _update_rate_limit_display(self):
        """Update the rate limit status display."""
        if self.spotify_client.is_rate_limited():
            info = self.spotify_client.get_rate_limit_status()
            self.rate_limit_label.setText(
                f"⚠️ Rate limited. Available at: {info['available_at']}"
            )
            self.rate_limit_label.setVisible(True)
        else:
            self.rate_limit_label.setVisible(False)
    
    def _do_full_backup(self):
        """Perform a full backup."""
        if not self.spotify_client.is_authenticated():
            QMessageBox.warning(
                self, "Not Connected",
                "Please connect to Spotify first."
            )
            return
        
        # Check for rate limiting
        if self.spotify_client.is_rate_limited():
            info = self.spotify_client.get_rate_limit_status()
            QMessageBox.warning(
                self, "Rate Limited",
                f"Currently rate limited by Spotify.\n\n"
                f"Available at: {info['available_at']}\n\n"
                f"Please try again later."
            )
            return
        
        # Check for resumable backup
        resume = False
        if self.spotify_client.can_resume_backup():
            resume_info = self.spotify_client.get_resume_info()
            reply = QMessageBox.question(
                self, "Resume Backup?",
                f"Found interrupted backup:\n"
                f"• {resume_info['playlists_completed']}/{resume_info['playlists_total']} playlists completed\n"
                f"• Liked songs: {'✓' if resume_info['liked_songs_completed'] else '✗'}\n\n"
                f"Would you like to resume?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel
            )
            if reply == QMessageBox.StandardButton.Cancel:
                return
            resume = (reply == QMessageBox.StandardButton.Yes)
        
        progress_dialog = ProgressDialog(self, "Full Backup" if not resume else "Resuming Backup")
        
        self._backup_worker = BackupWorker(
            self.spotify_client,
            self._settings.get('fetch_genres', False),
            include_spotify_playlists=True,
            include_collab_playlists=self._settings.get('include_collab_playlists', True),
            resume=resume
        )
        
        self._backup_worker.progress.connect(progress_dialog.update_progress)
        self._backup_worker.finished.connect(
            lambda data: self._on_backup_finished(data, progress_dialog)
        )
        self._backup_worker.error.connect(
            lambda err: self._on_backup_error(err, progress_dialog)
        )
        self._backup_worker.rate_limited.connect(
            lambda data: self._on_rate_limited(data, progress_dialog)
        )
        
        progress_dialog.rejected.connect(self._backup_worker.cancel)
        
        self._backup_worker.start()
        progress_dialog.exec()


    def _on_rate_limited(self, data: Dict[str, Any], dialog: ProgressDialog):
        """Handle rate limit during backup."""
        dialog.accept()
        
        info = data.get('rate_limit_info', {})
        
        self._update_rate_limit_display()
        
        message = "Backup was interrupted due to Spotify rate limiting.\n\n"
        
        if data.get('partial'):
            message += f"Progress saved:\n"
            message += f"• {data.get('playlists_completed', 0)}/{data.get('playlists_total', 0)} playlists\n\n"
        
        message += f"Available at: {info.get('available_at', 'Unknown')}\n\n"
        message += "You can resume the backup later by clicking 'Full Backup' again."
        
        QMessageBox.warning(self, "Rate Limited", message)
        
        self.statusbar.showMessage(f"Rate limited - available at {info.get('available_at', 'Unknown')}")

    
    def _get_liked_songs_count(self, liked_songs) -> int:
        """Safely get the count of liked songs."""
        if liked_songs is None:
            return 0
        if isinstance(liked_songs, LikedSongs):
            return len(liked_songs.tracks)
        if isinstance(liked_songs, dict):
            return len(liked_songs.get('tracks', []))
        return 0
    
    def _get_playlists_count(self, playlists) -> int:
        """Safely get the count of playlists."""
        if playlists is None:
            return 0
        return len(playlists)
    
    def _on_backup_finished(self, data: Dict[str, Any], dialog: ProgressDialog):
        """Handle backup completion."""
        dialog.accept()
        
        backup_path = self.data_manager.save_full_backup(data)
        self.playlist_view.load_data()
        
        playlists_count = self._get_playlists_count(data.get('playlists'))
        liked_songs_count = self._get_liked_songs_count(data.get('liked_songs'))
        
        # Count Spotify playlists
        spotify_count = 0
        for p in data.get('playlists', []):
            if isinstance(p, Playlist):
                if p.owner_id.lower() == 'spotify':
                    spotify_count += 1
            elif isinstance(p, dict):
                if p.get('owner_id', '').lower() == 'spotify':
                    spotify_count += 1
        
        QMessageBox.information(
            self, "Backup Complete",
            f"Backup saved to:\n{backup_path}\n\n"
            f"Total Playlists: {playlists_count}\n"
            f"  • Spotify Playlists: {spotify_count}\n"
            f"  • Other Playlists: {playlists_count - spotify_count}\n"
            f"Liked Songs: {liked_songs_count}"
        )
        
        self.statusbar.showMessage("Backup complete")
    
    def _on_backup_error(self, error: str, dialog: ProgressDialog):
        """Handle backup error."""
        dialog.reject()
        
        QMessageBox.critical(
            self, "Backup Error",
            f"An error occurred during backup:\n{error}"
        )
        
        self.statusbar.showMessage("Backup failed")
    
    def _do_incremental_update(self):
        """Perform an incremental update."""
        if not self.spotify_client.is_authenticated():
            QMessageBox.warning(
                self, "Not Connected",
                "Please connect to Spotify first."
            )
            return
        
        # Check for rate limiting
        if self.spotify_client.is_rate_limited():
            info = self.spotify_client.get_rate_limit_status()
            QMessageBox.warning(
                self, "Rate Limited",
                f"Currently rate limited by Spotify.\n\n"
                f"Available at: {info['available_at']}\n\n"
                f"Please try again later."
            )
            return
        
        existing_data = self.data_manager.load_backup()
        if not existing_data:
            reply = QMessageBox.question(
                self, "No Existing Backup",
                "No existing backup found. Would you like to do a full backup instead?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self._do_full_backup()
            return
        
        old_snapshots = {}
        for p in existing_data.get('playlists', []):
            if isinstance(p, dict):
                old_snapshots[p.get('playlist_id', '')] = p.get('snapshot_id', '')
            elif isinstance(p, Playlist):
                old_snapshots[p.playlist_id] = p.snapshot_id
        
        progress_dialog = ProgressDialog(self, "Incremental Update")
        
        self._backup_worker = BackupWorker(
            self.spotify_client,
            self._settings.get('fetch_genres', False),
            include_spotify_playlists=True,
            include_collab_playlists=self._settings.get('include_collab_playlists', True)
        )
        
        self._backup_worker.progress.connect(progress_dialog.update_progress)
        self._backup_worker.finished.connect(
            lambda data: self._on_update_finished(data, old_snapshots, progress_dialog)
        )
        self._backup_worker.error.connect(
            lambda err: self._on_backup_error(err, progress_dialog)
        )
        self._backup_worker.rate_limited.connect(
            lambda data: self._on_rate_limited(data, progress_dialog)
        )
        
        progress_dialog.rejected.connect(self._backup_worker.cancel)
        
        self._backup_worker.start()
        progress_dialog.exec()
    
    def _on_update_finished(
        self,
        data: Dict[str, Any],
        old_snapshots: Dict[str, str],
        dialog: ProgressDialog
    ):
        """Handle incremental update completion."""
        dialog.accept()
        
        stats = self.data_manager.update_incremental(
            data.get('playlists', []),
            data.get('liked_songs'),
            old_snapshots
        )
        
        self.playlist_view.load_data()
        
        result_dialog = UpdateResultDialog(self, stats)
        result_dialog.exec()
        
        self.statusbar.showMessage("Update complete")

    def _do_selective_refresh(self):
        """Refresh only selected playlists."""
        if not self.spotify_client.is_authenticated():
            QMessageBox.warning(
                self, "Not Connected",
                "Please connect to Spotify first."
            )
            return

        # Check for rate limiting
        if self.spotify_client.is_rate_limited():
            info = self.spotify_client.get_rate_limit_status()
            QMessageBox.warning(
                self, "Rate Limited",
                f"Currently rate limited by Spotify.\n\n"
                f"Available at: {info['available_at']}\n\n"
                f"Please try again later."
            )
            return

        # Get selected playlists
        selected_playlists = self.playlist_view.get_selected_playlists()

        if not selected_playlists:
            QMessageBox.information(
                self, "No Playlists Selected",
                "Please select one or more playlists to refresh by checking the boxes next to them."
            )
            return

        # Confirm refresh
        reply = QMessageBox.question(
            self, "Refresh Selected Playlists",
            f"Refresh {len(selected_playlists)} selected playlist(s)?\n\n"
            f"This will fetch fresh data from Spotify and update your local backup.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        progress_dialog = ProgressDialog(self, "Refreshing Selected Playlists")

        # Extract playlist IDs and metadata
        playlist_data = [
            {'id': p.playlist_id, 'name': p.name}
            for p in selected_playlists
        ]

        self._refresh_worker = SelectiveRefreshWorker(
            self.spotify_client,
            playlist_data,
            self._settings.get('fetch_genres', False)
        )

        self._refresh_worker.progress.connect(progress_dialog.update_progress)
        self._refresh_worker.finished.connect(
            lambda data: self._on_selective_refresh_finished(data, progress_dialog)
        )
        self._refresh_worker.error.connect(
            lambda err: self._on_backup_error(err, progress_dialog)
        )
        self._refresh_worker.rate_limited.connect(
            lambda data: self._on_rate_limited(data, progress_dialog)
        )

        progress_dialog.rejected.connect(self._refresh_worker.cancel)

        self._refresh_worker.start()
        progress_dialog.exec()

    def _on_selective_refresh_finished(self, data: Dict[str, Any], dialog: ProgressDialog):
        """Handle selective refresh completion."""
        dialog.accept()

        refreshed_playlists = data.get('playlists', [])

        # Update the backup with refreshed playlists
        update_stats = self.data_manager.update_selected_playlists(refreshed_playlists)

        # Reload the view
        self.playlist_view.load_data()

        QMessageBox.information(
            self, "Refresh Complete",
            f"Successfully refreshed {len(refreshed_playlists)} playlist(s).\n\n"
            f"Tracks updated: {update_stats.get('tracks_updated', 0)}\n"
            f"Tracks added: {update_stats.get('tracks_added', 0)}\n"
            f"Tracks removed: {update_stats.get('tracks_removed', 0)}"
        )

        self.statusbar.showMessage(f"Refreshed {len(refreshed_playlists)} playlist(s)")

    def _export_to_csv(self):
        """Export data to CSV."""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export to CSV",
            os.path.join(self._settings['backup_dir'], "spotify_export.csv"),
            "CSV Files (*.csv)"
        )
        
        if file_path:
            exported_path = self.data_manager.export_to_csv(file_path)
            if exported_path:
                QMessageBox.information(
                    self, "Export Complete",
                    f"Data exported to:\n{exported_path}"
                )
            else:
                QMessageBox.warning(
                    self, "Export Failed",
                    "No data to export. Please create a backup first."
                )
    
    def _open_backup_folder(self):
        """Open the backup folder in file explorer."""
        import subprocess
        import platform
        
        path = self._settings['backup_dir']
        
        if not os.path.exists(path):
            os.makedirs(path, exist_ok=True)
        
        try:
            if platform.system() == 'Windows':
                os.startfile(path)
            elif platform.system() == 'Darwin':
                subprocess.run(['open', path])
            else:
                subprocess.run(['xdg-open', path])
        except Exception as e:
            QMessageBox.warning(
                self, "Error",
                f"Could not open folder:\n{e}"
            )
    
    def _refresh_view(self):
        """Refresh the current view."""
        self.playlist_view.load_data()
        self.search_widget.clear()
        self.statusbar.showMessage("View refreshed")
    
    def _show_statistics(self):
        """Show backup statistics."""
        stats = self.data_manager.get_statistics()
        dialog = StatisticsDialog(self, stats)
        dialog.exec()
    
    def _show_settings(self):
        """Show settings dialog."""
        dialog = SettingsDialog(self, self._settings)
        
        if dialog.exec():
            new_settings = dialog.get_settings()
            self._settings.update(new_settings)
            self._save_settings()
            
            if new_settings['backup_dir'] != str(self.data_manager.backup_dir):
                self.data_manager = DataManager(new_settings['backup_dir'])
                self.playlist_view.data_manager = self.data_manager
                self.search_widget.data_manager = self.data_manager
                self._load_existing_data()
    
    def _show_about(self):
        """Show about dialog."""
        QMessageBox.about(
            self, f"About {APP_NAME}",
            f"<h3>{APP_NAME}</h3>"
            f"<p>Version {APP_VERSION}</p>"
            f"<p>A tool to backup your Spotify playlists and liked songs.</p>"
            f"<p><b>Includes:</b></p>"
            f"<ul>"
            f"<li>Your playlists</li>"
            f"<li>Playlists you follow</li>"
            f"<li>Spotify-created playlists (Discover Weekly, Daily Mix, etc.)</li>"
            f"<li>Liked songs</li>"
            f"</ul>"
        )
    
    def _on_folder_changed(self, playlist_id: str, new_folder: str):
        """Handle playlist folder change."""
        data = self.data_manager.load_backup()
        if data:
            for p in data.get('playlists', []):
                if isinstance(p, dict):
                    p_id = p.get('playlist_id', '')
                else:
                    p_id = p.playlist_id
                    
                if p_id == playlist_id:
                    if isinstance(p, dict):
                        p['folder_path'] = new_folder if new_folder else None
                    else:
                        p.folder_path = new_folder if new_folder else None
                    break
            
            self.data_manager._save_json(
                self.data_manager.main_backup_file,
                data
            )
    
    def _on_search_track_selected(self, playlist_id: str, track_id: str, track):
        """Handle track selection from search."""
        self.tabs.setCurrentIndex(0)
        self.playlist_view.navigate_to_playlist_track(playlist_id, track_id)
        self.statusbar.showMessage(f"Navigated to: {track.name}")
    
    def _on_search_playlist_selected(self, playlist):
        """Handle playlist selection from search."""
        self.tabs.setCurrentIndex(0)
        self.playlist_view._show_playlist(playlist)
        self.playlist_view._select_playlist_in_tree(playlist.playlist_id)
        self.statusbar.showMessage(f"Showing playlist: {playlist.name}")
    
    def closeEvent(self, event):
        """Handle window close."""
        self._save_settings()
        event.accept()