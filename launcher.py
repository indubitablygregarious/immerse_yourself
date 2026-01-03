#!/usr/bin/env python3
"""
Immerse Yourself Environment Launcher
A PyQt5 GUI for managing ambient environment scripts with Spotify and smart lights.
"""

import sys
import os
import subprocess
import signal
from pathlib import Path
from typing import List, Dict, Optional

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QGridLayout, QPushButton,
    QStatusBar, QMessageBox, QVBoxLayout
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import QShortcut


class EnvironmentDiscovery:
    """Discovers and catalogs environment scripts from the environments directory."""

    def __init__(self, environments_dir: str = "environments"):
        self.environments_dir = Path(environments_dir)

    def discover_environments(self) -> List[Dict[str, str]]:
        """
        Scan environments/ directory and return sorted list of environments.
        Returns list of dicts with 'filename', 'filepath', and 'display_name' keys.
        """
        environments = []

        if not self.environments_dir.exists():
            return environments

        # Find all .py files, sorted alphabetically
        for py_file in sorted(self.environments_dir.glob("*.py")):
            # Skip symlinks and test files
            if py_file.is_symlink() or py_file.name == "f.py":
                continue

            env_info = {
                "filename": py_file.name,
                "filepath": str(py_file.absolute()),
                "display_name": self._make_display_name(py_file.stem),
                "category": self._categorize(py_file.stem),
            }
            environments.append(env_info)

        return environments

    def _make_display_name(self, stem: str) -> str:
        """Convert filename stem to display name: battle_dungeon -> Battle Dungeon"""
        return stem.replace("_", " ").title()

    def _categorize(self, stem: str) -> str:
        """Categorize environment for potential sorting/grouping."""
        if stem.startswith("battle_"):
            return "battle"
        elif stem.startswith("travel_"):
            return "travel"
        elif "tavern" in stem:
            return "tavern"
        elif stem.startswith("town"):
            return "town"
        else:
            return "other"


class ProcessManager:
    """Manages subprocess execution and termination of environment scripts."""

    def __init__(self, project_root: str = None):
        # Default to the directory containing this launcher script
        if project_root is None:
            project_root = str(Path(__file__).parent.absolute())
        self.project_root = project_root
        self.current_process: Optional[subprocess.Popen] = None
        self.current_env_name: Optional[str] = None

    def start_environment(self, script_path: str, env_name: str) -> bool:
        """
        Start a new environment, killing any existing one first.
        Args:
            script_path: Absolute path to the environment script
            env_name: Display name of the environment
        Returns:
            True if successful, False otherwise
        """
        self.stop_current()

        try:
            # Use Popen for async execution with process control
            # Set cwd to root so config files are found
            self.current_process = subprocess.Popen(
                [sys.executable, script_path],
                cwd=self.project_root,
                # Let stdout/stderr pass through to terminal for debugging
                # Create new process group for clean termination
                preexec_fn=os.setsid if sys.platform != "win32" else None,
            )
            self.current_env_name = env_name
            return True
        except Exception as e:
            print(f"Error starting environment: {e}")
            return False

    def stop_current(self) -> None:
        """Terminate the currently running environment gracefully."""
        if self.current_process:
            try:
                # Send SIGTERM first for graceful shutdown
                if sys.platform != "win32":
                    os.killpg(os.getpgid(self.current_process.pid), signal.SIGTERM)
                else:
                    self.current_process.terminate()

                # Wait briefly for graceful shutdown
                try:
                    self.current_process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    # Force kill if not terminated
                    if sys.platform != "win32":
                        os.killpg(os.getpgid(self.current_process.pid), signal.SIGKILL)
                    else:
                        self.current_process.kill()
            except Exception as e:
                print(f"Error stopping process: {e}")
            finally:
                self.current_process = None
                self.current_env_name = None

    def is_running(self) -> bool:
        """Check if an environment is currently running."""
        if self.current_process is None:
            return False
        return self.current_process.poll() is None

    def get_current_env_name(self) -> Optional[str]:
        """Return the name of the currently running environment."""
        return self.current_env_name if self.is_running() else None


