"""
Dialog windows for the application.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QTextEdit, QCheckBox, QLineEdit, QFileDialog,
    QFormLayout, QMessageBox, QDialogButtonBox, QGroupBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from typing import Optional, Callable
import os

from config import DEFAULT_BACKUP_DIR


class ProgressDialog(QDialog):
    """Dialog showing progress of backup operations."""
    
    def __init__(self, parent=None, title: str = "Progress"):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(400)
        self.setModal(True)
        
        layout = QVBoxLayout(self)
        
        # Status label
        self.status_label = QLabel("Starting...")
        layout.addWidget(self.status_label)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        layout.addWidget(self.progress_bar)
        
        # Detail text
        self.detail_text = QTextEdit()
        self.detail_text.setReadOnly(True)
        self.detail_text.setMaximumHeight(150)
        layout.addWidget(self.detail_text)
        
        # Cancel button
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        layout.addWidget(self.cancel_button)
        
        self._cancelled = False
    
    def update_progress(self, message: str, current: int = 0, total: int = 0):
        """Update the progress display."""
        self.status_label.setText(message)
        self.detail_text.append(message)
        
        if total > 0:
            progress = int((current / total) * 100)
            self.progress_bar.setValue(progress)
        
        # Process events to update UI
        from PyQt6.QtWidgets import QApplication
        QApplication.processEvents()
    
    def is_cancelled(self) -> bool:
        return self._cancelled
    
    def reject(self):
        self._cancelled = True
        super().reject()


class SettingsDialog(QDialog):
    """Settings dialog."""
    
    def __init__(self, parent, settings: dict):
        super().__init__(parent)
        self.settings = settings
        self.setWindowTitle("Settings")
        self.setMinimumWidth(500)
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Backup location
        location_group = QGroupBox("Backup Location")
        location_layout = QHBoxLayout(location_group)
        
        self.backup_dir_edit = QLineEdit(self.settings.get('backup_dir', ''))
        location_layout.addWidget(self.backup_dir_edit)
        
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._browse_backup_dir)
        location_layout.addWidget(browse_btn)
        
        layout.addWidget(location_group)
        
        # Options
        options_group = QGroupBox("Backup Options")
        options_layout = QVBoxLayout(options_group)
        
        self.fetch_genres_cb = QCheckBox("Fetch genre information (slower)")
        self.fetch_genres_cb.setChecked(self.settings.get('fetch_genres', False))
        options_layout.addWidget(self.fetch_genres_cb)
        
        self.auto_backup_cb = QCheckBox("Enable automatic backup")
        self.auto_backup_cb.setChecked(self.settings.get('auto_backup', False))
        options_layout.addWidget(self.auto_backup_cb)
        
        self.include_collab_cb = QCheckBox("Include collaborative playlists in backup")
        self.include_collab_cb.setChecked(self.settings.get('include_collab_playlists', True))
        options_layout.addWidget(self.include_collab_cb)
        
        layout.addWidget(options_group)
        
        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def _browse_backup_dir(self):
        dir_path = QFileDialog.getExistingDirectory(
            self, "Select Backup Directory",
            self.backup_dir_edit.text()
        )
        if dir_path:
            self.backup_dir_edit.setText(dir_path)
    
    def get_settings(self) -> dict:
        return {
            'backup_dir': self.backup_dir_edit.text(),
            'fetch_genres': self.fetch_genres_cb.isChecked(),
            'auto_backup': self.auto_backup_cb.isChecked(),
            'include_collab_playlists': self.include_collab_cb.isChecked(),
        }


class StatisticsDialog(QDialog):
    """Dialog showing backup statistics."""
    
    def __init__(self, parent=None, stats: dict = None):
        super().__init__(parent)
        self.setWindowTitle("Backup Statistics")
        self.setMinimumWidth(400)
        
        layout = QVBoxLayout(self)
        
        if not stats:
            layout.addWidget(QLabel("No backup data available."))
        else:
            # Create stats display
            stats_text = f"""
            <h3>Backup Statistics</h3>
            <table>
                <tr><td><b>Playlists:</b></td><td>{stats.get('playlist_count', 0)}</td></tr>
                <tr><td><b>Liked Songs:</b></td><td>{stats.get('liked_songs_count', 0)}</td></tr>
                <tr><td><b>Unique Tracks:</b></td><td>{stats.get('unique_tracks', 0)}</td></tr>
                <tr><td><b>Unique Artists:</b></td><td>{stats.get('unique_artists', 0)}</td></tr>
                <tr><td><b>Unique Albums:</b></td><td>{stats.get('unique_albums', 0)}</td></tr>
                <tr><td><b>Genres Found:</b></td><td>{stats.get('genres_found', 0)}</td></tr>
                <tr><td><b>Total Duration:</b></td><td>{stats.get('total_duration_hours', 0)} hours</td></tr>
                <tr><td><b>Last Backup:</b></td><td>{stats.get('last_backup', 'Never')}</td></tr>
            </table>
            """
            label = QLabel(stats_text)
            label.setTextFormat(Qt.TextFormat.RichText)
            layout.addWidget(label)
        
        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)


class UpdateResultDialog(QDialog):
    """Dialog showing incremental update results."""
    
    def __init__(self, parent=None, stats: dict = None):
        super().__init__(parent)
        self.setWindowTitle("Update Complete")
        self.setMinimumWidth(350)
        
        layout = QVBoxLayout(self)
        
        if not stats:
            layout.addWidget(QLabel("Update completed."))
        else:
            text = f"""
            <h3>Incremental Update Results</h3>
            <table>
                <tr><td><b>Playlists Added:</b></td><td>{stats.get('playlists_added', 0)}</td></tr>
                <tr><td><b>Playlists Updated:</b></td><td>{stats.get('playlists_updated', 0)}</td></tr>
                <tr><td><b>Playlists Removed:</b></td><td>{stats.get('playlists_removed', 0)}</td></tr>
                <tr><td><b>Tracks Added:</b></td><td>{stats.get('tracks_added', 0)}</td></tr>
                <tr><td><b>Tracks Removed:</b></td><td>{stats.get('tracks_removed', 0)}</td></tr>
            </table>
            """
            label = QLabel(text)
            label.setTextFormat(Qt.TextFormat.RichText)
            layout.addWidget(label)
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)


class FolderDialog(QDialog):
    """Dialog for organizing playlists into folders."""
    
    def __init__(self, parent=None, playlist_name: str = "", current_folder: str = ""):
        super().__init__(parent)
        self.setWindowTitle("Set Playlist Folder")
        self.setMinimumWidth(400)
        
        layout = QVBoxLayout(self)
        
        layout.addWidget(QLabel(f"Playlist: <b>{playlist_name}</b>"))
        
        form = QFormLayout()
        
        self.folder_edit = QLineEdit(current_folder)
        self.folder_edit.setPlaceholderText("e.g., Music/Rock/Classic")
        form.addRow("Folder Path:", self.folder_edit)
        
        layout.addLayout(form)
        
        layout.addWidget(QLabel(
            "<i>Use '/' to create nested folders.<br>"
            "Leave empty to remove from folder.</i>"
        ))
        
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    
    def get_folder_path(self) -> str:
        return self.folder_edit.text().strip()