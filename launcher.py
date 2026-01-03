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

        # Keep running until stopped
        while self.running:
            await asyncio.sleep(1)

        await self.lights_engine.stop()

    def stop(self):
        """Stop the engines."""
        self.running = False
        self.wait(5000)  # Wait up to 5 seconds for thread to finish


class EnvironmentLauncher(QMainWindow):
    """Main PyQt5 window for the environment launcher with tabs."""

    # Keyboard shortcuts (can be used across all tabs)
    KEYS = [
        "Q", "W", "E", "R", "T", "Y", "U", "I", "O", "P",
        "A", "S", "D", "F", "G", "H", "J", "K", "L", ";",
        "Z", "X", "C", "V", "B", "N",
    ]

    ACTIVE_STYLE = "background-color: #4CAF50; color: white; font-weight: bold; font-size: 10px; padding: 5px;"
    INACTIVE_STYLE = "background-color: #f0f0f0; font-size: 9px; padding: 5px;"
    STOP_STYLE = "background-color: #f44336; color: white; font-weight: bold; font-size: 12px;"

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Immerse Yourself - Environment Launcher")
        self.setGeometry(100, 100, 1200, 500)

        # Load configurations
        self.config_loader = ConfigLoader("env_conf")
        self.configs = self._load_and_organize_configs()

        # Track active environment
        self.current_runner: Optional[EngineRunner] = None
        self.current_config_name: Optional[str] = None
        self.buttons: Dict[str, QPushButton] = {}  # config_name -> button
        self.shortcuts: List[QShortcut] = []

        # Create UI
        self._create_ui()

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
        for category, configs in self.configs.items():
            tab_widget = self._create_category_tab(category, configs)
            self.tabs.addTab(tab_widget, category.capitalize())

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

            # Determine if this config has a global keyboard shortcut
            global_idx = self._get_global_config_index(config["name"])
            has_shortcut = global_idx < len(self.KEYS)
            shortcut_key = self.KEYS[global_idx] if has_shortcut else ""

            # Create button
            btn = self._create_button(config, shortcut_key)
            layout.addWidget(btn, row, col)

            # Store button reference
            self.buttons[config["name"]] = btn

        tab_widget.setLayout(layout)
        return tab_widget

    def _get_global_config_index(self, config_name: str) -> int:
        """Get the global index of a config across all categories."""
        idx = 0
        for category in ["combat", "social", "exploration", "relaxation", "special"]:
            if category in self.configs:
                for config in self.configs[category]:
                    if config["name"] == config_name:
                        return idx
                    idx += 1
        return 999  # No shortcut

    def _create_button(self, config: Dict[str, Any], shortcut_key: str) -> QPushButton:
        """Create a button for an environment."""
        # Button text with metadata
        name = config["name"]
        intensity = config.get("metadata", {}).get("intensity", "")
        description = config.get("description", "")

        # Determine which engines are enabled
        sound_enabled = config.get("engines", {}).get("sound", {}).get("enabled", False)
        spotify_enabled = config.get("engines", {}).get("spotify", {}).get("enabled", False)
        lights_enabled = config.get("engines", {}).get("lights", {}).get("enabled", False)

        # Build emoji indicators
        emoji_indicators = ""
        if sound_enabled:
            emoji_indicators += "🔊"
        if spotify_enabled:
            emoji_indicators += "🎵"
        if lights_enabled:
            emoji_indicators += "💡"

        # Truncate description if too long (max ~50 chars for readability)
        if len(description) > 50:
            description = description[:47] + "..."

        btn_text = f"{emoji_indicators} {name}"
        if intensity:
            btn_text += f"\n[{intensity}]"
        if shortcut_key:
            btn_text += f" ({shortcut_key})"
        if description:
            btn_text += f"\n{description}"

        # Create button with larger size to fit description
        btn = QPushButton(btn_text)
        btn.setMinimumHeight(100)
        btn.setMinimumWidth(140)
        btn.setStyleSheet(self.INACTIVE_STYLE)
        btn.setToolTip(config.get("description", ""))  # Full description in tooltip

        # Connect click
        btn.clicked.connect(lambda: self._start_environment(config))

        # Create keyboard shortcut if applicable
        if shortcut_key:
            shortcut = QShortcut(QKeySequence(shortcut_key), self)
            shortcut.activated.connect(lambda: self._start_environment(config))
            self.shortcuts.append(shortcut)

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
            self.current_runner.stop()
            self.current_runner = None
            self.current_config_name = None
            self._reset_button_styles()
            self.stop_button.setEnabled(False)
            self.statusBar().showMessage("Stopped")

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
                self._stop_current()
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
