#!/usr/bin/env python3
"""
Immerse Yourself Environment Launcher
A PyQt5 GUI for managing ambient environment configs with Spotify and smart lights.
"""

import sys
import asyncio
import threading
import random
import subprocess
from pathlib import Path
from typing import List, Dict, Optional, Any, Set
from collections import defaultdict

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QGridLayout, QPushButton,
    QStatusBar, QMessageBox, QVBoxLayout, QTabWidget, QHBoxLayout,
    QShortcut, QLabel, QFrame, QSizePolicy, QStyleFactory, QMenuBar,
    QMenu, QAction, QDialog, QListWidget, QListWidgetItem, QStackedWidget,
    QRadioButton, QButtonGroup, QGroupBox, QSplitter, QLineEdit,
    QAbstractItemView
)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal, QSize
from PyQt5.QtGui import QKeySequence, QPalette, QColor, QPainter, QPen, QFont, QIcon

from config_loader import ConfigLoader
from status_bar import ImmersiveStatusBar
from freesound_manager import FreesoundManager, is_freesound_url
import configparser


class SettingsManager:
    """Manages application settings via settings.ini file."""

    DEFAULT_SETTINGS = {
        "appearance": {
            "theme": "light"  # Options: "light", "dark", "system"
        },
        "spotify": {
            "auto_start": "ask",  # Options: "always", "never", "ask"
            "startup_playlist": ""  # Playlist URI to play on startup (empty = none)
        }
    }

    def __init__(self, settings_file: str = "settings.ini"):
        self.settings_file = Path(settings_file)
        self.config = configparser.ConfigParser()
        self._load_or_create()

    def _load_or_create(self) -> None:
        """Load settings from file or create with defaults."""
        if self.settings_file.exists():
            self.config.read(self.settings_file)
        else:
            # Create default settings
            for section, values in self.DEFAULT_SETTINGS.items():
                self.config[section] = values
            self._save()

    def _save(self) -> None:
        """Save settings to file."""
        with open(self.settings_file, "w") as f:
            self.config.write(f)

    def get(self, section: str, key: str, fallback: str = "") -> str:
        """Get a setting value."""
        return self.config.get(section, key, fallback=fallback)

    def set(self, section: str, key: str, value: str) -> None:
        """Set a setting value and save."""
        if section not in self.config:
            self.config[section] = {}
        self.config[section][key] = value
        self._save()

    def get_theme(self) -> str:
        """Get the current theme setting."""
        return self.get("appearance", "theme", "light")

    def set_theme(self, theme: str) -> None:
        """Set the theme setting."""
        self.set("appearance", "theme", theme)

    def get_spotify_auto_start(self) -> str:
        """Get Spotify auto-start setting: 'always', 'never', or 'ask'."""
        return self.get("spotify", "auto_start", "ask")

    def set_spotify_auto_start(self, value: str) -> None:
        """Set Spotify auto-start setting."""
        self.set("spotify", "auto_start", value)

    def get_startup_playlist(self) -> str:
        """Get the startup playlist URI."""
        return self.get("spotify", "startup_playlist", "")

    def set_startup_playlist(self, uri: str) -> None:
        """Set the startup playlist URI."""
        self.set("spotify", "startup_playlist", uri)


class SpotifyConfigManager:
    """Manages Spotify configuration in .spotify.ini file."""

    CONFIG_FILE = ".spotify.ini"

    def __init__(self):
        self.config_path = Path(self.CONFIG_FILE)
        self.config = configparser.ConfigParser()
        self._load()

    def _load(self) -> None:
        """Load config from file if it exists."""
        if self.config_path.exists():
            self.config.read(self.config_path)

    def exists(self) -> bool:
        """Check if config file exists."""
        return self.config_path.exists()

    def is_configured(self) -> bool:
        """Check if Spotify is properly configured."""
        if not self.exists():
            return False
        try:
            return bool(self.get("client_id") and self.get("client_secret"))
        except:
            return False

    def get(self, key: str, fallback: str = "") -> str:
        """Get a config value."""
        return self.config.get("DEFAULT", key, fallback=fallback)

    def save(self, username: str, client_id: str, client_secret: str, redirect_uri: str) -> None:
        """Save Spotify configuration."""
        self.config["DEFAULT"] = {
            "username": username,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirectURI": redirect_uri
        }
        with open(self.config_path, "w") as f:
            self.config.write(f)


class WizBulbConfigManager:
    """Manages WIZ bulb configuration in .wizbulb.ini file."""

    CONFIG_FILE = ".wizbulb.ini"

    def __init__(self):
        self.config_path = Path(self.CONFIG_FILE)
        self.config = configparser.ConfigParser()
        self._load()

    def _load(self) -> None:
        """Load config from file if it exists."""
        if self.config_path.exists():
            self.config.read(self.config_path)

    def exists(self) -> bool:
        """Check if config file exists."""
        return self.config_path.exists()

    def is_configured(self) -> bool:
        """Check if any bulbs are configured."""
        if not self.exists():
            return False
        try:
            return bool(
                self.get("backdrop_bulbs") or
                self.get("overhead_bulbs") or
                self.get("battlefield_bulbs")
            )
        except:
            return False

    def get(self, key: str, fallback: str = "") -> str:
        """Get a config value."""
        return self.config.get("DEFAULT", key, fallback=fallback)

    def save(self, backdrop: str, overhead: str, battlefield: str) -> None:
        """Save WIZ bulb configuration."""
        self.config["DEFAULT"] = {
            "backdrop_bulbs": backdrop,
            "overhead_bulbs": overhead,
            "battlefield_bulbs": battlefield
        }
        with open(self.config_path, "w") as f:
            self.config.write(f)


