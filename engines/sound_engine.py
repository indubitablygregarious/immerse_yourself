"""
Sound Engine - Handles sound effect playback with graceful degradation
"""

import threading
from pathlib import Path
from typing import Optional
import playsound3


class SoundEngine:
    """
    Manages sound effect playback with error tolerance.

    This engine wraps playsound3 to provide graceful degradation when
    sound files are missing or playback fails. All errors are logged
    but don't crash the application.

    Attributes:
        project_root: Path to the project root directory
    """

    def __init__(self, project_root: Optional[str] = None):
        """
        Initialize the Sound Engine.

        Args:
            project_root: Path to project root. If None, uses current directory.
        """
        if project_root is None:
            self.project_root = Path.cwd()
        else:
            self.project_root = Path(project_root)

    def play(self, sound_file: Optional[str]) -> bool:
        """
        Play a sound file if it exists.

        This method attempts to play the specified sound file. If the file
        doesn't exist or playback fails for any reason, it logs a warning
        but returns gracefully without raising an exception.

        Args:
            sound_file: Filename relative to project root (e.g., "chill.wav"),
                       or None to skip playback

        Returns:
            True if sound played successfully, False otherwise

        Examples:
            >>> engine = SoundEngine()
            >>> engine.play("dooropen.wav")
            True
            >>> engine.play("nonexistent.wav")
            WARNING: Could not play sound file nonexistent.wav
            False
            >>> engine.play(None)
            False
        """
        if sound_file is None:
            return False

        sound_path = self.project_root / sound_file

        # Check if file exists first for better error messaging
        if not sound_path.exists():
            print(f"INFO: Sound file not found: {sound_file}")
            print(f"      (This is OK - some sounds are suggestions and not yet distributed)")
            print(f"      Expected path: {sound_path}")
            return False

        try:
            playsound3.playsound(str(sound_path))
            return True
        except Exception as e:
            # Graceful degradation - log but don't crash
            print(f"WARNING: Could not play sound file {sound_file}")
            print(f"         Reason: {str(e)}")
            print(f"         Path: {sound_path}")
            return False

    def play_async(self, sound_file: Optional[str], on_complete=None) -> bool:
        """
        Play a sound file asynchronously (non-blocking).

        Args:
            sound_file: Filename relative to project root
            on_complete: Optional callback to call when sound finishes

        Returns:
            True if playback was started, False otherwise
        """
        if sound_file is None:
            if on_complete:
                on_complete()
            return False

        sound_path = self.project_root / sound_file

        if not sound_path.exists():
            print(f"INFO: Sound file not found: {sound_file}")
            if on_complete:
                on_complete()
            return False

        def play_in_thread():
            try:
                playsound3.playsound(str(sound_path))
            except Exception as e:
                print(f"WARNING: Could not play sound file {sound_file}: {e}")
            finally:
                if on_complete:
                    on_complete()

        thread = threading.Thread(target=play_in_thread, daemon=True)
        thread.start()
        return True

    def test_sound(self, sound_file: str) -> bool:
        """
        Test if a sound file exists and is playable without actually playing it.

        Args:
            sound_file: Filename relative to project root

        Returns:
            True if file exists, False otherwise
        """
        sound_path = self.project_root / sound_file
        return sound_path.exists() and sound_path.is_file()
