"""
Immerse Yourself - Engine Modules

This package contains the three core engines for the Immerse Yourself system:
- SoundEngine: Plays sound effects
- SpotifyEngine: Manages Spotify playback
- LightsEngine: Controls WIZ smart bulbs with animations
"""

from .sound_engine import SoundEngine, stop_all_sounds
from .spotify_engine import (
    SpotifyEngine,
    SpotifyNoActiveDeviceError,
    SpotifyNotRunningError,
    is_spotify_running,
    is_spotify_in_path,
    get_spotify_path,
    start_spotify,
    wait_for_spotify_device,
)
from .lights_engine import LightsEngine, LightBulbGroup

__all__ = [
    "SoundEngine",
    "stop_all_sounds",
    "SpotifyEngine",
    "SpotifyNoActiveDeviceError",
    "SpotifyNotRunningError",
    "is_spotify_running",
    "is_spotify_in_path",
    "get_spotify_path",
    "start_spotify",
    "wait_for_spotify_device",
    "LightsEngine",
    "LightBulbGroup",
]