class SettingsDialog(QDialog):
    """Settings dialog with icon navigation and panels."""

    def __init__(self, settings_manager: SettingsManager, parent=None):
        super().__init__(parent)
        self.settings_manager = settings_manager
        self.spotify_config = SpotifyConfigManager()
        self.wizbulb_config = WizBulbConfigManager()
        self.setWindowTitle("Settings")
        self.setMinimumSize(600, 450)
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the dialog UI."""
        layout = QHBoxLayout()

        # Left navigation list
        self.nav_list = QListWidget()
        self.nav_list.setMaximumWidth(150)
        self.nav_list.setIconSize(QSize(24, 24))

        # Add navigation items with status indicators
        appearance_item = QListWidgetItem("🎨 Appearance")
        self.nav_list.addItem(appearance_item)

        spotify_status = "✓" if self.spotify_config.is_configured() else "!"
        spotify_item = QListWidgetItem(f"🎵 Spotify [{spotify_status}]")
        self.nav_list.addItem(spotify_item)

        bulb_status = "✓" if self.wizbulb_config.is_configured() else "!"
        bulb_item = QListWidgetItem(f"💡 WIZ Bulbs [{bulb_status}]")
        self.nav_list.addItem(bulb_item)

        self.nav_list.currentRowChanged.connect(self._on_nav_changed)

        # Right panel stack
        self.panel_stack = QStackedWidget()

        # Add panels
        self.panel_stack.addWidget(self._create_appearance_panel())
        self.panel_stack.addWidget(self._create_spotify_panel())
        self.panel_stack.addWidget(self._create_wizbulb_panel())

        layout.addWidget(self.nav_list)
        layout.addWidget(self.panel_stack, 1)

        self.setLayout(layout)

        # Select first item
        self.nav_list.setCurrentRow(0)

    def _create_appearance_panel(self) -> QWidget:
        """Create the appearance settings panel."""
        panel = QWidget()
        layout = QVBoxLayout()

        # Theme group
        theme_group = QGroupBox("Theme")
        theme_layout = QVBoxLayout()

        self.theme_button_group = QButtonGroup()

        self.light_radio = QRadioButton("Light mode")
        self.dark_radio = QRadioButton("Dark mode")
        self.system_radio = QRadioButton("Use OS setting")

        self.theme_button_group.addButton(self.light_radio, 0)
        self.theme_button_group.addButton(self.dark_radio, 1)
        self.theme_button_group.addButton(self.system_radio, 2)

        theme_layout.addWidget(self.light_radio)
        theme_layout.addWidget(self.dark_radio)
        theme_layout.addWidget(self.system_radio)
        theme_group.setLayout(theme_layout)

        # Set current theme
        current_theme = self.settings_manager.get_theme()
        if current_theme == "light":
            self.light_radio.setChecked(True)
        elif current_theme == "dark":
            self.dark_radio.setChecked(True)
        else:
            self.system_radio.setChecked(True)

        # Connect signal
        self.theme_button_group.buttonClicked.connect(self._on_theme_changed)

        layout.addWidget(theme_group)
        layout.addStretch()

        panel.setLayout(layout)
        return panel

    def _create_spotify_panel(self) -> QWidget:
        """Create the Spotify settings panel."""
        from PyQt5.QtWidgets import QScrollArea, QTextBrowser

        panel = QWidget()
        layout = QVBoxLayout()

        # Status indicator
        if self.spotify_config.is_configured():
            status_label = QLabel("✓ Spotify is configured")
            status_label.setStyleSheet("color: green; font-weight: bold;")
        else:
            status_label = QLabel("! Spotify is not configured - music playback disabled")
            status_label.setStyleSheet("color: orange; font-weight: bold;")
        layout.addWidget(status_label)

        # Credentials group
        creds_group = QGroupBox("Spotify API Credentials")
        creds_layout = QVBoxLayout()

        # Username
        username_layout = QHBoxLayout()
        username_layout.addWidget(QLabel("Username:"))
        self.spotify_username = QLineEdit()
        self.spotify_username.setText(self.spotify_config.get("username"))
        self.spotify_username.setPlaceholderText("Your Spotify username")
        username_layout.addWidget(self.spotify_username)
        creds_layout.addLayout(username_layout)

        # Client ID
        client_id_layout = QHBoxLayout()
        client_id_layout.addWidget(QLabel("Client ID:"))
        self.spotify_client_id = QLineEdit()
        self.spotify_client_id.setText(self.spotify_config.get("client_id"))
        self.spotify_client_id.setPlaceholderText("From Spotify Developer Dashboard")
        client_id_layout.addWidget(self.spotify_client_id)
        creds_layout.addLayout(client_id_layout)

        # Client Secret
        secret_layout = QHBoxLayout()
        secret_layout.addWidget(QLabel("Client Secret:"))
        self.spotify_client_secret = QLineEdit()
        self.spotify_client_secret.setText(self.spotify_config.get("client_secret"))
        self.spotify_client_secret.setPlaceholderText("From Spotify Developer Dashboard")
        self.spotify_client_secret.setEchoMode(QLineEdit.Password)
        secret_layout.addWidget(self.spotify_client_secret)
        creds_layout.addLayout(secret_layout)

        # Redirect URI
        redirect_layout = QHBoxLayout()
        redirect_layout.addWidget(QLabel("Redirect URI:"))
        self.spotify_redirect = QLineEdit()
        self.spotify_redirect.setText(self.spotify_config.get("redirectURI", "http://127.0.0.1:8888/callback"))
        self.spotify_redirect.setPlaceholderText("http://127.0.0.1:8888/callback")
        redirect_layout.addWidget(self.spotify_redirect)
        creds_layout.addLayout(redirect_layout)

        creds_group.setLayout(creds_layout)
        layout.addWidget(creds_group)

        # Auto-start behavior group
        autostart_group = QGroupBox("When Spotify is not playing on this PC")
        autostart_layout = QVBoxLayout()

        self.autostart_button_group = QButtonGroup()

        self.autostart_ask = QRadioButton("Ask me what to do")
        self.autostart_start_local = QRadioButton("Start Spotify on this PC")
        self.autostart_use_remote = QRadioButton("Connect to Spotify on another device")
        self.autostart_disabled = QRadioButton("Run without music")

        self.autostart_button_group.addButton(self.autostart_ask, 0)
        self.autostart_button_group.addButton(self.autostart_start_local, 1)
        self.autostart_button_group.addButton(self.autostart_use_remote, 2)
        self.autostart_button_group.addButton(self.autostart_disabled, 3)

        autostart_layout.addWidget(self.autostart_ask)
        autostart_layout.addWidget(self.autostart_start_local)
        autostart_layout.addWidget(self.autostart_use_remote)
        autostart_layout.addWidget(self.autostart_disabled)

        # Set current value
        current_autostart = self.settings_manager.get_spotify_auto_start()
        if current_autostart == "start_local":
            self.autostart_start_local.setChecked(True)
        elif current_autostart == "use_remote":
            self.autostart_use_remote.setChecked(True)
        elif current_autostart == "disabled":
            self.autostart_disabled.setChecked(True)
        else:
            self.autostart_ask.setChecked(True)

        autostart_group.setLayout(autostart_layout)
        layout.addWidget(autostart_group)

        # Save button
        save_btn = QPushButton("Save Spotify Settings")
        save_btn.clicked.connect(self._save_spotify_settings)
        layout.addWidget(save_btn)

        # Help section
        help_group = QGroupBox("How to Get Spotify API Credentials")
        help_layout = QVBoxLayout()

        help_text = QTextBrowser()
        help_text.setOpenExternalLinks(True)
        help_text.setHtml("""
        <p><b>To enable Spotify playback, you need a Spotify Developer account:</b></p>
        <ol>
            <li>Go to <a href="https://developer.spotify.com/dashboard">developer.spotify.com/dashboard</a></li>
            <li>Log in with your Spotify account (Premium required for playback)</li>
            <li>Click "Create App"</li>
            <li>Fill in app name and description (anything works)</li>
            <li>Copy the <b>Client ID</b> and <b>Client Secret</b> into the fields above</li>
            <li>In your app settings, add the Redirect URI: <code>http://127.0.0.1:8888/callback</code></li>
            <li>Save settings here, then restart the app</li>
        </ol>
        <p><b>First-time authentication:</b> When you first click an environment with music,
        a browser will open for you to authorize the app. This creates a token cache file.</p>
        <p><i>No Spotify account?</i> That's okay! The app still works for lights and sound effects.</p>
        """)
        help_text.setMaximumHeight(200)
        help_layout.addWidget(help_text)
        help_group.setLayout(help_layout)
        layout.addWidget(help_group)

        layout.addStretch()
        panel.setLayout(layout)
        return panel

    def _create_wizbulb_panel(self) -> QWidget:
        """Create the WIZ bulb settings panel."""
        from PyQt5.QtWidgets import QTextBrowser, QTextEdit

        panel = QWidget()
        layout = QVBoxLayout()

        # Status indicator
        if self.wizbulb_config.is_configured():
            status_label = QLabel("✓ WIZ bulbs are configured")
            status_label.setStyleSheet("color: green; font-weight: bold;")
        else:
            status_label = QLabel("! No WIZ bulbs configured - lighting effects disabled")
            status_label.setStyleSheet("color: orange; font-weight: bold;")
        layout.addWidget(status_label)

        # Bulb groups
        bulbs_group = QGroupBox("Bulb IP Addresses (space-separated)")
        bulbs_layout = QVBoxLayout()

        # Backdrop bulbs
        backdrop_layout = QVBoxLayout()
        backdrop_layout.addWidget(QLabel("Backdrop Bulbs (ambient/background lighting):"))
        self.backdrop_bulbs = QLineEdit()
        self.backdrop_bulbs.setText(self.wizbulb_config.get("backdrop_bulbs"))
        self.backdrop_bulbs.setPlaceholderText("192.168.1.100 192.168.1.101 192.168.1.102")
        backdrop_layout.addWidget(self.backdrop_bulbs)
        bulbs_layout.addLayout(backdrop_layout)

        # Overhead bulbs
        overhead_layout = QVBoxLayout()
        overhead_layout.addWidget(QLabel("Overhead Bulbs (main room lighting):"))
        self.overhead_bulbs = QLineEdit()
        self.overhead_bulbs.setText(self.wizbulb_config.get("overhead_bulbs"))
        self.overhead_bulbs.setPlaceholderText("192.168.1.103 192.168.1.104")
        overhead_layout.addWidget(self.overhead_bulbs)
        bulbs_layout.addLayout(overhead_layout)

        # Battlefield bulbs
        battlefield_layout = QVBoxLayout()
        battlefield_layout.addWidget(QLabel("Battlefield Bulbs (dramatic/combat lighting):"))
        self.battlefield_bulbs = QLineEdit()
        self.battlefield_bulbs.setText(self.wizbulb_config.get("battlefield_bulbs"))
        self.battlefield_bulbs.setPlaceholderText("192.168.1.105")
        battlefield_layout.addWidget(self.battlefield_bulbs)
        bulbs_layout.addLayout(battlefield_layout)

        bulbs_group.setLayout(bulbs_layout)
        layout.addWidget(bulbs_group)

        # Discover button and save
        button_layout = QHBoxLayout()

        discover_btn = QPushButton("Discover Bulbs on Network")
        discover_btn.clicked.connect(self._discover_bulbs)
        button_layout.addWidget(discover_btn)

        save_btn = QPushButton("Save Bulb Settings")
        save_btn.clicked.connect(self._save_wizbulb_settings)
        button_layout.addWidget(save_btn)

        layout.addLayout(button_layout)

        # Discovery results area
        self.discovery_results = QTextEdit()
        self.discovery_results.setReadOnly(True)
        self.discovery_results.setMaximumHeight(100)
        self.discovery_results.setPlaceholderText("Discovered bulbs will appear here...")
        layout.addWidget(self.discovery_results)

        # Help section
        help_group = QGroupBox("About WIZ Smart Bulbs")
        help_layout = QVBoxLayout()

        help_text = QTextBrowser()
        help_text.setOpenExternalLinks(True)
        help_text.setHtml("""
        <p><b>WIZ bulbs</b> are smart LED bulbs that connect to your WiFi network.</p>
        <p><b>To find your bulb IPs:</b></p>
        <ol>
            <li>Make sure your WIZ bulbs are on and connected to WiFi</li>
            <li>Click "Discover Bulbs on Network" above</li>
            <li>Copy the discovered IPs into the appropriate groups</li>
        </ol>
        <p><b>Bulb Groups:</b></p>
        <ul>
            <li><b>Backdrop</b> - Side/background lighting for ambient mood</li>
            <li><b>Overhead</b> - Main room lights (ceiling, lamps)</li>
            <li><b>Battlefield</b> - Special accent lights for dramatic combat scenes</li>
        </ul>
        <p><i>No WIZ bulbs?</i> That's fine! The app still works for music and sound effects.</p>
        <p><a href="https://www.wizconnected.com/">Get WIZ bulbs</a></p>
        """)
        help_text.setMaximumHeight(180)
        help_layout.addWidget(help_text)
        help_group.setLayout(help_layout)
        layout.addWidget(help_group)

        layout.addStretch()
        panel.setLayout(layout)
        return panel

    def _save_spotify_settings(self) -> None:
        """Save Spotify configuration."""
        self.spotify_config.save(
            username=self.spotify_username.text().strip(),
            client_id=self.spotify_client_id.text().strip(),
            client_secret=self.spotify_client_secret.text().strip(),
            redirect_uri=self.spotify_redirect.text().strip() or "http://127.0.0.1:8888/callback"
        )

        # Save auto-start setting
        if self.autostart_start_local.isChecked():
            self.settings_manager.set_spotify_auto_start("start_local")
        elif self.autostart_use_remote.isChecked():
            self.settings_manager.set_spotify_auto_start("use_remote")
        elif self.autostart_disabled.isChecked():
            self.settings_manager.set_spotify_auto_start("disabled")
        else:
            self.settings_manager.set_spotify_auto_start("ask")

        # Update nav item status
        self.nav_list.item(1).setText("🎵 Spotify [✓]")

        QMessageBox.information(
            self,
            "Settings Saved",
            "Spotify settings saved. You may need to restart the app and re-authenticate."
        )

    def _save_wizbulb_settings(self) -> None:
        """Save WIZ bulb configuration."""
        self.wizbulb_config.save(
            backdrop=self.backdrop_bulbs.text().strip(),
            overhead=self.overhead_bulbs.text().strip(),
            battlefield=self.battlefield_bulbs.text().strip()
        )

        # Update nav item status
        self.nav_list.item(2).setText("💡 WIZ Bulbs [✓]")

        QMessageBox.information(
            self,
            "Settings Saved",
            "WIZ bulb settings saved. Changes take effect on next environment activation."
        )

    def _discover_bulbs(self) -> None:
        """Discover WIZ bulbs on the network."""
        self.discovery_results.setText("Discovering bulbs... (this may take a few seconds)")
        QApplication.processEvents()

        try:
            import asyncio
            from pywizlight import discovery

            async def do_discovery():
                bulbs = await discovery.discover_lights(broadcast_space="192.168.1.255")
                return bulbs

            # Run discovery
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                bulbs = loop.run_until_complete(do_discovery())
            finally:
                loop.close()

            if bulbs:
                result_lines = ["Found {} bulb(s):".format(len(bulbs)), ""]
                for bulb in bulbs:
                    result_lines.append(f"  {bulb.ip}")
                result_lines.append("")
                result_lines.append("Copy these IPs to the fields above.")
                self.discovery_results.setText("\n".join(result_lines))
            else:
                self.discovery_results.setText(
                    "No bulbs found.\n\n"
                    "Make sure:\n"
                    "- Bulbs are powered on\n"
                    "- Bulbs are connected to same WiFi network\n"
                    "- Your firewall allows UDP broadcast"
                )
        except ImportError:
            self.discovery_results.setText(
                "pywizlight not installed.\n\n"
                "Run: pip install pywizlight"
            )
        except Exception as e:
            self.discovery_results.setText(f"Discovery failed:\n{str(e)}")

    def _on_nav_changed(self, index: int) -> None:
        """Handle navigation selection change."""
        self.panel_stack.setCurrentIndex(index)

    def _on_theme_changed(self) -> None:
        """Handle theme selection change."""
        if self.light_radio.isChecked():
            self.settings_manager.set_theme("light")
        elif self.dark_radio.isChecked():
            self.settings_manager.set_theme("dark")
        else:
            self.settings_manager.set_theme("system")

        # Show restart message
        QMessageBox.information(
            self,
            "Theme Changed",
            "Please restart the application for the theme change to take effect."
        )


from engines import (
    SoundEngine, SpotifyEngine, LightsEngine, stop_all_sounds,
    register_sound_process, unregister_sound_process,
    AtmosphereEngine, stop_all_atmosphere,
    SpotifyNoActiveDeviceError, is_spotify_running, is_spotify_in_path,
    start_spotify, wait_for_spotify_device
)


class OutlinedLabel(QLabel):
    """QLabel with outlined text for better readability."""

    def __init__(self, text: str, outline_color: QColor = QColor(0, 0, 0),
                 text_color: QColor = QColor(255, 255, 255), parent=None):
        super().__init__(text, parent)
        self.outline_color = outline_color
        self.text_color = text_color
        self._text = text

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Scale font size based on label dimensions
        rect = self.rect()
        min_dimension = min(rect.width(), rect.height())
        font_size = max(8, int(min_dimension * 0.5))  # 50% of smaller dimension, min 8pt

        font = self.font()
        font.setBold(True)
        font.setPointSize(font_size)
        painter.setFont(font)

        # Calculate centered position
        text_rect = painter.fontMetrics().boundingRect(self._text)
        x = (rect.width() - text_rect.width()) / 2
        y = (rect.height() + text_rect.height()) / 2 - painter.fontMetrics().descent()

        # Draw outline by drawing text multiple times with offset
        painter.setPen(QPen(self.outline_color))
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                if dx != 0 or dy != 0:
                    painter.drawText(int(x + dx), int(y + dy), self._text)

        # Draw main text (white)
        painter.setPen(QPen(self.text_color))
        painter.drawText(int(x), int(y), self._text)


class IconButton(QPushButton):
    """QPushButton with a large background emoji icon and scaled text."""

    def __init__(self, text: str, icon_emoji: str = "", parent=None):
        super().__init__("", parent)  # Empty text - we draw it ourselves
        self._label_text = text
        self.icon_emoji = icon_emoji

    def paintEvent(self, event):
        # Draw the default button (background, border) but without text
        super().paintEvent(event)

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect()
        min_dimension = min(rect.width(), rect.height())

        # Draw background emoji if present
        if self.icon_emoji:
            emoji_font_size = max(24, int(min_dimension * 0.5))  # 50% of smaller dimension
            font = painter.font()
            font.setPointSize(emoji_font_size)
            painter.setFont(font)
            painter.setOpacity(0.15)
            painter.drawText(rect, Qt.AlignCenter, self.icon_emoji)

        # Draw label text with scaled font
        painter.setOpacity(1.0)
        label_font_size = max(10, min(24, int(min_dimension * 0.10)))  # 10% of smaller dim, 10-24px
        font = painter.font()
        font.setPointSize(label_font_size)
        painter.setFont(font)
        # Use palette color for text (respects dark/light mode)
        painter.setPen(self.palette().color(self.palette().ButtonText))
        painter.drawText(rect, Qt.AlignCenter | Qt.TextWordWrap, self._label_text)


class ButtonContainer(QWidget):
    """Container widget that handles dynamic resizing with overlapping emoji indicators."""

    def __init__(self, btn: QPushButton, emoji_row: QWidget,
                 shortcut_label: Optional[QLabel] = None,
                 desc_label: Optional[QLabel] = None):
        super().__init__()
        self.btn = btn
        self.emoji_row = emoji_row
        self.shortcut_label = shortcut_label
        self.desc_label = desc_label
        self.btn.setParent(self)
        self.emoji_row.setParent(self)
        if self.shortcut_label:
            self.shortcut_label.setParent(self)
        if self.desc_label:
            self.desc_label.setParent(self)
        self.setMinimumHeight(130)
        self.setMinimumWidth(180)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def resizeEvent(self, event):
        w = self.width()
        h = self.height()
        # Reserve space for description at bottom
        desc_height = 30 if self.desc_label else 0
        btn_height = h - 10 - desc_height
        # Button fills container except for overlap and description
        self.btn.setGeometry(0, 0, w, btn_height)
        # Emoji row at bottom of button, overlapping by 10px
        self.emoji_row.setGeometry(0, btn_height - 10, w, 20)
        self.emoji_row.raise_()
        # Shortcut label in top-left, scaling with button size
        if self.shortcut_label:
            # Scale badge size based on button dimensions (15-20% of smaller dimension)
            min_dim = min(w, btn_height)
            badge_size = max(25, int(min_dim * 0.18))  # 18% of smaller dimension, min 25px
            badge_width = int(badge_size * 1.15)  # Slightly wider than tall
            self.shortcut_label.setGeometry(5, 5, badge_width, badge_size)
            self.shortcut_label.raise_()
        # Description below emoji row
        if self.desc_label:
            self.desc_label.setGeometry(10, btn_height + 5, w - 20, desc_height)
        super().resizeEvent(event)


class NowPlayingWidget(QWidget):
    """Widget showing current playing state with icon and label overlay."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(60)

        # Horizontal layout: "now playing:" on left, then icon section on right
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(8, 2, 8, 2)
        main_layout.setSpacing(6)

        # "now playing:" label always visible on the left
        self.title_label = QLabel("now playing:")
        self.title_label.setAlignment(Qt.AlignVCenter | Qt.AlignRight)
        self.title_label.setStyleSheet("font-size: 15px; color: #888; margin-top: 18px;")
        main_layout.addWidget(self.title_label)

        # Right section: status label on top, icon below (fixed width to prevent bouncing)
        icon_section = QWidget()
        icon_section.setFixedWidth(100)
        icon_layout = QVBoxLayout(icon_section)
        icon_layout.setContentsMargins(0, 0, 0, 0)
        icon_layout.setSpacing(0)

        # Status label on top (describes current state)
        self.status_label = QLabel("idle")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("font-size: 9px; color: #666; font-weight: bold;")
        icon_layout.addWidget(self.status_label)

        # Icon display below (visual indicator)
        self.icon_label = QLabel("⏸")
        self.icon_label.setAlignment(Qt.AlignCenter)
        self.icon_label.setStyleSheet("font-size: 24px;")
        icon_layout.addWidget(self.icon_label)

        main_layout.addWidget(icon_section)

        # State tracking
        self._current_state = "idle"  # idle, lights, sound, downloading
        self._lights_icon = ""
        self._lights_name = ""
        self._sound_icon = "🔊"
        self._download_icon = "⬇️"
        self._idle_icon = "⏸"

        # Pulse animation for download
        self._pulse_timer = QTimer(self)
        self._pulse_timer.timeout.connect(self._pulse_download)
        self._pulse_opacity = 1.0
        self._pulse_direction = -1
        self._download_count = 0  # Track concurrent downloads

        self.setStyleSheet("""
            NowPlayingWidget {
                background-color: rgba(100, 100, 100, 0.1);
                border: 1px solid rgba(100, 100, 100, 0.3);
                border-radius: 4px;
            }
        """)

    def set_lights(self, icon: str, name: str = "") -> None:
        """Set lights as active with the given icon."""
        self._lights_icon = icon
        self._lights_name = name if name else "lights"
        if self._current_state != "sound" and self._current_state != "downloading":
            self._current_state = "lights"
            self._stop_pulse()
            self.icon_label.setStyleSheet("font-size: 24px;")
            self.icon_label.setText(icon)
            self.status_label.setText(self._lights_name)

    def set_sound(self, active: bool = True, icon: str = "", name: str = "") -> None:
        """Set sound as active (temporarily shows sound icon)."""
        if active:
            self._current_state = "sound"
            self._stop_pulse()
            self.icon_label.setStyleSheet("font-size: 24px;")
            self.icon_label.setText(icon if icon else self._sound_icon)
            self.status_label.setText(name if name else "sound")
        else:
            # Sound finished, return to lights if we have it
            if self._lights_icon:
                self._current_state = "lights"
                self.icon_label.setStyleSheet("font-size: 24px;")
                self.icon_label.setText(self._lights_icon)
                self.status_label.setText(self._lights_name)
            else:
                self._current_state = "idle"
                self.icon_label.setStyleSheet("font-size: 24px;")
                self.icon_label.setText(self._idle_icon)
                self.status_label.setText("idle")

    def set_downloading(self, active: bool = True) -> None:
        """Show downloading state with pulsing icon. Uses counter for concurrent downloads."""
        if active:
            self._download_count += 1
            if self._download_count == 1:
                # First download starting - show pulsing icon
                self._current_state = "downloading"
                self.icon_label.setText(self._download_icon)
                self.status_label.setText("downloading")
                self._start_pulse()
        else:
            self._download_count = max(0, self._download_count - 1)
            if self._download_count == 0:
                # All downloads complete - return to previous state
                self._stop_pulse()
                self.icon_label.setStyleSheet("font-size: 24px;")
                if self._lights_icon:
                    self._current_state = "lights"
                    self.icon_label.setText(self._lights_icon)
                    self.status_label.setText(self._lights_name)
                else:
                    self._current_state = "idle"
                    self.icon_label.setText(self._idle_icon)
                    self.status_label.setText("idle")

    def clear(self) -> None:
        """Clear the now playing widget."""
        self._current_state = "idle"
        self._lights_icon = ""
        self._lights_name = ""
        self._download_count = 0
        self._stop_pulse()
        self.icon_label.setStyleSheet("font-size: 24px;")
        self.icon_label.setText(self._idle_icon)
        self.status_label.setText("idle")

    def _start_pulse(self) -> None:
        """Start the pulse animation."""
        self._pulse_timer.start(50)

    def _stop_pulse(self) -> None:
        """Stop the pulse animation."""
        self._pulse_timer.stop()
        self._pulse_opacity = 1.0

    def _pulse_download(self) -> None:
        """Animate the download icon opacity."""
        self._pulse_opacity += self._pulse_direction * 0.05
        if self._pulse_opacity <= 0.3:
            self._pulse_direction = 1
        elif self._pulse_opacity >= 1.0:
            self._pulse_direction = -1
        opacity_int = int(self._pulse_opacity * 255)
        self.icon_label.setStyleSheet(f"font-size: 28px; color: rgba(0, 150, 255, {opacity_int});")


