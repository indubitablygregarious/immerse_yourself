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

# Global mapping of URL -> process for individual sound control
_url_to_process: Dict[str, subprocess.Popen] = {}

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
    global _active_atmosphere_processes, _url_to_process
    stopped = 0

    with _atmosphere_lock:
        processes_to_stop = _active_atmosphere_processes[:]
        _active_atmosphere_processes.clear()
        _url_to_process.clear()

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


def is_url_playing(url: str) -> bool:
    """Check if a specific URL is currently playing."""
    with _atmosphere_lock:
        if url in _url_to_process:
            proc = _url_to_process[url]
            # Check if process is still running
            if proc.poll() is None:
                return True
            else:
                # Process ended, clean up
                del _url_to_process[url]
                if proc in _active_atmosphere_processes:
                    _active_atmosphere_processes.remove(proc)
        return False


def get_active_urls() -> List[str]:
    """Get list of currently playing atmosphere URLs."""
    with _atmosphere_lock:
        # Clean up dead processes while we're at it
        dead_urls = []
        for url, proc in _url_to_process.items():
            if proc.poll() is not None:
                dead_urls.append(url)
                if proc in _active_atmosphere_processes:
                    _active_atmosphere_processes.remove(proc)
        for url in dead_urls:
            del _url_to_process[url]
        return list(_url_to_process.keys())


