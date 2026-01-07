"""
ImmersiveStatusBar - Multi-section status bar for tracking environment state.

Tracks 4 independent statuses:
- Sound file currently playing
- Music/atmosphere (Spotify playlist)
- Lights animation currently running
- Temporary messages (errors, general status)
"""

from typing import Optional
from pathlib import Path
from PyQt5.QtWidgets import QWidget, QStatusBar, QHBoxLayout
from PyQt5.QtCore import pyqtSignal, pyqtSlot, QTimer


class ImmersiveStatusBar(QWidget):
    """
    Multi-section status bar for Immerse Yourself.

    Displays format:
    "Immerse yourself running - sound: playing X - music: playing Y - lights: playing Z"

    Sections are omitted when not active.
    """

    # Signal emitted when the displayed status changes
    status_changed = pyqtSignal(str)

    # Default messages
    DEFAULT_READY = "Ready - Select an environment to start"
    PREFIX = "Immerse yourself running"

    def __init__(self, parent=None):
        super().__init__(parent)

        # Internal state
        self._sound: Optional[str] = None
        self._music: Optional[str] = None
        self._music_source: str = "spotify"  # "spotify" or "atmosphere"
        self._music_raw: Optional[str] = None  # Raw name for tooltip
        self._lights: Optional[str] = None
        self._temp_message: Optional[str] = None

        # Timer for temporary messages
        self._temp_timer = QTimer(self)
        self._temp_timer.setSingleShot(True)
        self._temp_timer.timeout.connect(self._clear_temp_message)

        # Create the underlying status bar
        self._status_bar = QStatusBar(self)
        self._status_bar.setSizeGripEnabled(True)

        # Layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._status_bar)

        # Initial display
        self._update_display()

    def _update_display(self) -> None:
        """Update the status bar display based on current state."""
        # Temporary message takes precedence
        if self._temp_message:
            self._status_bar.showMessage(self._temp_message)
            self.status_changed.emit(self._temp_message)
            self._update_tooltip()
            return

        # Build sections
        sections = []

        if self._sound:
            sections.append(f"sound: playing {self._sound}")

        if self._music:
            sections.append(f"music: playing {self._music}")

        if self._lights:
            sections.append(f"lights: playing {self._lights}")

        # Compose final message
        if sections:
            status = f"{self.PREFIX} || " + " || ".join(sections)
        else:
            status = self.DEFAULT_READY

        self._status_bar.showMessage(status)
        self.status_changed.emit(status)
        self._update_tooltip()

    def _update_tooltip(self) -> None:
        """Update the tooltip with detailed multi-line status information."""
        lines = []

        # Sound section
        lines.append("═══ Sound ═══")
        if self._sound:
            lines.append(f"  🔊 {self._sound}")
        else:
            lines.append("  (not playing)")
        lines.append("")

        # Music/Atmosphere section
        if self._music_source == "atmosphere":
            lines.append("═══ Atmosphere ═══")
            if self._music_raw:
                # Split by " + " to show each sound on its own line
                sounds = self._music_raw.split(" + ")
                for sound in sounds:
                    lines.append(f"  🌊 {sound}")
            else:
                lines.append("  (not playing)")
        else:
            lines.append("═══ Music ═══")
            if self._music_raw:
                lines.append(f"  🎵 {self._music_raw}")
            else:
                lines.append("  (not playing)")
        lines.append("")

        # Lights section
        lines.append("═══ Lights ═══")
        if self._lights:
            lines.append(f"  💡 {self._lights}")
        else:
            lines.append("  (not active)")

        self._status_bar.setToolTip("\n".join(lines))

    # --- Setters ---

    def set_sound(self, sound_file: Optional[str]) -> None:
        """Set current sound status. Pass None or empty string to clear."""
        if sound_file:
            # Extract just filename from path
            self._sound = Path(sound_file).name
        else:
            self._sound = None
        self._update_display()

    def set_music(self, name: Optional[str], source: str = "spotify") -> None:
        """
        Set current music status. Pass None to clear.

        Args:
            name: Playlist name or sound names (joined with " + " for atmosphere)
            source: "spotify" or "atmosphere" - affects display prefix
        """
        self._music_source = source
        self._music_raw = name
        if name:
            if source == "atmosphere":
                self._music = f"Atmosphere: {name}"
            else:
                self._music = f"Spotify: {name}"
        else:
            self._music = None
        self._update_display()

    def set_lights(self, animation_name: Optional[str]) -> None:
        """Set current lights status. Pass None to clear."""
        self._lights = animation_name if animation_name else None
        self._update_display()

    def set_message(self, message: Optional[str], timeout_ms: int = 0) -> None:
        """
        Set a temporary message that overrides the status display.

        Args:
            message: Message to display, or None to clear
            timeout_ms: Auto-clear after this many milliseconds (0 = no timeout)
        """
        self._temp_timer.stop()
        self._temp_message = message

        if message and timeout_ms > 0:
            self._temp_timer.start(timeout_ms)

        self._update_display()

    # --- Clear methods ---

    def clear_sound(self) -> None:
        """Clear sound status."""
        self._sound = None
        self._update_display()

    def clear_music(self) -> None:
        """Clear music status."""
        self._music = None
        self._music_raw = None
        self._update_display()

    def clear_lights(self) -> None:
        """Clear lights status."""
        self._lights = None
        self._update_display()

    def clear_message(self) -> None:
        """Clear temporary message."""
        self._temp_timer.stop()
        self._temp_message = None
        self._update_display()

    def clear_all(self) -> None:
        """Clear all statuses."""
        self._temp_timer.stop()
        self._sound = None
        self._music = None
        self._music_raw = None
        self._lights = None
        self._temp_message = None
        self._update_display()

    def _clear_temp_message(self) -> None:
        """Internal: clear temp message when timer fires."""
        self._temp_message = None
        self._update_display()

    # --- Getters ---

    def get_sound(self) -> Optional[str]:
        """Get current sound status."""
        return self._sound

    def get_music(self) -> Optional[str]:
        """Get current music status."""
        return self._music

    def get_lights(self) -> Optional[str]:
        """Get current lights status."""
        return self._lights

    def is_active(self) -> bool:
        """Check if any environment is currently running."""
        return bool(self._sound or self._music or self._lights)

    # --- Slots for signal connection ---

    @pyqtSlot(str)
    def on_sound_started(self, sound_file: str) -> None:
        """Slot: sound playback started."""
        self.set_sound(sound_file)

    @pyqtSlot()
    def on_sound_finished(self) -> None:
        """Slot: sound playback finished."""
        self.clear_sound()

    @pyqtSlot(str)
    def on_music_started(self, playlist_name: str) -> None:
        """Slot: Spotify playback started."""
        self.set_music(playlist_name, source="spotify")

    @pyqtSlot(str)
    def on_atmosphere_started(self, sound_names: str) -> None:
        """Slot: Atmosphere playback started."""
        self.set_music(sound_names, source="atmosphere")

    @pyqtSlot()
    def on_music_stopped(self) -> None:
        """Slot: Spotify/Atmosphere playback stopped."""
        self.clear_music()

    @pyqtSlot(str)
    def on_lights_started(self, animation_name: str) -> None:
        """Slot: lights animation started."""
        self.set_lights(animation_name)

    @pyqtSlot()
    def on_lights_stopped(self) -> None:
        """Slot: lights animation stopped."""
        self.clear_lights()

    @pyqtSlot(str)
    def on_error(self, error_msg: str) -> None:
        """Slot: error occurred - show as temporary message."""
        self.set_message(f"Error: {error_msg}", timeout_ms=5000)

    @pyqtSlot(str)
    def on_status_message(self, message: str) -> None:
        """Slot: general status message - show temporarily."""
        self.set_message(message, timeout_ms=3000)

    # --- Compatibility methods ---

    def get_status_bar(self) -> QStatusBar:
        """Get the underlying QStatusBar for use with QMainWindow.setStatusBar()."""
        return self._status_bar

    def showMessage(self, message: str, timeout: int = 0) -> None:
        """
        Compatibility method: show a message like QStatusBar.

        Note: This sets a temporary message that overrides the status display.
        For permanent status changes, use set_sound(), set_music(), set_lights().
        """
        self.set_message(message, timeout_ms=timeout)