class FuzzySearchBar(QLineEdit):
    """Search bar with substring matching results list."""

    environment_selected = pyqtSignal(str, int)  # (config_name, category_index)

    def __init__(self, configs: Dict[str, List[Dict[str, Any]]], parent=None):
        super().__init__(parent)
        self.setPlaceholderText("Search environments... (Ctrl+L)")
        self.setMinimumWidth(300)

        # Build search index: (display_text, search_text, name, category_index)
        self.items: List[tuple] = []
        category_index = 0
        for category, config_list in configs.items():
            for config in config_list:
                name = config["name"]
                description = config.get("description", "")
                tags = config.get("metadata", {}).get("tags", [])
                intensity = config.get("metadata", {}).get("intensity", "")

                display_text = f"{name} - {description}"
                search_text = f"{name} {description} {intensity} {' '.join(tags)}".lower()

                self.items.append((display_text, search_text, name, category_index))
            category_index += 1

        # Results list - will be parented to top-level window
        self.results = QListWidget()
        self.results.setWindowFlags(Qt.ToolTip)  # Lightweight overlay, not a full popup
        self.results.setMaximumHeight(200)
        self.results.setMinimumWidth(400)
        self.results.hide()
        self.results.itemClicked.connect(self._on_item_clicked)
        self.results.itemActivated.connect(self._on_item_clicked)

        self.textChanged.connect(self._on_text_changed)
        self.returnPressed.connect(self._select_first)

    def _on_text_changed(self, text: str) -> None:
        """Filter and show results."""
        self.results.clear()
        if not text:
            self.results.hide()
            return

        pattern = text.lower()
        matches = [(disp, name, cat_idx) for disp, search, name, cat_idx in self.items
                   if pattern in search]

        if matches:
            for disp, name, cat_idx in matches[:15]:
                item = QListWidgetItem(disp)
                item.setData(Qt.UserRole, (name, cat_idx))
                self.results.addItem(item)
            self.results.setCurrentRow(0)
            # Position below the search bar
            pos = self.mapToGlobal(self.rect().bottomLeft())
            self.results.move(pos)
            self.results.setFixedWidth(max(400, self.width()))
            self.results.show()
        else:
            self.results.hide()

    def _on_item_clicked(self, item: QListWidgetItem) -> None:
        """Handle item selection."""
        name, cat_idx = item.data(Qt.UserRole)
        self.environment_selected.emit(name, cat_idx)
        self._clear_and_hide()

    def _select_first(self) -> None:
        """Select first result on Enter."""
        if self.results.count() > 0:
            current = self.results.currentItem()
            if current:
                self._on_item_clicked(current)

    def _clear_and_hide(self) -> None:
        """Clear text and hide results."""
        self.clear()
        self.results.hide()
        self.clearFocus()

    def keyPressEvent(self, event) -> None:
        """Handle arrow keys for result navigation."""
        if event.key() == Qt.Key_Down and self.results.isVisible():
            row = self.results.currentRow()
            if row < self.results.count() - 1:
                self.results.setCurrentRow(row + 1)
            return
        elif event.key() == Qt.Key_Up and self.results.isVisible():
            row = self.results.currentRow()
            if row > 0:
                self.results.setCurrentRow(row - 1)
            return
        elif event.key() == Qt.Key_Escape:
            self._clear_and_hide()
            return
        super().keyPressEvent(event)

    def focusOutEvent(self, event) -> None:
        """Hide results when focus is lost."""
        # Small delay to allow click on results to register
        QTimer.singleShot(150, self._maybe_hide_results)
        super().focusOutEvent(event)

    def _maybe_hide_results(self) -> None:
        """Hide results if we don't have focus."""
        if not self.hasFocus():
            self.results.hide()