def register_atmosphere_process(proc: subprocess.Popen, url: str = None) -> None:
    """
    Register an atmosphere process for tracking.

    Args:
        proc: The subprocess.Popen object to track
        url: Optional URL to associate with this process for individual control
    """
    with _atmosphere_lock:
        _active_atmosphere_processes.append(proc)
        if url:
            _url_to_process[url] = proc


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

    def select_sounds(self, mix: List[Dict[str, Any]], min_sounds: int = 2, max_sounds: int = 6) -> List[Dict[str, Any]]:
        """
        Select which sounds to play based on optional/probability/pool settings.

        Selection logic:
        1. Required sounds (no optional flag) are always included
        2. Pool sounds: group by pool name, pick one randomly from each pool
        3. Probability sounds: include if random roll passes probability threshold
        4. Enforce min/max constraints by adding/removing optional sounds

        Args:
            mix: List of sound configurations
            min_sounds: Minimum number of sounds to play
            max_sounds: Maximum number of sounds to play

        Returns:
            List of selected sound configurations
        """
        import random

        required = []
        optional_probability = []
        pools: Dict[str, List[Dict[str, Any]]] = {}

        # Categorize sounds
        for sound in mix:
            is_optional = sound.get("optional", False)
            pool_name = sound.get("pool")
            probability = sound.get("probability")

            if not is_optional:
                # Required sound - always include
                required.append(sound)
            elif pool_name:
                # Pool-based sound - group by pool name
                if pool_name not in pools:
                    pools[pool_name] = []
                pools[pool_name].append(sound)
            elif probability is not None:
                # Probability-based sound
                optional_probability.append(sound)
            else:
                # Optional without probability or pool - treat as 50% probability
                optional_probability.append({**sound, "probability": 0.5})

        selected = list(required)
        unselected_optional = []

        # Select one random sound from each pool
        for pool_name, pool_sounds in pools.items():
            chosen = random.choice(pool_sounds)
            selected.append(chosen)
            # Track unselected pool sounds for potential min enforcement
            for s in pool_sounds:
                if s is not chosen:
                    unselected_optional.append(s)

        # Process probability-based sounds
        for sound in optional_probability:
            prob = sound.get("probability", 0.5)
            if random.random() < prob:
                selected.append(sound)
            else:
                unselected_optional.append(sound)

        # Enforce max_sounds constraint
        if len(selected) > max_sounds:
            # Keep required sounds, randomly remove optional until at max
            required_set = set(id(s) for s in required)
            optional_in_selected = [s for s in selected if id(s) not in required_set]
            random.shuffle(optional_in_selected)

            # Calculate how many to remove
            excess = len(selected) - max_sounds
            to_remove = optional_in_selected[:excess]
            selected = [s for s in selected if s not in to_remove]

        # Enforce min_sounds constraint
        if len(selected) < min_sounds and unselected_optional:
            needed = min_sounds - len(selected)
            random.shuffle(unselected_optional)
            selected.extend(unselected_optional[:needed])

        return selected

    def play_mix(self, mix: List[Dict[str, Any]], min_sounds: int = 2, max_sounds: int = 6) -> tuple:
        """
        Start playing a mix of sounds with random selection.

        Each sound loops infinitely with its specified volume and fades in
        over 3 seconds. Optional sounds are selected based on probability
        and pool settings.

        Args:
            mix: List of sound configurations, each with:
                - url: freesound.org URL or local file path (required)
                - volume: 0-100, defaults to 100 (optional)
                - optional: bool, marks sound as optional (optional)
                - probability: 0.0-1.0, chance to play if optional (optional)
                - pool: string, pool name for group selection (optional)
            min_sounds: Minimum number of sounds to play
            max_sounds: Maximum number of sounds to play

        Returns:
            Tuple of (success: bool, selected_urls: List[str])
            - success: True if at least one sound started
            - selected_urls: List of URLs that were actually selected to play
        """
        if not self._player_cmd:
            print("WARNING: ffplay not found. Atmosphere requires ffplay (ffmpeg).")
            return False, []

        # Select which sounds to play
        selected_sounds = self.select_sounds(mix, min_sounds, max_sounds)

        started_any = False
        selected_urls = []

        for sound_config in selected_sounds:
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
                register_atmosphere_process(proc, url)
                started_any = True
                selected_urls.append(url)
            except Exception as e:
                print(f"WARNING: Failed to start atmosphere sound: {url}")
                print(f"         Reason: {e}")

        return started_any, selected_urls

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

    def is_url_playing(self, url: str) -> bool:
        """Check if a specific URL is currently playing."""
        return is_url_playing(url)

    def start_single(self, url: str, volume: int = 100, fade_in: bool = True) -> bool:
        """
        Start a single sound looping.

        Args:
            url: freesound.org URL or local file path
            volume: 0-100, defaults to 100
            fade_in: If True, fade in over 3 seconds

        Returns:
            True if sound started successfully
        """
        if not self._player_cmd:
            print("WARNING: ffplay not found. Atmosphere requires ffplay (ffmpeg).")
            return False

        # Don't start if already playing
        if is_url_playing(url):
            return True

        # Resolve to local path
        sound_path = self._resolve_sound_path(url)
        if not sound_path:
            return False

        # Build ffplay command with looping, volume, and optional fade-in
        cmd = [
            "ffplay",
            "-nodisp",           # No display window
            "-loglevel", "quiet",  # Suppress output
            "-loop", "0",        # Infinite loop
            "-volume", str(int(volume)),
        ]

        if fade_in:
            cmd.extend(["-af", f"afade=t=in:st=0:d={FADE_DURATION}"])

        cmd.append(str(sound_path))

        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            register_atmosphere_process(proc, url)
            return True
        except Exception as e:
            print(f"WARNING: Failed to start atmosphere sound: {url}")
            print(f"         Reason: {e}")
            return False

    def stop_single(self, url: str, fade_out: bool = True) -> bool:
        """
        Stop a single sound by URL.

        Args:
            url: freesound.org URL or local file path to stop
            fade_out: If True, attempt graceful fade out (note: ffplay doesn't
                     support runtime volume changes, so this just terminates)

        Returns:
            True if sound was stopped, False if not playing
        """
        global _url_to_process, _active_atmosphere_processes

        with _atmosphere_lock:
            if url not in _url_to_process:
                return False

            proc = _url_to_process[url]
            del _url_to_process[url]
            if proc in _active_atmosphere_processes:
                _active_atmosphere_processes.remove(proc)

        try:
            proc.terminate()
            return True
        except Exception:
            return False

    def set_volume(self, url: str, volume: int) -> bool:
        """
        Set volume for a currently playing sound using PulseAudio.

        Args:
            url: freesound.org URL or local file path
            volume: 0-100

        Returns:
            True if volume was set, False if sound not playing or pactl failed
        """
        with _atmosphere_lock:
            if url not in _url_to_process:
                return False
            proc = _url_to_process[url]
            pid = proc.pid

        # Use pactl to find and adjust the sink input for this PID
        try:
            # Get list of sink inputs
            result = subprocess.run(
                ["pactl", "list", "sink-inputs"],
                capture_output=True,
                text=True,
                timeout=2
            )
            if result.returncode != 0:
                return False

            # Parse output to find sink input with matching PID
            lines = result.stdout.split('\n')
            current_sink_input = None
            found_pid = False

            for line in lines:
                if line.startswith("Sink Input #"):
                    current_sink_input = line.split("#")[1].strip()
                    found_pid = False
                elif "application.process.id" in line and current_sink_input:
                    # Extract PID from line like: application.process.id = "12345"
                    try:
                        line_pid = int(line.split('"')[1])
                        if line_pid == pid:
                            found_pid = True
                            break
                    except (IndexError, ValueError):
                        pass

            if not found_pid or not current_sink_input:
                return False

            # Set volume (pactl uses percentage or absolute values)
            # Convert 0-100 to percentage string
            subprocess.run(
                ["pactl", "set-sink-input-volume", current_sink_input, f"{volume}%"],
                capture_output=True,
                timeout=2
            )
            return True

        except (subprocess.SubprocessError, FileNotFoundError):
            return False
