#!/usr/bin/env python3
"""
Immerse Yourself Environment Launcher
A PyQt5 GUI for managing ambient environment configs with Spotify and smart lights.
"""

import sys
import asyncio
from pathlib import Path
from typing import List, Dict, Optional, Any
from collections import defaultdict

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QGridLayout, QPushButton,
    QStatusBar, QMessageBox, QVBoxLayout, QTabWidget, QHBoxLayout
)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import QShortcut

from config_loader import ConfigLoader
from engines import SoundEngine, SpotifyEngine, LightsEngine


class EngineRunner(QThread):
    """Background thread for running async engines."""

    error_occurred = pyqtSignal(str)
    status_update = pyqtSignal(str)

    def __init__(self, config: Dict[str, Any]):
        super().__init__()
        self.config = config
        self.lights_engine: Optional[LightsEngine] = None
        self.running = False

    def run(self):
        """Run the engines based on configuration."""
        try:
            self.running = True

            # Sound engine (synchronous, one-shot)
            if self.config["engines"]["sound"]["enabled"]:
                sound_file = self.config["engines"]["sound"]["file"]
                self.status_update.emit(f"Playing sound: {sound_file}")
                sound_engine = SoundEngine()
                sound_engine.play(sound_file)

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

        except Exception as e:
            self.error_occurred.emit(f"Engine error: {str(e)}")
        finally:
            self.running = False

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

    ACTIVE_STYLE = "background-color: #4CAF50; color: white; padding: 8px; font-family: monospace; font-size: 13px;"
    INACTIVE_STYLE = "background-color: #f0f0f0; padding: 8px; font-family: monospace; font-size: 13px;"
    STOP_STYLE = "background-color: #f44336; color: white; font-weight: bold; font-size: 12px;"

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Immerse Yourself - Environment Launcher")
        self.setGeometry(100, 100, 1000, 600)

        # Load configurations
        self.config_loader = ConfigLoader("env_conf")
        self.configs = self._load_and_organize_configs()

        # Track active environment
        self.current_runner: Optional[EngineRunner] = None
        self.current_config_name: Optional[str] = None
        self.buttons: Dict[str, QPushButton] = {}  # config_name -> button
        self.shortcuts: List[QShortcut] = []
        self._old_runners: List[EngineRunner] = []  # Keep refs until threads finish
        self.tab_configs: Dict[int, List[Dict[str, Any]]] = {}  # tab_index -> configs

        # Create UI
        self._create_ui()
        self._setup_tab_shortcuts()

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

            # Create button
            btn = self._create_button(config, shortcut_key)
            layout.addWidget(btn, row, col)

            # Store button reference
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

    def _create_button(self, config: Dict[str, Any], shortcut_key: str) -> QPushButton:
        """Create a button for an environment."""
        name = config["name"]
        description = config.get("description", "")

        # Determine which engines are enabled
        sound_enabled = config.get("engines", {}).get("sound", {}).get("enabled", False)
        spotify_enabled = config.get("engines", {}).get("spotify", {}).get("enabled", False)
        lights_enabled = config.get("engines", {}).get("lights", {}).get("enabled", False)

        # Build emoji indicators - use distinct emoji for sound-only
        emoji_indicators = ""
        is_sound_only = sound_enabled and not spotify_enabled and not lights_enabled
        if sound_enabled:
            emoji_indicators += "📢" if is_sound_only else "🔊"
        if spotify_enabled:
            emoji_indicators += "🎵"
        if lights_enabled:
            emoji_indicators += "💡"

        # Word wrap description to ~30 chars per line for 3 lines
        desc_lines = []
        if description:
            words = description.split()
            current_line = ""
            for word in words:
                if len(current_line) + len(word) + 1 <= 30:
                    current_line += (" " if current_line else "") + word
                else:
                    if current_line:
                        desc_lines.append(current_line)
                    current_line = word
                if len(desc_lines) >= 3:
                    break
            if current_line and len(desc_lines) < 3:
                desc_lines.append(current_line)

        # Build button text with fixed-width padding for alignment
        # Header: "emoji      name      (key)"
        hotkey_text = f"({shortcut_key})" if shortcut_key else "   "

        # Pad to create: emoji (left) ... name (center) ... hotkey (right)
        total_width = 28
        emoji_part = emoji_indicators.ljust(4)
        hotkey_part = hotkey_text.rjust(4)
        # Center the name in remaining space
        center_width = total_width - 8
        name_part = name.center(center_width)

        header = f"{emoji_part}{name_part}{hotkey_part}"

        # Combine: header, blank line, description
        btn_text = header + "\n"
        if desc_lines:
            for line in desc_lines:
                btn_text += "\n" + line.center(total_width)

        # Create button
        btn = QPushButton(btn_text)
        btn.setMinimumHeight(130)
        btn.setMinimumWidth(260)
        btn.setStyleSheet(self.INACTIVE_STYLE)
        btn.setToolTip(config.get("description", ""))

        # Connect click
        btn.clicked.connect(lambda checked=False, c=config: self._start_environment(c))

        return btn

    def _start_environment(self, config: Dict[str, Any]) -> None:
        """Start an environment."""
        # Stop current if running
        if self.current_runner is not None:
            self._stop_current()

        # Create and start runner
        try:
            self.current_runner = EngineRunner(config)
            self.current_runner.error_occurred.connect(self._on_error)
            self.current_runner.status_update.connect(self._on_status_update)
            self.current_runner.finished.connect(self._on_runner_finished)
            self.current_runner.start()

            self.current_config_name = config["name"]
            self._update_active_button(config["name"])
            self.stop_button.setEnabled(True)
            self.statusBar().showMessage(f"Running: {config['name']}")

        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to start {config['name']}:\n{str(e)}"
            )
            self.statusBar().showMessage("Error starting environment")

    def _stop_current(self) -> None:
        """Stop the currently running environment."""
        if self.current_runner is not None:
            self.statusBar().showMessage("Stopping...")
            old_runner = self.current_runner
            old_runner.stop()
            # Keep reference until thread finishes to avoid QThread crash
            self._old_runners.append(old_runner)
            old_runner.finished.connect(lambda: self._cleanup_old_runner(old_runner))
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

    def _on_runner_finished(self) -> None:
        """Handle runner thread finishing."""
        if self.current_config_name:
            self.statusBar().showMessage(f"{self.current_config_name} finished")

    def _update_active_button(self, active_name: str) -> None:
        """Highlight the active environment button."""
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
        if self.current_runner is not None and self.current_runner.running:
            reply = QMessageBox.question(
                self,
                "Confirm Exit",
                f"Environment '{self.current_config_name}' is running.\n\nStop and exit?",
                QMessageBox.Yes | QMessageBox.No,
            )

            if reply == QMessageBox.Yes:
                # On exit, actually wait for cleanup
                self.current_runner.running = False
                self.current_runner.wait(2000)
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()


def main():
    """Entry point for the application."""
    app = QApplication(sys.argv)
    launcher = EnvironmentLauncher()
    launcher.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
