"""
Sound Engine - Handles sound effect playback with graceful degradation
"""

import threading
import subprocess
from pathlib import Path
from typing import Optional, List


# Global list to track active sound processes
_active_sound_processes: List[subprocess.Popen] = []
_process_lock = threading.Lock()


def stop_all_sounds() -> int:
    """
    Stop all currently playing sounds.

    Returns:
        Number of sounds stopped
    """
    global _active_sound_processes
    stopped = 0
    with _process_lock:
        for proc in _active_sound_processes[:]:
            try:
                proc.terminate()
                stopped += 1
            except Exception:
                pass
        _active_sound_processes.clear()
    return stopped


def register_sound_process(proc: subprocess.Popen) -> None:
    """
    Register a sound process for tracking (so it can be stopped later).

    Args:
        proc: The subprocess.Popen object to track
    """
    with _process_lock:
        _active_sound_processes.append(proc)


def unregister_sound_process(proc: subprocess.Popen) -> None:
    """
    Unregister a sound process when it finishes.

    Args:
        proc: The subprocess.Popen object to remove
    """
    with _process_lock:
        if proc in _active_sound_processes:
            _active_sound_processes.remove(proc)


class SoundEngine:
    """
    Manages sound effect playback with error tolerance.

    This engine uses ffplay/paplay for audio playback to allow stopping sounds.
    Falls back to playsound3 if neither is available. All errors are logged
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

        # Detect available audio player
        self._player_cmd = self._detect_player()

    def _detect_player(self) -> Optional[List[str]]:
        """Detect available audio player command."""
        # Try ffplay first (from ffmpeg, very common)
        try:
            subprocess.run(["ffplay", "-version"], capture_output=True, timeout=1)
            return ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet"]
        except (subprocess.SubprocessError, FileNotFoundError):
            pass

        # Try paplay (PulseAudio, common on Linux)
        try:
            subprocess.run(["paplay", "--version"], capture_output=True, timeout=1)
            return ["paplay"]
        except (subprocess.SubprocessError, FileNotFoundError):
            pass

        # Try aplay (ALSA, common on Linux)
        try:
            subprocess.run(["aplay", "--version"], capture_output=True, timeout=1)
            return ["aplay", "-q"]
        except (subprocess.SubprocessError, FileNotFoundError):
            pass

        # No subprocess player available, will use playsound3
        return None

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
            if self._player_cmd:
                # Use subprocess player (preferred)
                cmd = self._player_cmd + [str(sound_path)]
                subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                # Fallback to playsound3
                import playsound3
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
                if self._player_cmd:
                    # Use subprocess player (can be stopped)
                    cmd = self._player_cmd + [str(sound_path)]
                    proc = subprocess.Popen(
                        cmd,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                    )
                    with _process_lock:
                        _active_sound_processes.append(proc)
                    proc.wait()
                    with _process_lock:
                        if proc in _active_sound_processes:
                            _active_sound_processes.remove(proc)
                else:
                    # Fallback to playsound3 (cannot be stopped)
                    import playsound3
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
