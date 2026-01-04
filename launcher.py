#!/usr/bin/env python3
"""
Immerse Yourself Environment Launcher
A PyQt5 GUI for managing ambient environment configs with Spotify and smart lights.
"""

import sys
import asyncio
import threading
import random
from pathlib import Path
from typing import List, Dict, Optional, Any
from collections import defaultdict

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QGridLayout, QPushButton,
    QStatusBar, QMessageBox, QVBoxLayout, QTabWidget, QHBoxLayout,
    QShortcut, QLabel, QFrame, QSizePolicy, QStyleFactory
)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt5.QtGui import QKeySequence, QPalette, QColor, QPainter, QPen, QFont

from config_loader import ConfigLoader
from engines import SoundEngine, SpotifyEngine, LightsEngine


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

        # Get the font and text rect
        font = self.font()
        font.setBold(True)
        font.setPointSize(12)
        painter.setFont(font)

        # Calculate centered position
        rect = self.rect()
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
        # Shortcut label in top-left, overlapping button
        if self.shortcut_label:
            self.shortcut_label.setGeometry(5, 5, 33, 29)
            self.shortcut_label.raise_()
        # Description below emoji row
        if self.desc_label:
            self.desc_label.setGeometry(10, btn_height + 5, w - 20, desc_height)
        super().resizeEvent(event)