class EngineRunner(QThread):
    """Background thread for running async engines."""

    error_occurred = pyqtSignal(str)
    status_update = pyqtSignal(str)
    sound_finished = pyqtSignal()  # Signal when sound-only config finishes
    spotify_no_device = pyqtSignal()  # Signal when Spotify has no active device

    # Signals for ImmersiveStatusBar
    sound_started = pyqtSignal(str)   # sound filename
    sound_done = pyqtSignal()         # sound playback finished (always emitted)
    music_started = pyqtSignal(str)   # playlist name
    atmosphere_started = pyqtSignal(str)  # atmosphere sound names
    lights_started = pyqtSignal(str)  # animation/config name
    download_started = pyqtSignal(str)  # download title
    download_finished = pyqtSignal()    # download complete

    def __init__(self, config: Dict[str, Any]):
        super().__init__()
        self.config = config
        self.lights_engine: Optional[LightsEngine] = None
        self.running = False
        self.has_lights = config["engines"]["lights"]["enabled"]
        self.has_atmosphere = config["engines"].get("atmosphere", {}).get("enabled", False)
        self._sound_done_event = threading.Event()

    def run(self):
        """Run the engines based on configuration."""
        try:
            self.running = True

            # Sound engine (non-blocking, fire and forget)
            # Default transition sound for environments with lights, spotify, or atmosphere
            DEFAULT_SOUND = "https://freesound.org/people/DJT4NN3R/sounds/449994/"

            has_spotify = self.config["engines"]["spotify"]["enabled"]
            has_atmosphere = self.config["engines"].get("atmosphere", {}).get("enabled", False)
            sound_enabled = self.config["engines"]["sound"]["enabled"]

            if sound_enabled:
                sound_file = self.config["engines"]["sound"].get("file", DEFAULT_SOUND)
            elif self.has_lights or has_spotify or has_atmosphere:
                # Play default transition sound for lights/spotify/atmosphere environments without explicit sound
                sound_file = DEFAULT_SOUND
            else:
                sound_file = None

            # Start sound in a separate thread so it doesn't block Spotify/lights
            if sound_file:
                sound_thread = threading.Thread(
                    target=self._play_sound_async,
                    args=(sound_file, sound_enabled),
                    daemon=True
                )
                sound_thread.start()

            # Spotify engine (synchronous) - only if atmosphere is not enabled
            if self.config["engines"]["spotify"]["enabled"]:
                context_uri = self.config["engines"]["spotify"]["context_uri"]
                self.status_update.emit(f"Starting Spotify...")
                try:
                    spotify_engine = SpotifyEngine()
                    spotify_engine.play_context_with_device_check(context_uri)
                    self.status_update.emit("Spotify playback started")
                    # Try to get playlist name from Spotify API
                    playlist_name = self._get_playlist_name(spotify_engine, context_uri)
                    self.music_started.emit(playlist_name)
                except SpotifyNoActiveDeviceError:
                    self.spotify_no_device.emit()
                except Exception as e:
                    self.error_occurred.emit(f"Spotify error: {str(e)}")

            # Atmosphere engine (alternative to Spotify - looping ambient sounds)
            if has_atmosphere:
                self.status_update.emit("Starting atmosphere...")
                try:
                    atmosphere_engine = AtmosphereEngine()
                    mix = self.config["engines"]["atmosphere"]["mix"]

                    # Check for uncached files and emit download signals
                    freesound = FreesoundManager()
                    needs_download = False
                    for sound_config in mix:
                        url = sound_config.get("url", "")
                        if is_freesound_url(url):
                            creator, sound_id = freesound.parse_url(url)
                            if not freesound._find_cached_file(creator, sound_id):
                                needs_download = True
                                break

                    if needs_download:
                        self.download_started.emit("atmosphere sounds")
                        self.status_update.emit("Downloading atmosphere sounds...")
                        # Small delay to ensure UI updates before blocking download
                        QThread.msleep(50)

                    # Get display names for status bar (this will download if needed)
                    display_names = atmosphere_engine.get_display_names(mix)
                    combined_name = " + ".join(display_names)

                    if needs_download:
                        self.download_finished.emit()

                    # Start playback
                    if atmosphere_engine.play_mix(mix):
                        self.status_update.emit("Atmosphere playing")
                        self.atmosphere_started.emit(combined_name)
                    else:
                        self.error_occurred.emit("Failed to start atmosphere (ffplay required)")
                except Exception as e:
                    self.download_finished.emit()  # Clear download state on error
                    self.error_occurred.emit(f"Atmosphere error: {str(e)}")

            # Lights engine (asynchronous, continuous)
            if self.config["engines"]["lights"]["enabled"]:
                self.status_update.emit("Starting light animation...")
                try:
                    # Run async event loop for lights
                    asyncio.run(self._run_lights())
                except Exception as e:
                    self.error_occurred.emit(f"Lights error: {str(e)}")
            elif self.config["engines"]["sound"]["enabled"]:
                # Sound-only config - wait for sound to finish
                self._sound_done_event.wait()

        except Exception as e:
            self.error_occurred.emit(f"Engine error: {str(e)}")
        finally:
            self.running = False

    def _play_sound_async(self, sound_file: str, sound_enabled: bool) -> None:
        """Handle sound download and playback in a separate thread."""
        try:
            # Check if this is a freesound.org URL
            if is_freesound_url(sound_file):
                try:
                    freesound = FreesoundManager()

                    # Check if we need to download (not cached)
                    creator, sound_id = freesound.parse_url(sound_file)
                    cached = freesound._find_cached_file(creator, sound_id)

                    if not cached:
                        # Need to download - emit signal
                        sound_name = freesound._fetch_sound_name(sound_file)
                        self.download_started.emit(sound_name.replace('_', ' '))
                        self.status_update.emit(f"Downloading sound: {sound_name.replace('_', ' ')}")
                        # Small delay to ensure UI updates before blocking download
                        import time
                        time.sleep(0.05)

                    local_path, metadata = freesound.get_sound(sound_file)

                    if not cached:
                        # Download finished
                        self.download_finished.emit()
                        # Auto-create YAML config for this freesound
                        self._auto_create_freesound_config(sound_file, metadata)

                    # Sound name from title already includes "by creator"
                    sound_display = metadata["sound_name"].replace('_', ' ')
                    sound_file = str(local_path)
                except Exception as e:
                    self.download_finished.emit()  # Clear download state on error
                    self.error_occurred.emit(f"Freesound error: {str(e)}")
                    return
            else:
                sound_display = sound_file

            self.status_update.emit(f"Playing sound: {sound_display}")
            self.sound_started.emit(sound_display)

            # Play sound directly (we're already in a thread)
            # Use subprocess for stoppable playback
            sound_path = Path(sound_file)
            if not sound_path.is_absolute():
                sound_path = Path.cwd() / sound_file

            if sound_path.exists():
                # Try common audio players
                for player in [["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet"], ["paplay"], ["aplay", "-q"]]:
                    try:
                        proc = subprocess.Popen(
                            player + [str(sound_path)],
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL
                        )
                        # Register process so it can be stopped
                        register_sound_process(proc)
                        proc.wait()
                        # Unregister when done
                        unregister_sound_process(proc)
                        break
                    except FileNotFoundError:
                        continue

            # Always signal when sound playback finishes
            self.sound_done.emit()

            # Signal completion for sound-only configs (keeps existing behavior)
            if not self.has_lights and sound_enabled:
                self._on_sound_complete()
        except Exception as e:
            self.sound_done.emit()  # Clear sound state on error
            self.error_occurred.emit(f"Sound error: {str(e)}")

    def _auto_create_freesound_config(self, url: str, metadata: Dict[str, str]) -> None:
        """Auto-create a YAML config for a new freesound download."""
        try:
            sound_name = metadata.get("sound_name", "Unknown")
            creator = metadata.get("creator", "Unknown")
            sound_id = metadata.get("sound_id", "0")

            # Create a safe filename
            safe_name = sound_name.lower().replace(' ', '_').replace('-', '_')
            safe_name = ''.join(c for c in safe_name if c.isalnum() or c == '_')
            config_filename = f"freesound_{safe_name}_{sound_id}.yaml"
            config_path = Path("env_conf") / config_filename

            # Check if config already exists
            if config_path.exists():
                return

            # Create the config content - freesounds are loop-capable
            display_name = sound_name.replace('_', ' ')
            config_content = f'''name: "{display_name}"
category: "freesound"
description: "Freesound by {creator}"
icon: "🔁"

metadata:
  tags: ["freesound", "downloaded", "{creator}", "loop"]
  intensity: "low"
  suitable_for: ["ambient", "atmosphere", "loop"]
  loop: true

engines:
  sound:
    enabled: true
    file: "{url}"
    loop: true

  spotify:
    enabled: false

  lights:
    enabled: false
'''
            # Write the config file
            with open(config_path, 'w') as f:
                f.write(config_content)

        except Exception as e:
            # Don't fail the main operation if auto-config fails
            print(f"Warning: Failed to auto-create freesound config: {e}")

    def _on_sound_complete(self):
        """Called when sound-only playback completes."""
        self._sound_done_event.set()
        self.sound_finished.emit()

    def _get_playlist_name(self, spotify_engine: "SpotifyEngine", context_uri: str) -> str:
        """Fetch playlist name from Spotify API. Falls back to config name on error."""
        try:
            # Extract playlist ID from URI (e.g., "spotify:playlist:5Q8DWZnPe7o7GA96SARmOK")
            if context_uri.startswith("spotify:playlist:"):
                playlist_id = context_uri.split(":")[-1]
                playlist = spotify_engine.spotify_client.playlist(playlist_id, fields="name")
                return playlist.get("name", self.config.get("name", "Unknown"))
            else:
                # Not a playlist (could be album, artist, etc.)
                return self.config.get("name", "Unknown")
        except Exception:
            # Fallback to config name
            return self.config.get("name", "Unknown")

    async def _run_lights(self):
        """Run the lights engine asynchronously."""
        self.lights_engine = LightsEngine()
        animation_config = self.config["engines"]["lights"]["animation"]

        await self.lights_engine.start(animation_config)
        config_name = self.config.get("name", "Unknown")
        self.status_update.emit(f"Light animation running: {config_name}")
        self.lights_started.emit(config_name)

        # Keep running until stopped (check frequently for fast response)
        while self.running:
            await asyncio.sleep(0.05)

        await self.lights_engine.stop()

    def stop(self):
        """Stop the engines."""
        self.running = False
        # Don't block - let the old thread clean up in background
        # New environment can start immediately