class EnvironmentLauncher(QMainWindow):
    """Main PyQt5 window for the environment launcher."""

    # Keyboard layout matching QWERTY rows
    KEYS = [
        # Row 1: Q-P (10 keys)
        "Q", "W", "E", "R", "T", "Y", "U", "I", "O", "P",
        # Row 2: A-L (10 keys)
        "A", "S", "D", "F", "G", "H", "J", "K", "L", ";",
        # Row 3: Z-N (6 keys)
        "Z", "X", "C", "V", "B", "N",
    ]

    ACTIVE_STYLE = "background-color: #4CAF50; color: white; font-weight: bold; font-size: 11px;"
    INACTIVE_STYLE = "background-color: #f0f0f0; font-size: 11px;"
    OVERFLOW_STYLE = "background-color: #e0e0e0; font-size: 10px;"

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Immerse Yourself - Environment Launcher")
        self.setGeometry(100, 100, 1100, 450)

        # Initialize discovery and process management
        self.discovery = EnvironmentDiscovery()
        self.process_manager = ProcessManager()
        self.environments = self.discovery.discover_environments()

        # Track buttons for highlighting
        self.buttons: Dict[str, QPushButton] = {}
        self.shortcuts: List[QShortcut] = []

        # Create UI
        self._create_ui()

        # Monitor process status
        self.process_monitor = QTimer()
        self.process_monitor.timeout.connect(self._check_process_status)
        self.process_monitor.start(500)  # Check every 500ms

    def _create_ui(self) -> None:
        """Create the main UI layout."""
        # Central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout()

        # Grid layout for environment buttons
        grid_layout = QGridLayout()
        grid_layout.setSpacing(10)

        # Row configurations (row, col_offset, num_cols)
        rows_config = [
            (0, 0, 10),  # Row 0: Q-P (10 buttons)
            (1, 0.5, 10),  # Row 1: A-L (offset 0.5 for stagger effect)
            (2, 1, 6),  # Row 2: Z-N (offset 1)
        ]

        btn_index = 0
        for row_num, col_offset, num_cols in rows_config:
            for col in range(num_cols):
                if btn_index >= len(self.environments):
                    break

                env = self.environments[btn_index]
                self._create_button(
                    grid_layout, env, row_num, col, btn_index
                )
                btn_index += 1

        main_layout.addLayout(grid_layout)
        central_widget.setLayout(main_layout)

        # Status bar
        self.statusBar().showMessage("Ready")

    def _create_button(
        self, layout: QGridLayout, env: Dict, row: int, col: int, index: int
    ) -> None:
        """Create a single environment button with optional keyboard shortcut."""
        # Determine if this button has a keyboard shortcut
        has_shortcut = index < len(self.KEYS)
        shortcut_key = self.KEYS[index] if has_shortcut else ""

        # Create button text
        if has_shortcut:
            btn_text = f"{env['display_name']}\n({shortcut_key})"
        else:
            btn_text = env["display_name"]

        # Create button
        btn = QPushButton(btn_text)
        btn.setMinimumHeight(70)
        btn.setMinimumWidth(90)
        btn.setStyleSheet(self.INACTIVE_STYLE if has_shortcut else self.OVERFLOW_STYLE)
        btn.env = env  # Store environment info on button

        # Connect click event
        btn.clicked.connect(lambda checked, e=env: self._on_environment_clicked(e))

        # Store button for highlighting
        self.buttons[env["filename"]] = btn

        # Add to grid layout
        layout.addWidget(btn, row, col)

        # Create keyboard shortcut if applicable
        if has_shortcut:
            shortcut = QShortcut(QKeySequence(shortcut_key), self)
            shortcut.activated.connect(
                lambda e=env: self._on_environment_clicked(e)
            )
            self.shortcuts.append(shortcut)

    def _on_environment_clicked(self, env: Dict) -> None:
        """Handle environment button click or keyboard shortcut."""
        success = self.process_manager.start_environment(
            env["filepath"], env["display_name"]
        )

        if success:
            # Update UI
            self._update_active_button(env["filename"])
            self.statusBar().showMessage(f"Running: {env['display_name']}")
        else:
            self.statusBar().showMessage(
                f"Failed to start: {env['display_name']}"
            )
            QMessageBox.warning(
                self,
                "Launch Failed",
                f"Could not start {env['display_name']}.\n\nCheck that all config files (.spotify.ini, .wizbulb.ini) are present.",
            )

    def _update_active_button(self, active_filename: str) -> None:
        """Highlight the active environment button and unhighlight others."""
        for filename, btn in self.buttons.items():
            if filename == active_filename:
                btn.setStyleSheet(self.ACTIVE_STYLE)
            else:
                # Determine if button should have regular or overflow style
                btn_index = next(
                    (i for i, env in enumerate(self.environments)
                     if env["filename"] == filename),
                    -1
                )
                has_shortcut = btn_index < len(self.KEYS) if btn_index >= 0 else False
                btn.setStyleSheet(
                    self.INACTIVE_STYLE if has_shortcut else self.OVERFLOW_STYLE
                )

    def _check_process_status(self) -> None:
        """Periodically check if the current process is still running."""
        if not self.process_manager.is_running():
            if self.process_manager.current_env_name:
                # Process has died, reset UI
                self._reset_button_styles()
                self.statusBar().showMessage("Environment stopped")
                self.process_manager.current_env_name = None

    def _reset_button_styles(self) -> None:
        """Reset all buttons to inactive state."""
        for i, (filename, btn) in enumerate(self.buttons.items()):
            has_shortcut = i < len(self.KEYS)
            btn.setStyleSheet(
                self.INACTIVE_STYLE if has_shortcut else self.OVERFLOW_STYLE
            )

    def closeEvent(self, event) -> None:
        """Handle window close event - stop any running environment."""
        if self.process_manager.is_running():
            reply = QMessageBox.question(
                self,
                "Confirm Exit",
                f"Environment '{self.process_manager.current_env_name}' is running.\n\nStop and exit?",
                QMessageBox.Yes | QMessageBox.No,
            )

            if reply == QMessageBox.Yes:
                self.process_manager.stop_current()
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