class EngineRunner(QThread):
    """Background thread for running async engines."""

    error_occurred = pyqtSignal(str)
    status_update = pyqtSignal(str)
    sound_finished = pyqtSignal()  # Signal when sound-only config finishes

    def __init__(self, config: Dict[str, Any]):
        super().__init__()
        self.config = config
        self.lights_engine: Optional[LightsEngine] = None
        self.running = False
        self.has_lights = config["engines"]["lights"]["enabled"]
        self._sound_done_event = threading.Event()

    def run(self):
        """Run the engines based on configuration."""
        try:
            self.running = True

            # Sound engine (non-blocking, fire and forget)
            if self.config["engines"]["sound"]["enabled"]:
                sound_file = self.config["engines"]["sound"]["file"]
                self.status_update.emit(f"Playing sound: {sound_file}")
                sound_engine = SoundEngine()
                # For sound-only configs, use callback to signal when done
                if not self.has_lights:
                    sound_engine.play_async(sound_file, on_complete=self._on_sound_complete)
                else:
                    sound_engine.play_async(sound_file)

            # Spotify engine (synchronous)
            if self.config["engines"]["spotify"]["enabled"]:
                context_uri = self.config["engines"]["spotify"]["context_uri"]
                self.status_update.emit(f"Starting Spotify...")
                try:
                    spotify_engine = SpotifyEngine()
                    spotify_engine.play_context(context_uri)
                    self.status_update.emit("Spotify playback started")
                except Exception as e:
                    self.error_occurred.emit(f"Spotify error: {str(e)}")

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

    def _on_sound_complete(self):
        """Called when sound-only playback completes."""
        self._sound_done_event.set()
        self.sound_finished.emit()

    async def _run_lights(self):
        """Run the lights engine asynchronously."""
        self.lights_engine = LightsEngine()
        animation_config = self.config["engines"]["lights"]["animation"]

        await self.lights_engine.start(animation_config)
        self.status_update.emit("Light animation running")

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
    INACTIVE_STYLE = "padding: 8px; font-size: 17px;"
    STOP_STYLE = "background-color: #f44336; color: white; font-weight: bold; font-size: 12px;"
    DESC_STYLE = "font-size: 11px; color: #666; padding: 2px 4px; border: 1px solid #ccc; border-radius: 3px; background-color: #fafafa;"
    DESC_STYLE_DARK = "font-size: 11px; color: #aaa; padding: 2px 4px; border: 1px solid #555; border-radius: 3px; background-color: #2a2a2a;"

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Immerse Yourself - Environment Launcher")
        self.setGeometry(100, 100, 1000, 600)

        # Detect dark mode from system palette
        self.is_dark_mode = self._detect_dark_mode()

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

        # Create UI
        self._create_ui()
        self._setup_tab_shortcuts()

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
        for category in ["combat", "social", "exploration", "relaxation", "special"]:
            if category in organized:
                # Sort configs within category by name
                sorted_organized[category] = sorted(
                    organized[category],
                    key=lambda c: c["name"]
                )

        return sorted_organized

    def _create_ui(self) -> None:
        """Create the main UI layout with tabs."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout()

        # Create tab widget
        self.tabs = QTabWidget()
        self.tabs.setTabPosition(QTabWidget.North)

        # Add a tab for each category
        tab_index = 0
        for category, configs in self.configs.items():
            tab_widget = self._create_category_tab(category, configs)
            self.tabs.addTab(tab_widget, category.capitalize())
            self.tab_configs[tab_index] = configs
            tab_index += 1

        # Connect tab change to update shortcuts
        self.tabs.currentChanged.connect(self._on_tab_changed)

        main_layout.addWidget(self.tabs)

        # Add control buttons (Stop button)
        control_layout = QHBoxLayout()

        self.stop_button = QPushButton("STOP")
        self.stop_button.setMinimumHeight(40)
        self.stop_button.setStyleSheet(self.STOP_STYLE)
        self.stop_button.clicked.connect(self._stop_current)
        self.stop_button.setEnabled(False)
        control_layout.addWidget(self.stop_button)

        main_layout.addLayout(control_layout)

        central_widget.setLayout(main_layout)

        # Status bar
        self.statusBar().showMessage("Ready - Select an environment to start")

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
        next_tab.activated.connect(lambda: self.tabs.setCurrentIndex(
            (self.tabs.currentIndex() + 1) % self.tabs.count()
        ))

        prev_tab = QShortcut(QKeySequence("Ctrl+PgUp"), self)
        prev_tab.activated.connect(lambda: self.tabs.setCurrentIndex(
            (self.tabs.currentIndex() - 1) % self.tabs.count()
        ))

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
        lights_enabled = config.get("engines", {}).get("lights", {}).get("enabled", False)

        # Button shows only the name (larger font)
        btn = QPushButton(name)
        btn.setStyleSheet(self.INACTIVE_STYLE)
        btn.setToolTip(description)
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
            shortcut_label.setFixedSize(29, 25)

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
        is_sound_only = sound_enabled and not spotify_enabled and not lights_enabled

        if sound_enabled:
            sound_emoji = "📢" if is_sound_only else "🔊"
            sound_label = QLabel(sound_emoji)
            sound_label.setFixedHeight(18)
            sound_label.setStyleSheet(
                "background-color: #FFCBA4; padding: 0px 6px; border: 1px solid gray; border-radius: 3px; font-size: 14px;"
            )
            sound_label.setAlignment(Qt.AlignCenter)
            emoji_layout.addWidget(sound_label)

        if spotify_enabled:
            spotify_label = QLabel("🎵")
            spotify_label.setFixedHeight(18)
            spotify_label.setStyleSheet(
                "background-color: #B4F0A8; padding: 0px 6px; border: 1px solid gray; border-radius: 3px; font-size: 14px;"
            )
            spotify_label.setAlignment(Qt.AlignCenter)
            emoji_layout.addWidget(spotify_label)

        if lights_enabled:
            lights_label = QLabel("💡")
            lights_label.setFixedHeight(18)
            lights_label.setStyleSheet(
                "background-color: #FFF9B0; padding: 0px 6px; border: 1px solid gray; border-radius: 3px; font-size: 14px;"
            )
            lights_label.setAlignment(Qt.AlignCenter)
            emoji_layout.addWidget(lights_label)

        emoji_layout.addStretch()
        emoji_row.setLayout(emoji_layout)

        # Create container that handles resizing with overlap
        container = ButtonContainer(btn, emoji_row, shortcut_label, desc_label)

        return container, btn

    def _start_environment(self, config: Dict[str, Any]) -> None:
        """Start an environment."""
        has_lights = config["engines"]["lights"]["enabled"]

        # Only stop lights runner if new config has lights
        if has_lights and self.lights_runner is not None:
            self._stop_lights()

        # Create and start runner
        try:
            runner = EngineRunner(config)
            runner.error_occurred.connect(self._on_error)
            runner.status_update.connect(self._on_status_update)
            runner.finished.connect(lambda: self._on_runner_finished(runner))
            runner.sound_finished.connect(lambda: self._on_sound_finished(config["name"]))
            runner.start()

            self.current_runner = runner
            self.current_config_name = config["name"]

            if has_lights:
                # This is a lights config - track it and highlight button
                self.lights_runner = runner
                self.lights_config_name = config["name"]
                self._update_active_button(config["name"])
                self.stop_button.setEnabled(True)
                self.statusBar().showMessage(f"Running: {config['name']}")
            else:
                # Sound-only config - highlight it while playing
                self._update_active_button(config["name"])
                status = f"Playing: {config['name']}"
                if self.lights_config_name:
                    status += f" (Lights: {self.lights_config_name})"
                self.statusBar().showMessage(status)

        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to start {config['name']}:\n{str(e)}"
            )
            self.statusBar().showMessage("Error starting environment")

    def _stop_lights(self) -> None:
        """Stop the currently running lights."""
        if self.lights_runner is not None:
            old_runner = self.lights_runner
            old_runner.stop()
            # Keep reference until thread finishes to avoid QThread crash
            self._old_runners.append(old_runner)
            old_runner.finished.connect(lambda: self._cleanup_old_runner(old_runner))
            self.lights_runner = None
            self.lights_config_name = None

    def _stop_current(self) -> None:
        """Stop all running environments (lights)."""
        self._stop_lights()
        self.current_runner = None
        self.current_config_name = None
        self._reset_button_styles()
        self.stop_button.setEnabled(False)
        self.statusBar().showMessage("Stopped")

    def _cleanup_old_runner(self, runner: EngineRunner) -> None:
        """Remove finished runner from old runners list."""
        if runner in self._old_runners:
            self._old_runners.remove(runner)

    def _on_error(self, error_msg: str) -> None:
        """Handle error from engine runner."""
        QMessageBox.warning(self, "Engine Error", error_msg)
        self.statusBar().showMessage(f"Error: {error_msg}")

    def _on_status_update(self, status: str) -> None:
        """Handle status update from engine runner."""
        self.statusBar().showMessage(status)

    def _on_sound_finished(self, sound_name: str) -> None:
        """Handle sound-only config finishing."""
        if self.lights_config_name:
            self.statusBar().showMessage(f"Sound '{sound_name}' finished - Lights: {self.lights_config_name}")
            # Re-highlight the active lights button
            self._update_active_button(self.lights_config_name)
        else:
            self.statusBar().showMessage(f"Sound '{sound_name}' finished")
            self._reset_button_styles()

    def _on_runner_finished(self, runner: EngineRunner) -> None:
        """Handle runner thread finishing."""
        # Only update status if this was the lights runner
        if runner == self.lights_runner:
            self.statusBar().showMessage(f"{self.lights_config_name} finished")
            self.lights_runner = None
            self.lights_config_name = None
            self._reset_button_styles()
            self.stop_button.setEnabled(False)

    def _update_active_button(self, active_name: str) -> None:
        """Highlight the active lights button."""
        for name, btn in self.buttons.items():
            if name == active_name:
                btn.setStyleSheet(self.ACTIVE_STYLE)
            else:
                btn.setStyleSheet(self.INACTIVE_STYLE)

    def _reset_button_styles(self) -> None:
        """Reset all buttons to inactive state."""
        for btn in self.buttons.values():
            btn.setStyleSheet(self.INACTIVE_STYLE)

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
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()


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

    # Detect and apply dark mode if system prefers it
    if detect_system_dark_mode():
        apply_dark_palette(app)

    launcher = EnvironmentLauncher()
    launcher.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