class EnvironmentLauncher(QMainWindow):
    """Main PyQt5 window for the environment launcher with tabs."""

    # Keyboard shortcuts (applied to current tab only)
    KEYS = [
        "Q", "W", "E", "R", "T", "Y", "U", "I", "O", "P",
        "A", "S", "D", "F", "G", "H", "J", "K", "L", ";",
        "Z", "X", "C", "V", "B", "N",
    ]

    # Button styles (font-size 17px for larger name display)
    ACTIVE_STYLE = "background-color: #4CAF50; color: white; padding: 8px; font-size: 17px;"
    ATMOSPHERE_ACTIVE_STYLE = "background-color: #5B9BD5; color: white; padding: 8px; font-size: 17px;"  # Blue for atmosphere members
    INACTIVE_STYLE = "padding: 8px; font-size: 17px;"
    STOP_STYLE = "background-color: #f44336; color: white; font-weight: bold; font-size: 12px;"
    DESC_STYLE = "font-size: 11px; color: #666; padding: 2px 4px; border: 1px solid #ccc; border-radius: 3px; background-color: #fafafa;"
    DESC_STYLE_DARK = "font-size: 11px; color: #aaa; padding: 2px 4px; border: 1px solid #555; border-radius: 3px; background-color: #2a2a2a;"

    # Global tooltip style for readability in both light and dark modes
    TOOLTIP_STYLE = """
        QToolTip {
            background-color: #ffffcc;
            color: #333333;
            border: 1px solid #666666;
            padding: 4px;
            font-family: monospace;
        }
    """

    def __init__(self, settings_manager: SettingsManager):
        super().__init__()
        self.settings_manager = settings_manager
        self.setWindowTitle("Immerse Yourself - Environment Launcher")
        self.setGeometry(100, 100, 1000, 600)

        # Apply tooltip style globally to all child widgets
        self.setStyleSheet(self.TOOLTIP_STYLE)

        # Detect dark mode based on settings
        self.is_dark_mode = self._is_dark_mode_enabled()

        # Load configurations
        self.config_loader = ConfigLoader("env_conf")
        self.configs = self._load_and_organize_configs()

        # Track active environment
        self.current_runner: Optional[EngineRunner] = None
        self.current_config_name: Optional[str] = None
        self.lights_runner: Optional[EngineRunner] = None  # Runner with active lights
        self.lights_config_name: Optional[str] = None  # Config name with active lights
        self.buttons: Dict[str, QPushButton] = {}  # config_name -> button
        self.shortcuts: List[QShortcut] = []
        self._old_runners: List[EngineRunner] = []  # Keep refs until threads finish
        self.tab_configs: Dict[int, List[Dict[str, Any]]] = {}  # tab_index -> configs
        self._pending_search_button: Optional[QPushButton] = None  # Button from search result

        # Track active atmosphere sounds (URLs currently playing in atmosphere)
        self.active_atmosphere_urls: Set[str] = set()
        self.url_to_config: Dict[str, Dict[str, Any]] = {}  # URL -> config mapping

        # Store Spotify config manager for checking configuration
        self.spotify_config = SpotifyConfigManager()

        # Store WIZ bulb config manager for checking configuration
        self.wizbulb_config = WizBulbConfigManager()

        # Create immersive status bar
        self.immersive_status = ImmersiveStatusBar(self)

        # Create UI
        self._create_menu()
        self._create_ui()
        self._setup_tab_shortcuts()

        # Build URL to config mapping for atmosphere tracking
        self._build_url_to_config_mapping()

        # Schedule startup Spotify check (after window is shown)
        QTimer.singleShot(500, self._check_startup_spotify)

    def _check_startup_spotify(self) -> None:
        """Check Spotify status on startup and optionally play music."""
        # Only proceed if Spotify is configured
        if not self.spotify_config.is_configured():
            return

        # Find the "startup" config (or fall back to "travel")
        startup_config = None
        travel_config = None
        for category, configs in self.configs.items():
            for config in configs:
                name = config.get("name", "").lower()
                if name == "startup":
                    startup_config = config
                elif name == "travel":
                    travel_config = config
            if startup_config:
                break

        # Use startup if found, otherwise fall back to travel
        startup_config = startup_config or travel_config

        if not startup_config:
            return

        # Check Spotify status FIRST before trying to play
        auto_start = self.settings_manager.get_spotify_auto_start()

        # If disabled, skip startup music entirely
        if auto_start == "disabled":
            self.immersive_status.set_message("Ready (Spotify disabled in settings)", timeout_ms=5000)
            return

        # Try to connect to Spotify and check for active device
        try:
            engine = SpotifyEngine()
            local_device = engine.get_local_computer_device()

            if local_device:
                # Local device exists and ready - start startup environment
                self.immersive_status.set_message("Spotify connected - starting...", timeout_ms=3000)
                self._start_environment(startup_config)
                return

            # No local device - need to handle based on settings
            spotify_running = is_spotify_running()
            spotify_available = is_spotify_in_path()
            remote_devices = engine.get_remote_devices()

            if auto_start == "start_local":
                if self._ensure_local_spotify(spotify_running, spotify_available, startup_config):
                    # Spotify starting - polling will auto-start when ready
                    return
                # Failed to start - fall through to show status
                self.immersive_status.set_message("Ready (could not start Spotify)", timeout_ms=5000)
                return

            if auto_start == "use_remote":
                if remote_devices:
                    # Connect to first remote device and play
                    device = remote_devices[0]
                    if engine.transfer_to_device(device["id"], start_playback=False):
                        self.immersive_status.set_message(f"Connected to {device['name']} - starting...", timeout_ms=3000)
                        self._start_environment(startup_config)
                        return
                self.immersive_status.set_message("Ready (no remote devices available)", timeout_ms=5000)
                return

            # auto_start == "ask" - show dialog
            if self._show_startup_spotify_dialog(spotify_running, spotify_available, remote_devices, engine, startup_config):
                # User chose an option that connected successfully
                self.immersive_status.set_message("Spotify connected - starting...", timeout_ms=3000)
                self._start_environment(startup_config)

        except FileNotFoundError:
            # Spotify not configured
            self.immersive_status.set_message("Ready (Spotify not configured)", timeout_ms=5000)
        except Exception as e:
            # Other error - just show ready
            self.immersive_status.set_message(f"Ready (Spotify: {e})", timeout_ms=5000)

    def _ensure_local_spotify(self, spotify_running: bool, spotify_available: bool,
                               then_play_config: Optional[Dict[str, Any]] = None) -> bool:
        """Ensure Spotify is running locally. Returns True if started/running.

        Args:
            spotify_running: Whether Spotify process is currently running
            spotify_available: Whether Spotify executable is in PATH
            then_play_config: If provided, auto-start this config after Spotify is ready
        """
        if spotify_running:
            # Spotify is running but no device - need user to activate it
            QMessageBox.information(
                self,
                "Spotify Running",
                "Spotify is running but not playing on this PC.\n\n"
                "Please click on any track in Spotify to activate playback, "
                "then click an environment to start music."
            )
            return False

        if not spotify_available:
            return False

        self.immersive_status.set_message("Starting Spotify...", timeout_ms=0)
        if start_spotify():
            # Start polling for Spotify to be ready
            self._poll_for_spotify_ready(then_play_config)
            return True
        return False

    def _poll_for_spotify_ready(self, then_play_config: Optional[Dict[str, Any]] = None,
                                 attempts: int = 0, max_attempts: int = 20) -> None:
        """Poll for Spotify to become ready, then optionally start an environment.

        Args:
            then_play_config: Config to auto-start when ready
            attempts: Current attempt number
            max_attempts: Maximum polling attempts (20 * 500ms = 10 seconds)
        """
        if attempts >= max_attempts:
            self.immersive_status.set_message("Spotify started - click an environment to play music", timeout_ms=5000)
            self.activateWindow()
            self.raise_()
            return

        # Check if Spotify device is now available
        try:
            engine = SpotifyEngine()
            local_device = engine.get_local_computer_device()

            if local_device:
                # Device found! Wait 5 more seconds for stability, then proceed
                self.immersive_status.set_message("Spotify ready - starting music in 5s...", timeout_ms=0)
                QTimer.singleShot(5000, lambda: self._spotify_ready_play(then_play_config))
                return
        except:
            pass

        # Not ready yet - check again in 500ms
        self.immersive_status.set_message(f"Waiting for Spotify... ({attempts + 1})", timeout_ms=0)
        QTimer.singleShot(500, lambda: self._poll_for_spotify_ready(then_play_config, attempts + 1, max_attempts))

    def _spotify_ready_play(self, config: Optional[Dict[str, Any]]) -> None:
        """Called when Spotify is ready - steal focus and optionally start environment."""
        # Steal focus back from Spotify
        self.activateWindow()
        self.raise_()

        if config:
            self.immersive_status.set_message(f"Starting {config['name']}...", timeout_ms=3000)
            self._start_environment(config)

    def _show_startup_spotify_dialog(self, spotify_running: bool, spotify_available: bool,
                                      remote_devices: list, engine: "SpotifyEngine",
                                      then_play_config: Optional[Dict[str, Any]] = None) -> bool:
        """Show startup Spotify options dialog. Returns True if connected successfully."""
        from PyQt5.QtWidgets import QDialog, QCheckBox

        dialog = QDialog(self)
        dialog.setWindowTitle("Spotify Setup")
        dialog.setMinimumWidth(400)

        layout = QVBoxLayout()

        # Message
        msg = QLabel(
            "Spotify is not playing on this PC.\n\n"
            "How would you like to play music?"
        )
        msg.setWordWrap(True)
        layout.addWidget(msg)

        # Store result
        self._startup_dialog_result = None

        # Options as buttons
        btn_layout = QVBoxLayout()

        # Option 1: Start Spotify locally
        btn_start = QPushButton("Start Spotify on this PC")
        btn_start.setEnabled(spotify_available and not spotify_running)
        if spotify_running:
            btn_start.setText("Spotify is running (activate it manually)")
            btn_start.setEnabled(False)
        elif not spotify_available:
            btn_start.setToolTip("Spotify not found in PATH")
        btn_start.clicked.connect(lambda: self._startup_dialog_choose(dialog, "start_local"))
        btn_layout.addWidget(btn_start)

        # Option 2: Use remote device
        btn_remote = QPushButton(f"Connect to another device ({len(remote_devices)} available)")
        btn_remote.setEnabled(len(remote_devices) > 0)
        if not remote_devices:
            btn_remote.setToolTip("No remote devices found")
        btn_remote.clicked.connect(lambda: self._startup_dialog_choose(dialog, "use_remote"))
        btn_layout.addWidget(btn_remote)

        # Option 3: Continue without music
        btn_skip = QPushButton("Continue without music")
        btn_skip.clicked.connect(lambda: self._startup_dialog_choose(dialog, "disabled"))
        btn_layout.addWidget(btn_skip)

        layout.addLayout(btn_layout)

        # Remember choice checkbox
        self._startup_remember_checkbox = QCheckBox("Remember my choice")
        layout.addWidget(self._startup_remember_checkbox)

        dialog.setLayout(layout)
        dialog.exec_()

        # Handle the result
        if self._startup_dialog_result is None:
            return False

        # Save setting if remember is checked
        if self._startup_remember_checkbox.isChecked():
            self.settings_manager.set_spotify_auto_start(self._startup_dialog_result)

        if self._startup_dialog_result == "start_local":
            # Pass the config so it auto-starts after Spotify is ready
            if self._ensure_local_spotify(spotify_running, spotify_available, then_play_config):
                return False  # Started - polling will handle the rest
            return False

        if self._startup_dialog_result == "use_remote":
            if remote_devices:
                # If multiple, let user choose
                if len(remote_devices) > 1:
                    device_names = [f"{d['name']} ({d['type']})" for d in remote_devices]
                    from PyQt5.QtWidgets import QInputDialog
                    choice, ok = QInputDialog.getItem(
                        self, "Select Device", "Choose a Spotify device:",
                        device_names, 0, False
                    )
                    if ok and choice:
                        idx = device_names.index(choice)
                        device = remote_devices[idx]
                    else:
                        return False
                else:
                    device = remote_devices[0]

                if engine.transfer_to_device(device["id"], start_playback=False):
                    self.immersive_status.set_message(f"Connected to {device['name']}", timeout_ms=3000)
                    return True
            return False

        # "disabled" - continue without music
        self.immersive_status.set_message("Continuing without music", timeout_ms=3000)
        return False

    def _startup_dialog_choose(self, dialog: "QDialog", choice: str) -> None:
        """Handle choice from startup dialog."""
        self._startup_dialog_result = choice
        dialog.accept()

    def _handle_spotify_no_device(self) -> None:
        """Handle case where Spotify has no active device on this PC."""
        auto_start = self.settings_manager.get_spotify_auto_start()

        # If disabled, just silently continue without music
        if auto_start == "disabled":
            self.immersive_status.set_message("Running without music (Spotify disabled in settings)", timeout_ms=5000)
            return

        # Check what options are available
        spotify_running = is_spotify_running()
        spotify_available = is_spotify_in_path()

        # Try to get remote devices for the "use remote" option
        remote_devices = []
        try:
            engine = SpotifyEngine()
            remote_devices = engine.get_remote_devices()
        except:
            pass

        # Handle based on setting
        if auto_start == "start_local":
            self._do_start_local_spotify(spotify_running, spotify_available)
            return

        if auto_start == "use_remote":
            self._do_use_remote_spotify(remote_devices)
            return

        # auto_start == "ask" - show dialog with options
        self._show_spotify_options_dialog(spotify_running, spotify_available, remote_devices)

    def _do_start_local_spotify(self, spotify_running: bool, spotify_available: bool) -> None:
        """Try to start Spotify locally."""
        if spotify_running:
            QMessageBox.information(
                self,
                "Spotify Running",
                "Spotify is running but not playing on this PC.\n\n"
                "Please click on any track in Spotify to activate playback, "
                "then try again."
            )
            return

        if not spotify_available:
            QMessageBox.warning(
                self,
                "Spotify Not Found",
                "Spotify is not installed or not found in your PATH.\n\n"
                "Please install Spotify or start it manually."
            )
            return

        self.immersive_status.set_message("Starting Spotify...", timeout_ms=0)
        if start_spotify():
            QMessageBox.information(
                self,
                "Spotify Starting",
                "Spotify is starting. Please wait a moment for it to initialize, "
                "then click on an environment again to start music."
            )
        else:
            QMessageBox.warning(
                self,
                "Failed to Start Spotify",
                "Could not start Spotify. Please start it manually."
            )

    def _do_use_remote_spotify(self, remote_devices: list) -> None:
        """Try to use a remote Spotify device."""
        if not remote_devices:
            QMessageBox.warning(
                self,
                "No Remote Devices",
                "No remote Spotify devices found.\n\n"
                "Make sure Spotify is running on another device and try again."
            )
            return

        # If only one device, use it directly
        if len(remote_devices) == 1:
            device = remote_devices[0]
            try:
                engine = SpotifyEngine()
                if engine.transfer_to_device(device["id"], start_playback=False):
                    self.immersive_status.set_message(f"Connected to {device['name']}", timeout_ms=3000)
                    QMessageBox.information(
                        self,
                        "Connected",
                        f"Connected to {device['name']}.\n\n"
                        "Click on an environment again to start music."
                    )
                else:
                    QMessageBox.warning(self, "Failed", f"Could not connect to {device['name']}")
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to connect: {e}")
            return

        # Multiple devices - let user choose
        device_names = [f"{d['name']} ({d['type']})" for d in remote_devices]
        from PyQt5.QtWidgets import QInputDialog
        choice, ok = QInputDialog.getItem(
            self,
            "Select Device",
            "Choose a Spotify device:",
            device_names,
            0,
            False
        )
        if ok and choice:
            idx = device_names.index(choice)
            device = remote_devices[idx]
            try:
                engine = SpotifyEngine()
                if engine.transfer_to_device(device["id"], start_playback=False):
                    self.immersive_status.set_message(f"Connected to {device['name']}", timeout_ms=3000)
                else:
                    QMessageBox.warning(self, "Failed", f"Could not connect to {device['name']}")
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to connect: {e}")

    def _show_spotify_options_dialog(self, spotify_running: bool, spotify_available: bool, remote_devices: list) -> None:
        """Show dialog with Spotify connection options."""
        from PyQt5.QtWidgets import QDialog, QDialogButtonBox

        dialog = QDialog(self)
        dialog.setWindowTitle("Spotify - No Active Device")
        dialog.setMinimumWidth(400)

        layout = QVBoxLayout()

        # Message
        msg = QLabel(
            "Spotify is not playing on this PC.\n\n"
            "What would you like to do?"
        )
        msg.setWordWrap(True)
        layout.addWidget(msg)

        # Options as buttons
        btn_layout = QVBoxLayout()

        # Option 1: Start Spotify locally
        btn_start = QPushButton("Start Spotify on this PC")
        btn_start.setEnabled(spotify_available)
        if not spotify_available:
            btn_start.setToolTip("Spotify not found in PATH")
        btn_start.clicked.connect(lambda: self._dialog_start_local(dialog, spotify_running, spotify_available))
        btn_layout.addWidget(btn_start)

        # Option 2: Use remote device
        btn_remote = QPushButton(f"Connect to another device ({len(remote_devices)} available)")
        btn_remote.setEnabled(len(remote_devices) > 0)
        if not remote_devices:
            btn_remote.setToolTip("No remote devices found")
        btn_remote.clicked.connect(lambda: self._dialog_use_remote(dialog, remote_devices))
        btn_layout.addWidget(btn_remote)

        # Option 3: Continue without music
        btn_skip = QPushButton("Continue without music")
        btn_skip.clicked.connect(lambda: self._dialog_skip_music(dialog))
        btn_layout.addWidget(btn_skip)

        layout.addLayout(btn_layout)

        # Remember choice checkbox
        from PyQt5.QtWidgets import QCheckBox
        self._remember_checkbox = QCheckBox("Remember my choice")
        layout.addWidget(self._remember_checkbox)

        dialog.setLayout(layout)
        dialog.exec_()

    def _dialog_start_local(self, dialog: "QDialog", spotify_running: bool, spotify_available: bool) -> None:
        """Handle 'Start local' from options dialog."""
        if self._remember_checkbox.isChecked():
            self.settings_manager.set_spotify_auto_start("start_local")
        dialog.accept()
        self._do_start_local_spotify(spotify_running, spotify_available)

    def _dialog_use_remote(self, dialog: "QDialog", remote_devices: list) -> None:
        """Handle 'Use remote' from options dialog."""
        if self._remember_checkbox.isChecked():
            self.settings_manager.set_spotify_auto_start("use_remote")
        dialog.accept()
        self._do_use_remote_spotify(remote_devices)

    def _dialog_skip_music(self, dialog: "QDialog") -> None:
        """Handle 'Continue without music' from options dialog."""
        if self._remember_checkbox.isChecked():
            self.settings_manager.set_spotify_auto_start("disabled")
        dialog.reject()
        self.immersive_status.set_message("Continuing without music", timeout_ms=3000)

    def _is_dark_mode_enabled(self) -> bool:
        """Check if dark mode should be enabled based on settings."""
        theme = self.settings_manager.get_theme()
        if theme == "dark":
            return True
        elif theme == "light":
            return False
        else:  # "system"
            return self._detect_system_dark_mode()

    def _detect_system_dark_mode(self) -> bool:
        """Detect if the system is using dark mode."""
        # This is called during init before palette may be set
        # Use external detection
        return detect_system_dark_mode()

    def _create_menu(self) -> None:
        """Create the application menu bar."""
        menubar = self.menuBar()

        # File menu (Ctrl+F, F underlined)
        file_menu = menubar.addMenu("&File")

        # Settings action (S underlined)
        settings_action = QAction("&Settings", self)
        settings_action.setShortcut("Ctrl+,")
        settings_action.triggered.connect(self._show_settings)
        file_menu.addAction(settings_action)

        file_menu.addSeparator()

        # Quit action (Q underlined)
        quit_action = QAction("&Quit", self)
        quit_action.setShortcut("Ctrl+Q")
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)

    def _show_settings(self) -> None:
        """Show the settings dialog."""
        dialog = SettingsDialog(self.settings_manager, self)
        dialog.exec_()

    def _detect_dark_mode(self) -> bool:
        """Detect if the system is using dark mode based on window background color."""
        palette = self.palette()
        bg_color = palette.color(palette.Window)
        # If background luminance is low, we're in dark mode
        luminance = (0.299 * bg_color.red() + 0.587 * bg_color.green() + 0.114 * bg_color.blue()) / 255
        return luminance < 0.5

    def _load_and_organize_configs(self) -> Dict[str, List[Dict[str, Any]]]:
        """Load all configs and organize by category."""
        all_configs = self.config_loader.discover_all()

        # Group by category
        organized = defaultdict(list)
        for config in all_configs:
            category = config.get("category", "special")
            organized[category].append(config)

        # Sort categories
        sorted_organized = {}
        for category in ["combat", "social", "exploration", "relaxation", "special", "hidden", "freesound"]:
            if category in organized:
                # Sort configs within category by name
                sorted_organized[category] = sorted(
                    organized[category],
                    key=lambda c: c["name"]
                )

        return sorted_organized

    def _build_url_to_config_mapping(self) -> None:
        """Build mapping from freesound URLs to config names for atmosphere tracking."""
        self.url_to_config.clear()
        for category, configs in self.configs.items():
            for config in configs:
                # Check if this config has a freesound URL as its sound file
                sound_file = config.get("engines", {}).get("sound", {}).get("file", "")
                if sound_file and "freesound.org" in sound_file:
                    self.url_to_config[sound_file] = config

    def _ensure_atmosphere_configs(self, mix: List[Dict[str, Any]]) -> bool:
        """
        Ensure individual configs exist for all freesound URLs in an atmosphere mix.

        Creates config files, loads them, creates buttons, and updates mappings.

        Args:
            mix: List of sound configurations with 'url' keys

        Returns:
            True if any new configs were created
        """
        from freesound_manager import FreesoundManager, is_freesound_url

        created_any = False
        freesound_manager = FreesoundManager()
        new_configs = []

        for sound_config in mix:
            url = sound_config.get("url", "")
            if not url or not is_freesound_url(url):
                continue

            # Check if config already exists for this URL
            if url in self.url_to_config:
                continue

            # Try to get metadata from FreesoundManager
            try:
                # get_sound returns (local_path, metadata) - uses cache if available
                _, metadata = freesound_manager.get_sound(url)

                # Create config file inline (same logic as EngineRunner._auto_create_freesound_config)
                sound_name = metadata.get("sound_name", "Unknown")
                creator = metadata.get("creator", "Unknown")
                sound_id = metadata.get("sound_id", "0")

                safe_name = sound_name.lower().replace(' ', '_').replace('-', '_')
                safe_name = ''.join(c for c in safe_name if c.isalnum() or c == '_')
                config_filename = f"freesound_{safe_name}_{sound_id}.yaml"
                config_path = Path("env_conf") / config_filename

                # Skip if config file already exists
                if not config_path.exists():
                    display_name = sound_name.replace('_', ' ')
                    config_content = f'''name: "{display_name}"
category: "freesound"
description: "Freesound by {creator}"
icon: "🔁"

metadata:
  tags: ["freesound", "downloaded", "{creator}", "loop"]
  intensity: "low"
  suitable_for: ["ambient", "atmosphere", "loop"]
  loop: true

engines:
  sound:
    enabled: true
    file: "{url}"
    loop: true

  spotify:
    enabled: false

  lights:
    enabled: false
'''
                    with open(config_path, 'w') as f:
                        f.write(config_content)

                # Load the new config
                try:
                    new_config = self.config_loader.load(config_filename)
                    new_configs.append(new_config)
                    created_any = True
                except Exception as e:
                    print(f"Warning: Could not load new config {config_filename}: {e}")

            except Exception as e:
                print(f"Warning: Could not create config for {url}: {e}")

        # Add new configs to our data structures and create buttons
        if new_configs:
            for config in new_configs:
                category = config.get("category", "freesound")
                # Add to configs dict
                if category not in self.configs:
                    self.configs[category] = []
                self.configs[category].append(config)

                # Add to url_to_config mapping
                sound_file = config.get("engines", {}).get("sound", {}).get("file", "")
                if sound_file:
                    self.url_to_config[sound_file] = config

                # Create button for the new config (no shortcut key for dynamically added)
                container, btn = self._create_button(config, "")
                name = config["name"]
                self.buttons[name] = btn

                # Add to the freesound tab - create it if it doesn't exist
                if "freesound" not in self.category_content_widgets:
                    # Create the freesound tab dynamically
                    tab_widget = QWidget()
                    layout = QGridLayout()
                    layout.setSpacing(10)
                    tab_widget.setLayout(layout)

                    # Add to category list and stack
                    item = QListWidgetItem("Freesound")
                    item.setSizeHint(QSize(0, 40))
                    self.category_list.addItem(item)
                    self.category_stack.addWidget(tab_widget)
                    self.category_content_widgets["freesound"] = tab_widget

                    # Update tab_configs
                    new_tab_index = self.category_list.count() - 1
                    self.tab_configs[new_tab_index] = []

                content = self.category_content_widgets["freesound"]
                # Find the grid layout
                if content.layout():
                    grid = content.layout()
                    count = grid.count()
                    cols = 4  # Match the column count from _create_category_tab
                    row = count // cols
                    col = count % cols
                    grid.addWidget(container, row, col)

        return created_any

    def _update_atmosphere_buttons(self, urls: List[str], active: bool) -> None:
        """Highlight or unhighlight buttons for atmosphere member sounds."""
        for url in urls:
            config = self.url_to_config.get(url)
            if config:
                config_name = config.get("name")
                if config_name and config_name in self.buttons:
                    btn = self.buttons[config_name]
                    if active:
                        btn.setStyleSheet(self.ATMOSPHERE_ACTIVE_STYLE)
                    else:
                        btn.setStyleSheet(self.INACTIVE_STYLE)
                    btn.update()  # Force visual refresh

    def _clear_atmosphere_buttons(self) -> None:
        """Clear all atmosphere button highlights."""
        for url in self.active_atmosphere_urls:
            config = self.url_to_config.get(url)
            if config:
                config_name = config.get("name")
                if config_name and config_name in self.buttons:
                    btn = self.buttons[config_name]
                    btn.setStyleSheet(self.INACTIVE_STYLE)
                    btn.update()  # Force visual refresh
        self.active_atmosphere_urls.clear()

    def _toggle_loop_sound(self, config: Dict[str, Any]) -> None:
        """Toggle a loop sound in/out of the atmosphere mix."""
        from engines import AtmosphereEngine, is_atmosphere_playing

        sound_url = config.get("engines", {}).get("sound", {}).get("file", "")
        if not sound_url:
            return

        config_name = config.get("name", "")

        if sound_url in self.active_atmosphere_urls:
            # Sound is playing - fade it out and remove from atmosphere
            atmosphere_engine = AtmosphereEngine()
            atmosphere_engine.stop_single(sound_url, fade_out=True)
            self.active_atmosphere_urls.discard(sound_url)
            if config_name in self.buttons:
                self.buttons[config_name].setStyleSheet(self.INACTIVE_STYLE)
            self.immersive_status.set_message(f"Removed: {config_name}", timeout_ms=2000)

            # Update status bar music display
            if self.active_atmosphere_urls:
                # Get display names for remaining sounds
                remaining_names = []
                for url in self.active_atmosphere_urls:
                    cfg = self.url_to_config.get(url)
                    if cfg:
                        remaining_names.append(cfg.get("name", "Unknown"))
                self.immersive_status.set_music(" + ".join(remaining_names), source="atmosphere")
            else:
                self.immersive_status.clear_music()
        else:
            # Sound is not playing - fade it in and add to atmosphere
            atmosphere_engine = AtmosphereEngine()
            if atmosphere_engine.start_single(sound_url, volume=100, fade_in=True):
                self.active_atmosphere_urls.add(sound_url)
                if config_name in self.buttons:
                    self.buttons[config_name].setStyleSheet(self.ATMOSPHERE_ACTIVE_STYLE)
                self.immersive_status.set_message(f"Added: {config_name}", timeout_ms=2000)

                # Update status bar music display
                all_names = []
                for url in self.active_atmosphere_urls:
                    cfg = self.url_to_config.get(url)
                    if cfg:
                        all_names.append(cfg.get("name", "Unknown"))
                self.immersive_status.set_music(" + ".join(all_names), source="atmosphere")
            else:
                self.immersive_status.set_message(f"Failed to add: {config_name}", timeout_ms=3000)

    def _create_ui(self) -> None:
        """Create the main UI layout with tabs on left side."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(5, 5, 5, 5)

        # Search bar at top (fixed height container)
        search_container = QWidget()
        search_container.setFixedHeight(65)
        search_layout = QHBoxLayout(search_container)
        search_layout.setContentsMargins(0, 0, 0, 0)
        self.search_bar = FuzzySearchBar(self.configs)
        self.search_bar.environment_selected.connect(self._on_search_selected)
        # Only focus search bar when clicked or via Ctrl+L, not by default
        self.search_bar.setFocusPolicy(Qt.ClickFocus)
        if self.is_dark_mode:
            self.search_bar.setStyleSheet("""
                QLineEdit {
                    padding: 6px 10px;
                    border: 1px solid #555;
                    border-radius: 4px;
                    background-color: #2d2d2d;
                    color: white;
                }
                QLineEdit:focus {
                    border: 2px solid #4CAF50;
                }
            """)
        else:
            self.search_bar.setStyleSheet("""
                QLineEdit {
                    padding: 6px 10px;
                    border: 1px solid #ccc;
                    border-radius: 4px;
                }
                QLineEdit:focus {
                    border: 2px solid #4CAF50;
                }
            """)
        search_label = QLabel("🔍")
        search_label.setStyleSheet("font-size: 16px;")
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_bar)
        search_layout.addStretch()

        # Now Playing widget on the right
        self.now_playing = NowPlayingWidget()
        search_layout.addWidget(self.now_playing)

        main_layout.addWidget(search_container)

        # Create splitter for left tabs and right content
        self.splitter = QSplitter(Qt.Horizontal)

        # Left side: category list (15% width)
        self.category_list = QListWidget()
        self.category_list.setMinimumWidth(120)
        self.category_list.setMaximumWidth(200)

        # Style based on dark mode
        if self.is_dark_mode:
            self.category_list.setStyleSheet("""
                QListWidget {
                    font-size: 14px;
                    padding: 5px;
                    background-color: #2d2d2d;
                    border: none;
                }
                QListWidget::item {
                    padding: 10px 8px;
                    border-radius: 4px;
                    margin: 2px 4px;
                    color: white;
                }
                QListWidget::item:selected {
                    background-color: #4CAF50;
                    color: white;
                }
                QListWidget::item:hover:!selected {
                    background-color: #404040;
                }
            """)
        else:
            self.category_list.setStyleSheet("""
                QListWidget {
                    font-size: 14px;
                    padding: 5px;
                    border: none;
                }
                QListWidget::item {
                    padding: 10px 8px;
                    border-radius: 4px;
                    margin: 2px 4px;
                }
                QListWidget::item:selected {
                    background-color: #4CAF50;
                    color: white;
                }
                QListWidget::item:hover:!selected {
                    background-color: #e0e0e0;
                }
            """)

        # Right side: stacked widget for category content
        self.category_stack = QStackedWidget()

        # Track category content widgets for dynamic button addition
        self.category_content_widgets = {}

        # Add categories
        tab_index = 0
        for category, configs in self.configs.items():
            # Skip hidden category
            if category == "hidden":
                continue
            # Add to list
            item = QListWidgetItem(category.capitalize())
            item.setSizeHint(QSize(0, 40))
            self.category_list.addItem(item)

            # Add content page
            tab_widget = self._create_category_tab(category, configs)
            self.category_stack.addWidget(tab_widget)
            self.category_content_widgets[category] = tab_widget
            self.tab_configs[tab_index] = configs
            tab_index += 1

        # Connect list selection to stack
        self.category_list.currentRowChanged.connect(self._on_tab_changed)
        self.category_list.currentRowChanged.connect(self.category_stack.setCurrentIndex)

        # Select first category
        self.category_list.setCurrentRow(0)

        # Add to splitter
        self.splitter.addWidget(self.category_list)
        self.splitter.addWidget(self.category_stack)

        # Set initial sizes (15% for list, 85% for content)
        self.splitter.setSizes([150, 850])
        self.splitter.setStretchFactor(0, 0)  # List doesn't stretch
        self.splitter.setStretchFactor(1, 1)  # Content stretches

        main_layout.addWidget(self.splitter)

        # Add control buttons (Stop buttons)
        control_layout = QHBoxLayout()

        self.stop_button = QPushButton("STOP LIGHTS")
        self.stop_button.setMinimumHeight(40)
        self.stop_button.setStyleSheet(self.STOP_STYLE)
        self.stop_button.clicked.connect(self._stop_current)
        self.stop_button.setEnabled(False)
        self.stop_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        control_layout.addWidget(self.stop_button)

        # Stop Sound button with shortcut badge
        stop_sound_container = QWidget()
        stop_sound_container.setMinimumHeight(45)
        stop_sound_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self.stop_sound_button = QPushButton("STOP SOUND")
        self.stop_sound_button.setMinimumHeight(40)
        self.stop_sound_button.setStyleSheet(
            "background-color: #FF9800; color: white; font-weight: bold; font-size: 12px;"
        )
        self.stop_sound_button.clicked.connect(self._stop_sounds)
        self.stop_sound_button.setParent(stop_sound_container)

        # Shortcut badge showing spacebar
        space_badge = OutlinedLabel("␣")
        pastel_color = self._generate_pastel_color()
        space_badge.setStyleSheet(
            f"background-color: {pastel_color}; border: 1px solid gray; border-radius: 3px;"
        )
        space_badge.setFixedSize(29, 25)
        space_badge.setParent(stop_sound_container)

        # Position elements using resize event
        def resize_stop_sound(event):
            w, h = stop_sound_container.width(), stop_sound_container.height()
            self.stop_sound_button.setGeometry(0, 0, w, h)
            space_badge.move(5, (h - 25) // 2)
            space_badge.raise_()
        stop_sound_container.resizeEvent = resize_stop_sound

        control_layout.addWidget(stop_sound_container)

        # Stop Atmosphere button (stops both Spotify and atmosphere sounds)
        self.stop_atmosphere_button = QPushButton("STOP ATMOSPHERE")
        self.stop_atmosphere_button.setMinimumHeight(40)
        self.stop_atmosphere_button.setStyleSheet(
            "background-color: #1DB954; color: white; font-weight: bold; font-size: 12px;"
        )
        self.stop_atmosphere_button.clicked.connect(self._stop_atmosphere_and_spotify)
        self.stop_atmosphere_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        control_layout.addWidget(self.stop_atmosphere_button)

        # Equal width for all three stop buttons
        control_layout.setStretch(0, 1)
        control_layout.setStretch(1, 1)
        control_layout.setStretch(2, 1)

        main_layout.addLayout(control_layout)

        central_widget.setLayout(main_layout)

        # Set focus to main window so keyboard shortcuts work immediately
        self.setFocus()

        # Status bar - use our immersive status bar
        self.setStatusBar(self.immersive_status.get_status_bar())

    def _create_category_tab(self, category: str, configs: List[Dict[str, Any]]) -> QWidget:
        """Create a tab widget for a category."""
        tab_widget = QWidget()
        layout = QGridLayout()
        layout.setSpacing(10)

        # Create buttons in a grid (4 columns)
        for idx, config in enumerate(configs):
            row = idx // 4
            col = idx % 4

            # Shortcut key based on position in this tab
            shortcut_key = self.KEYS[idx] if idx < len(self.KEYS) else ""

            # Create button widget (returns container and button)
            container, btn = self._create_button(config, shortcut_key)
            layout.addWidget(container, row, col)

            # Store button reference for styling
            self.buttons[config["name"]] = btn

        tab_widget.setLayout(layout)
        return tab_widget

    def _setup_tab_shortcuts(self) -> None:
        """Setup tab navigation and per-tab button shortcuts."""
        # Tab navigation: Ctrl+PgUp/PgDn
        next_tab = QShortcut(QKeySequence("Ctrl+PgDown"), self)
        next_tab.activated.connect(lambda: self.category_list.setCurrentRow(
            (self.category_list.currentRow() + 1) % self.category_list.count()
        ))

        prev_tab = QShortcut(QKeySequence("Ctrl+PgUp"), self)
        prev_tab.activated.connect(lambda: self.category_list.setCurrentRow(
            (self.category_list.currentRow() - 1) % self.category_list.count()
        ))

        # Spacebar to stop sounds
        stop_sound_shortcut = QShortcut(QKeySequence(Qt.Key_Space), self)
        stop_sound_shortcut.activated.connect(self._stop_sounds)

        # Ctrl+L to focus search bar
        search_shortcut = QShortcut(QKeySequence("Ctrl+L"), self)
        search_shortcut.activated.connect(self._focus_search)

        # Escape to clear search and unfocus
        escape_shortcut = QShortcut(QKeySequence(Qt.Key_Escape), self)
        escape_shortcut.activated.connect(self._clear_search)

        # Setup initial shortcuts for first tab
        self._update_shortcuts_for_tab(0)

    def _on_tab_changed(self, index: int) -> None:
        """Handle tab change - remap keyboard shortcuts."""
        self._update_shortcuts_for_tab(index)

    def _update_shortcuts_for_tab(self, tab_index: int) -> None:
        """Update keyboard shortcuts to point to current tab's buttons."""
        # Clear existing shortcuts
        for shortcut in self.shortcuts:
            shortcut.setEnabled(False)
            shortcut.deleteLater()
        self.shortcuts.clear()

        # Get configs for this tab
        configs = self.tab_configs.get(tab_index, [])

        # Create shortcuts for each button in this tab
        for idx, config in enumerate(configs):
            if idx >= len(self.KEYS):
                break
            key = self.KEYS[idx]
            shortcut = QShortcut(QKeySequence(key), self)

            # Check if this is a loop-capable sound
            is_loop = config.get("metadata", {}).get("loop", False) or \
                      config.get("engines", {}).get("sound", {}).get("loop", False)

            if is_loop:
                shortcut.activated.connect(
                    lambda c=config: self._toggle_loop_sound(c)
                )
            else:
                shortcut.activated.connect(
                    lambda c=config: self._start_environment(c)
                )
            self.shortcuts.append(shortcut)

    def _generate_pastel_color(self) -> str:
        """Generate a random pastel color as hex string."""
        # Pastel colors have high lightness - RGB values between 180-255
        r = random.randint(180, 255)
        g = random.randint(180, 255)
        b = random.randint(180, 255)
        return f"#{r:02x}{g:02x}{b:02x}"

    def _create_button(self, config: Dict[str, Any], shortcut_key: str):
        """Create a button widget with emoji indicators below.

        Returns:
            Tuple of (container_widget, button) - container for layout, button for styling
        """
        name = config["name"]
        description = config.get("description", "")

        # Determine which engines are enabled
        sound_enabled = config.get("engines", {}).get("sound", {}).get("enabled", False)
        spotify_enabled = config.get("engines", {}).get("spotify", {}).get("enabled", False)
        atmosphere_enabled = config.get("engines", {}).get("atmosphere", {}).get("enabled", False)
        lights_enabled = config.get("engines", {}).get("lights", {}).get("enabled", False)
        # Check if this is a loop-capable sound (can be mixed into atmosphere)
        is_loop = config.get("metadata", {}).get("loop", False) or config.get("engines", {}).get("sound", {}).get("loop", False)

        # Get optional icon emoji from config
        icon_emoji = config.get("icon", "")

        # Button shows only the name (larger font) with background icon
        btn = IconButton(name, icon_emoji)
        btn.setStyleSheet(self.INACTIVE_STYLE)
        btn.setToolTip(description)
        # Loop sounds toggle in/out of atmosphere; other configs start environment
        if is_loop:
            btn.clicked.connect(lambda checked=False, c=config: self._toggle_loop_sound(c))
        else:
            btn.clicked.connect(lambda checked=False, c=config: self._start_environment(c))

        # Create shortcut key badge (top-left corner) with outlined text
        shortcut_label = None
        if shortcut_key:
            shortcut_label = OutlinedLabel(shortcut_key.upper())
            pastel_color = self._generate_pastel_color()
            shortcut_label.setStyleSheet(
                f"background-color: {pastel_color}; border: 1px solid gray; "
                f"border-radius: 3px;"
            )
            # Size is set dynamically in ButtonContainer.resizeEvent

        # Create description label (below emoji row)
        desc_label = None
        if description:
            desc_label = QLabel(description)
            desc_label.setAlignment(Qt.AlignCenter)
            desc_label.setWordWrap(True)
            desc_style = self.DESC_STYLE_DARK if self.is_dark_mode else self.DESC_STYLE
            desc_label.setStyleSheet(desc_style)

        # Create emoji indicator row (will be parented to container)
        emoji_row = QWidget()
        emoji_layout = QHBoxLayout()
        emoji_layout.setContentsMargins(0, 0, 0, 0)
        emoji_layout.setSpacing(4)
        emoji_layout.addStretch()

        # Pastel colors for each indicator
        is_sound_only = sound_enabled and not spotify_enabled and not atmosphere_enabled and not lights_enabled

        if sound_enabled:
            sound_emoji = "📢" if is_sound_only else "🔊"
            sound_label = QLabel(sound_emoji)
            sound_label.setFixedHeight(18)
            sound_label.setStyleSheet(
                "background-color: #FFCBA4; padding: 0px 6px; border: 1px solid gray; border-radius: 3px; font-size: 14px; color: black;"
            )
            sound_label.setAlignment(Qt.AlignCenter)
            emoji_layout.addWidget(sound_label)

        if spotify_enabled:
            spotify_label = QLabel("🎵")
            spotify_label.setFixedHeight(18)
            spotify_label.setStyleSheet(
                "background-color: #B4F0A8; padding: 0px 6px; border: 1px solid gray; border-radius: 3px; font-size: 14px; color: black;"
            )
            spotify_label.setAlignment(Qt.AlignCenter)
            emoji_layout.addWidget(spotify_label)

        if atmosphere_enabled:
            atmosphere_label = QLabel("🌊")
            atmosphere_label.setFixedHeight(18)
            atmosphere_label.setStyleSheet(
                "background-color: #B4E8F0; padding: 0px 6px; border: 1px solid gray; border-radius: 3px; font-size: 14px; color: black;"
            )
            atmosphere_label.setAlignment(Qt.AlignCenter)
            emoji_layout.addWidget(atmosphere_label)

        if lights_enabled:
            lights_label = QLabel("💡")
            lights_label.setFixedHeight(18)
            lights_label.setStyleSheet(
                "background-color: #FFF9B0; padding: 0px 6px; border: 1px solid gray; border-radius: 3px; font-size: 14px; color: black;"
            )
            lights_label.setAlignment(Qt.AlignCenter)
            emoji_layout.addWidget(lights_label)

        if is_loop:
            loop_label = QLabel("🔁")
            loop_label.setFixedHeight(18)
            loop_label.setStyleSheet(
                "background-color: #E0B4F0; padding: 0px 6px; border: 1px solid gray; border-radius: 3px; font-size: 14px; color: black;"
            )
            loop_label.setAlignment(Qt.AlignCenter)
            emoji_layout.addWidget(loop_label)

        emoji_layout.addStretch()
        emoji_row.setLayout(emoji_layout)

        # Create container that handles resizing with overlap
        container = ButtonContainer(btn, emoji_row, shortcut_label, desc_label)

        return container, btn

    def _start_environment(self, config: Dict[str, Any]) -> None:
        """Start an environment."""
        # Clear pending search button since we're starting an environment
        self._pending_search_button = None

        has_lights = config["engines"]["lights"]["enabled"]
        has_spotify = config["engines"].get("spotify", {}).get("enabled", False)
        has_atmosphere = config["engines"].get("atmosphere", {}).get("enabled", False)

        # Only stop lights runner if new config has lights
        if has_lights and self.lights_runner is not None:
            self._stop_lights()

        # Stop any currently playing sounds when starting an environment with lights
        if has_lights:
            stop_all_sounds()
            self.immersive_status.clear_sound()

        # Handle atmosphere/spotify switching
        # Stop atmosphere when switching to a Spotify environment
        if has_spotify:
            stop_all_atmosphere()

        # Stop Spotify when switching to an atmosphere environment
        if has_atmosphere:
            try:
                SpotifyEngine().stop()
            except Exception:
                pass  # Spotify may not be configured
            # Also stop any previous atmosphere
            stop_all_atmosphere()
            # Clear previous atmosphere button highlights
            self._clear_atmosphere_buttons()

            # Extract atmosphere URLs and ensure configs exist for them
            atmosphere_mix = config.get("engines", {}).get("atmosphere", {}).get("mix", [])
            atmosphere_urls = [item.get("url", "") for item in atmosphere_mix if item.get("url")]

            # Create configs for any new freesound URLs in the mix
            # This also creates buttons and updates url_to_config mapping
            self._ensure_atmosphere_configs(atmosphere_mix)

            # Rebuild mapping to ensure all URLs are included
            # (handles case where configs existed but weren't in mapping)
            self._build_url_to_config_mapping()

            self.active_atmosphere_urls = set(atmosphere_urls)
            self._update_atmosphere_buttons(atmosphere_urls, active=True)
        elif has_spotify:
            # Clear atmosphere buttons when switching to Spotify
            self._clear_atmosphere_buttons()

        # Get the icon for this config (for NowPlayingWidget)
        config_icon = config.get("icon", "💡")

        # Create and start runner
        try:
            runner = EngineRunner(config)
            runner.error_occurred.connect(self._on_error)
            runner.status_update.connect(self._on_status_update)
            runner.finished.connect(lambda: self._on_runner_finished(runner))
            runner.sound_finished.connect(lambda: self._on_sound_finished(config["name"]))
            runner.spotify_no_device.connect(self._handle_spotify_no_device)
            # Connect to immersive status bar
            runner.sound_started.connect(self.immersive_status.on_sound_started)
            runner.sound_done.connect(self.immersive_status.on_sound_finished)
            runner.music_started.connect(self.immersive_status.on_music_started)
            runner.atmosphere_started.connect(self.immersive_status.on_atmosphere_started)
            runner.lights_started.connect(self.immersive_status.on_lights_started)
            # Connect to NowPlayingWidget
            runner.download_started.connect(lambda _: self.now_playing.set_downloading(True))
            runner.download_finished.connect(lambda: self.now_playing.set_downloading(False))
            config_name = config["name"]
            runner.sound_started.connect(lambda _, icon=config_icon, name=config_name: self.now_playing.set_sound(True, icon, name))
            runner.sound_done.connect(lambda: self.now_playing.set_sound(False))
            if has_lights:
                runner.lights_started.connect(lambda _, icon=config_icon, name=config_name: self.now_playing.set_lights(icon, name))
            runner.start()

            self.current_runner = runner
            self.current_config_name = config["name"]

            if has_lights:
                # This is a lights config - track it and highlight button
                self.lights_runner = runner
                self.lights_config_name = config["name"]
                self._update_active_button(config["name"])
                self.stop_button.setEnabled(True)
            else:
                # Sound-only config - highlight it while playing
                self._update_active_button(config["name"])

        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to start {config['name']}:\n{str(e)}"
            )
            self.immersive_status.set_message("Error starting environment", timeout_ms=5000)

    def _stop_lights(self) -> None:
        """Stop the currently running lights and set bulbs to warm white."""
        if self.lights_runner is not None:
            old_runner = self.lights_runner
            old_runner.stop()
            # Keep reference until thread finishes to avoid QThread crash
            self._old_runners.append(old_runner)
            old_runner.finished.connect(lambda: self._cleanup_old_runner(old_runner))
            self.lights_runner = None
            self.lights_config_name = None
            self.immersive_status.clear_lights()
            self.now_playing.clear()

        # Set all lights to warm white
        self._set_lights_warm_white()

    def _set_lights_warm_white(self) -> None:
        """Set all configured lights to soft warm white at full brightness."""
        import asyncio
        from pywizlight import wizlight, PilotBuilder

        wizbulb_config = WizBulbConfigManager()
        if wizbulb_config.is_configured():
            all_ips = []
            for group in ["backdrop_bulbs", "overhead_bulbs", "battlefield_bulbs"]:
                ips = wizbulb_config.get(group, "").split()
                all_ips.extend([ip.strip() for ip in ips if ip.strip()])

            if all_ips:
                async def set_lights_soft_white():
                    # Soft warm white at max brightness: ~2700K equivalent
                    pilot = PilotBuilder(rgb=(255, 244, 229), brightness=255)
                    for ip in all_ips:
                        try:
                            bulb = wizlight(ip)
                            await bulb.turn_on(pilot)
                        except:
                            pass  # Ignore unreachable bulbs

                try:
                    asyncio.run(set_lights_soft_white())
                except:
                    pass

    def _stop_current(self) -> None:
        """Stop all running environments (lights)."""
        self._stop_lights()
        self.current_runner = None
        self.current_config_name = None
        self._reset_button_styles()
        self.stop_button.setEnabled(False)
        self.now_playing.clear()

    def _stop_sounds(self) -> None:
        """Stop all playing sound effects."""
        stopped = stop_all_sounds()
        self.immersive_status.clear_sound()
        if stopped > 0:
            self.immersive_status.set_message(f"Stopped {stopped} sound(s)", timeout_ms=3000)
        else:
            self.immersive_status.set_message("No sounds playing", timeout_ms=3000)

    def _stop_atmosphere_and_spotify(self) -> None:
        """Stop both Spotify and atmosphere playback."""
        stopped_any = False

        # Stop atmosphere sounds
        atmosphere_stopped = stop_all_atmosphere()
        if atmosphere_stopped > 0:
            stopped_any = True
            # Clear atmosphere button highlights
            self._clear_atmosphere_buttons()

        # Stop Spotify
        try:
            spotify_engine = SpotifyEngine()
            if spotify_engine.stop():
                stopped_any = True
        except Exception:
            pass  # Spotify may not be configured

        self.immersive_status.clear_music()
        if stopped_any:
            self.immersive_status.set_message("Atmosphere stopped", timeout_ms=3000)
        else:
            self.immersive_status.set_message("No atmosphere playing", timeout_ms=3000)

    def _focus_search(self) -> None:
        """Focus the search bar."""
        self.search_bar.setFocus()
        self.search_bar.selectAll()

    def _clear_search(self) -> None:
        """Clear and unfocus search bar."""
        self.search_bar.clear()
        self.search_bar.clearFocus()
        self.setFocus()

    def _on_search_selected(self, config_name: str, category_index: int) -> None:
        """Handle environment selection from search bar."""
        # Switch to the correct category
        if category_index < self.category_list.count():
            self.category_list.setCurrentRow(category_index)
            self.category_stack.setCurrentIndex(category_index)

        # Find and pulse the button
        if config_name in self.buttons:
            btn = self.buttons[config_name]
            self._pulse_button(btn)
            # Store pending button so Enter key can trigger it
            # Delay activation to avoid Enter from search selection also triggering the button
            self._pending_search_button = None  # Clear first
            QTimer.singleShot(300, lambda: self._set_pending_button(btn, config_name))

    def _set_pending_button(self, btn: QPushButton, config_name: str) -> None:
        """Set the pending search button after a delay."""
        self._pending_search_button = btn
        self.immersive_status.set_message(f"Found: {config_name} (press Enter to activate)", timeout_ms=5000)

    def _pulse_button(self, btn: QPushButton) -> None:
        """Make a button pulse with a green border glow for 3 seconds."""
        # Find the config name for this button
        btn_config_name = None
        for name, b in self.buttons.items():
            if b is btn:
                btn_config_name = name
                break

        # Pulse styles - border expands with color getting brighter, 3 quick pulses
        # Border grows 1→6→1, color goes dark→bright→dark, radius shrinks as border grows
        single_pulse = [
            "border: 1px solid #004400; border-radius: 3px; padding: 8px; font-size: 17px;",
            "border: 2px solid #005500; border-radius: 3px; padding: 8px; font-size: 17px;",
            "border: 3px solid #007700; border-radius: 2px; padding: 8px; font-size: 17px;",
            "border: 4px solid #009900; border-radius: 2px; padding: 8px; font-size: 17px;",
            "border: 5px solid #00CC00; border-radius: 1px; padding: 8px; font-size: 17px;",
            "border: 6px solid #00FF00; border-radius: 1px; padding: 8px; font-size: 17px;",
            "border: 5px solid #00CC00; border-radius: 1px; padding: 8px; font-size: 17px;",
            "border: 4px solid #009900; border-radius: 2px; padding: 8px; font-size: 17px;",
            "border: 3px solid #007700; border-radius: 2px; padding: 8px; font-size: 17px;",
            "border: 2px solid #005500; border-radius: 3px; padding: 8px; font-size: 17px;",
        ]
        # Repeat 4 times
        pulse_styles = single_pulse * 4

        # Create pulse animation using timers
        pulse_count = [0]
        total_pulses = len(pulse_styles)

        def do_pulse():
            if pulse_count[0] < total_pulses:
                btn.setStyleSheet(pulse_styles[pulse_count[0]])
                pulse_count[0] += 1
                QTimer.singleShot(20, do_pulse)  # ~0.6 seconds total for 3 pulses
            else:
                # Check if this button is now the active lights button
                if btn_config_name and btn_config_name == self.lights_config_name:
                    btn.setStyleSheet(self.ACTIVE_STYLE)
                else:
                    btn.setStyleSheet(self.INACTIVE_STYLE)

        do_pulse()

    def _cleanup_old_runner(self, runner: EngineRunner) -> None:
        """Remove finished runner from old runners list."""
        if runner in self._old_runners:
            self._old_runners.remove(runner)

    def _on_error(self, error_msg: str) -> None:
        """Handle error from engine runner."""
        QMessageBox.warning(self, "Engine Error", error_msg)
        self.immersive_status.set_message(f"Error: {error_msg}", timeout_ms=5000)

    def _on_status_update(self, status: str) -> None:
        """Handle status update from engine runner."""
        # Show status message temporarily (auto-clears after 3 seconds)
        self.immersive_status.set_message(status, timeout_ms=3000)

    def _on_sound_finished(self, sound_name: str) -> None:
        """Handle sound-only config finishing."""
        self.immersive_status.clear_sound()
        if self.lights_config_name:
            # Re-highlight the active lights button
            self._update_active_button(self.lights_config_name)
        else:
            self._reset_button_styles()

    def _on_runner_finished(self, runner: EngineRunner) -> None:
        """Handle runner thread finishing."""
        # Only update status if this was the lights runner
        if runner == self.lights_runner:
            self.immersive_status.clear_lights()
            self.lights_runner = None
            self.lights_config_name = None
            self._reset_button_styles()
            self.stop_button.setEnabled(False)

    def _update_active_button(self, active_name: str) -> None:
        """Highlight the active lights button, preserving atmosphere button styles."""
        # Build set of active atmosphere button names
        atmosphere_button_names = set()
        for url in self.active_atmosphere_urls:
            cfg = self.url_to_config.get(url)
            if cfg:
                atmosphere_button_names.add(cfg.get("name"))

        for name, btn in self.buttons.items():
            if name == active_name:
                btn.setStyleSheet(self.ACTIVE_STYLE)
            elif name in atmosphere_button_names:
                # Keep atmosphere members blue
                btn.setStyleSheet(self.ATMOSPHERE_ACTIVE_STYLE)
            else:
                btn.setStyleSheet(self.INACTIVE_STYLE)

    def _reset_button_styles(self) -> None:
        """Reset all buttons to inactive state."""
        for btn in self.buttons.values():
            btn.setStyleSheet(self.INACTIVE_STYLE)

    def keyPressEvent(self, event) -> None:
        """Handle key press events."""
        # Enter triggers pending search result button
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            if self._pending_search_button is not None:
                self._pending_search_button.click()
                self._pending_search_button = None
                return
        super().keyPressEvent(event)

    def closeEvent(self, event) -> None:
        """Handle window close event."""
        if self.lights_runner is not None and self.lights_runner.running:
            reply = QMessageBox.question(
                self,
                "Confirm Exit",
                f"Lights '{self.lights_config_name}' are running.\n\nStop and exit?",
                QMessageBox.Yes | QMessageBox.No,
            )

            if reply == QMessageBox.Yes:
                # On exit, actually wait for cleanup
                self.lights_runner.running = False
                self.lights_runner.wait(2000)
                self._cleanup_on_exit()
                event.accept()
            else:
                event.ignore()
        else:
            self._cleanup_on_exit()
            event.accept()

    def _cleanup_on_exit(self) -> None:
        """Cleanup actions when exiting the app."""
        # Stop Spotify playback
        try:
            engine = SpotifyEngine()
            engine.stop()
            self.immersive_status.clear_music()
        except:
            pass  # Spotify may not be configured

        # Stop atmosphere sounds
        try:
            stop_all_atmosphere(fade_out=False)  # No fade on exit, just stop
        except:
            pass

        # Set all lights to soft white
        self._set_lights_warm_white()


