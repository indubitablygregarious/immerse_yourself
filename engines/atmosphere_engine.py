"""
Atmosphere Engine - Manages looping ambient soundscapes with mixing support

This engine plays multiple sounds simultaneously in loops, with individual
volume control and fade-in/fade-out transitions. Used as an alternative
to Spotify for ambient audio.
"""

import threading
import subprocess
import time
from pathlib import Path
from typing import Optional, List, Dict, Any

from freesound_manager import FreesoundManager, is_freesound_url


# Global list to track active atmosphere processes (separate from sound effects)
_active_atmosphere_processes: List[subprocess.Popen] = []
_atmosphere_lock = threading.Lock()

# Fade duration in seconds
FADE_DURATION = 3


def stop_all_atmosphere(fade_out: bool = True) -> int:
    """
    Stop all currently playing atmosphere sounds.

    Args:
        fade_out: If True, fade out over 3 seconds before stopping

    Returns:
        Number of sounds stopped
    """
    global _active_atmosphere_processes
    stopped = 0

    with _atmosphere_lock:
        processes_to_stop = _active_atmosphere_processes[:]
        _active_atmosphere_processes.clear()

    if not processes_to_stop:
        return 0

    if fade_out:
        # Graceful fade out - just terminate and let ffplay handle it
        # ffplay doesn't support runtime volume changes, so we do a quick terminate
        for proc in processes_to_stop:
            try:
                proc.terminate()
                stopped += 1
            except Exception:
                pass
    else:
        # Immediate stop
        for proc in processes_to_stop:
            try:
                proc.terminate()
                stopped += 1
            except Exception:
                pass

    return stopped


def register_atmosphere_process(proc: subprocess.Popen) -> None:
    """
    Register an atmosphere process for tracking.

    Args:
        proc: The subprocess.Popen object to track
    """
    with _atmosphere_lock:
        _active_atmosphere_processes.append(proc)


def unregister_atmosphere_process(proc: subprocess.Popen) -> None:
    """
    Unregister an atmosphere process when it finishes.

    Args:
        proc: The subprocess.Popen object to remove
    """
    with _atmosphere_lock:
        if proc in _active_atmosphere_processes:
            _active_atmosphere_processes.remove(proc)


def is_atmosphere_playing() -> bool:
    """Check if any atmosphere sounds are currently playing."""
    with _atmosphere_lock:
        return len(_active_atmosphere_processes) > 0


class AtmosphereEngine:
    """
    Manages atmosphere audio playback with multiple looped sounds.

    Features:
    - Multiple simultaneous sounds from freesound.org URLs
    - Individual volume control per sound (0-100%)
    - 3-second fade in transitions
    - Process tracking for stoppable playback

    Attributes:
        project_root: Path to the project root directory
    """

    def __init__(self, project_root: Optional[str] = None):
        """
        Initialize the Atmosphere Engine.

        Args:
            project_root: Path to project root. If None, uses current directory.
        """
        if project_root is None:
            self.project_root = Path.cwd()
        else:
            self.project_root = Path(project_root)

        self._freesound_manager = FreesoundManager()
        self._player_cmd = self._detect_player()

    def _detect_player(self) -> Optional[List[str]]:
        """Detect available audio player command."""
        # Only ffplay supports looping and volume control properly
        try:
            subprocess.run(["ffplay", "-version"], capture_output=True, timeout=1)
            return ["ffplay"]
        except (subprocess.SubprocessError, FileNotFoundError):
            pass

        return None

    def _resolve_sound_path(self, url_or_path: str) -> Optional[Path]:
        """
        Resolve a sound URL or path to a local file path.

        Args:
            url_or_path: Either a freesound.org URL or local file path

        Returns:
            Path to local file, or None if resolution fails
        """
        if is_freesound_url(url_or_path):
            try:
                local_path, _ = self._freesound_manager.get_sound(url_or_path)
                return local_path
            except Exception as e:
                print(f"WARNING: Failed to download freesound: {url_or_path}")
                print(f"         Reason: {e}")
                return None
        else:
            # Local file path
            path = Path(url_or_path)
            if not path.is_absolute():
                path = self.project_root / url_or_path
            if path.exists():
                return path
            else:
                print(f"WARNING: Atmosphere file not found: {url_or_path}")
                return None

    def _get_sound_display_name(self, url_or_path: str) -> str:
        """
        Get the display name for a sound.

        Args:
            url_or_path: Either a freesound.org URL or local file path

        Returns:
            Human-readable display name
        """
        if is_freesound_url(url_or_path):
            try:
                return self._freesound_manager.get_display_name(url_or_path)
            except Exception:
                return "Unknown Sound"
        else:
            # Local file - use filename without extension
            return Path(url_or_path).stem

    def get_display_names(self, mix: List[Dict[str, Any]]) -> List[str]:
        """
        Get display names for all sounds in a mix.

        Args:
            mix: List of sound configurations with 'url' keys

        Returns:
            List of human-readable display names
        """
        names = []
        for sound_config in mix:
            url = sound_config.get("url", "")
            name = self._get_sound_display_name(url)
            names.append(name)
        return names

    def play_mix(self, mix: List[Dict[str, Any]]) -> bool:
        """
        Start playing a mix of sounds.

        Each sound loops infinitely with its specified volume and fades in
        over 3 seconds.

        Args:
            mix: List of sound configurations, each with:
                - url: freesound.org URL or local file path (required)
                - volume: 0-100, defaults to 100 (optional)

        Returns:
            True if at least one sound started successfully
        """
        if not self._player_cmd:
            print("WARNING: ffplay not found. Atmosphere requires ffplay (ffmpeg).")
            return False

        started_any = False

        for sound_config in mix:
            url = sound_config.get("url", "")
            volume = sound_config.get("volume", 100)

            # Resolve to local path
            sound_path = self._resolve_sound_path(url)
            if not sound_path:
                continue

            # Build ffplay command with looping, volume, and fade-in
            # -loop 0 = infinite loop
            # -volume N = volume 0-100
            # -af "afade=t=in:st=0:d=3" = fade in over 3 seconds
            cmd = [
                "ffplay",
                "-nodisp",           # No display window
                "-loglevel", "quiet",  # Suppress output
                "-loop", "0",        # Infinite loop
                "-volume", str(int(volume)),
                "-af", f"afade=t=in:st=0:d={FADE_DURATION}",
                str(sound_path)
            ]

            try:
                proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                register_atmosphere_process(proc)
                started_any = True
            except Exception as e:
                print(f"WARNING: Failed to start atmosphere sound: {url}")
                print(f"         Reason: {e}")

        return started_any

    def stop(self, fade_out: bool = True) -> int:
        """
        Stop all atmosphere sounds.

        Args:
            fade_out: If True, attempt graceful fade out

        Returns:
            Number of sounds stopped
        """
        return stop_all_atmosphere(fade_out=fade_out)

    def is_playing(self) -> bool:
        """Check if atmosphere is currently playing."""
        return is_atmosphere_playing()