def detect_system_dark_mode() -> bool:
    """Detect if the system is using dark mode."""
    import subprocess
    import os

    # Check Linux GNOME/GTK dark mode
    if os.environ.get("XDG_CURRENT_DESKTOP"):
        try:
            result = subprocess.run(
                ["gsettings", "get", "org.gnome.desktop.interface", "color-scheme"],
                capture_output=True, text=True, timeout=1
            )
            if "dark" in result.stdout.lower():
                return True
        except (subprocess.SubprocessError, FileNotFoundError):
            pass

        # Try GTK theme name as fallback
        try:
            result = subprocess.run(
                ["gsettings", "get", "org.gnome.desktop.interface", "gtk-theme"],
                capture_output=True, text=True, timeout=1
            )
            if "dark" in result.stdout.lower():
                return True
        except (subprocess.SubprocessError, FileNotFoundError):
            pass

    # Check KDE dark mode
    kde_globals = Path.home() / ".config" / "kdeglobals"
    if kde_globals.exists():
        try:
            content = kde_globals.read_text()
            if "ColorScheme" in content and "Dark" in content:
                return True
        except Exception:
            pass

    return False


def apply_dark_palette(app: QApplication) -> None:
    """Apply a dark color palette to the application."""
    dark_palette = QPalette()

    # Base colors
    dark_palette.setColor(QPalette.Window, QColor(53, 53, 53))
    dark_palette.setColor(QPalette.WindowText, Qt.white)
    dark_palette.setColor(QPalette.Base, QColor(25, 25, 25))
    dark_palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
    dark_palette.setColor(QPalette.ToolTipBase, Qt.white)
    dark_palette.setColor(QPalette.ToolTipText, Qt.white)
    dark_palette.setColor(QPalette.Text, Qt.white)
    dark_palette.setColor(QPalette.Button, QColor(53, 53, 53))
    dark_palette.setColor(QPalette.ButtonText, Qt.white)
    dark_palette.setColor(QPalette.BrightText, Qt.red)
    dark_palette.setColor(QPalette.Link, QColor(42, 130, 218))
    dark_palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
    dark_palette.setColor(QPalette.HighlightedText, Qt.black)

    # Disabled colors
    dark_palette.setColor(QPalette.Disabled, QPalette.WindowText, QColor(127, 127, 127))
    dark_palette.setColor(QPalette.Disabled, QPalette.Text, QColor(127, 127, 127))
    dark_palette.setColor(QPalette.Disabled, QPalette.ButtonText, QColor(127, 127, 127))

    app.setPalette(dark_palette)


def main():
    """Entry point for the application."""
    app = QApplication(sys.argv)

    # Use Fusion style for consistent cross-platform appearance
    app.setStyle(QStyleFactory.create("Fusion"))

    # Load settings
    settings_manager = SettingsManager()

    # Apply theme based on settings
    theme = settings_manager.get_theme()
    if theme == "dark":
        apply_dark_palette(app)
    elif theme == "system" and detect_system_dark_mode():
        apply_dark_palette(app)
    # else: light mode, use default palette

    launcher = EnvironmentLauncher(settings_manager)
    launcher.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
