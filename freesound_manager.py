"""
Freesound Manager - Downloads and caches sounds from freesound.org

Sounds are cached in the freesound.org/ directory with naming scheme:
    creator_idnumber_soundname.extension

Usage:
    from freesound_manager import FreesoundManager

    manager = FreesoundManager()

    # Get local path (downloads if needed)
    path, metadata = manager.get_sound("https://freesound.org/people/DJT4NN3R/sounds/449994/")

    # metadata contains: creator, sound_id, sound_name, filename
"""

import os
import re
import subprocess
from pathlib import Path
from typing import Optional, Tuple, Dict
from urllib.parse import urlparse
import requests


class FreesoundError(Exception):
    """Base exception for freesound operations."""
    pass


class FreesoundManager:
    """
    Manages downloading and caching of sounds from freesound.org.

    Sounds are cached locally to avoid repeated downloads.
    Uses yt-dlp for downloading audio files.
    """

    CACHE_DIR = "freesound.org"
    URL_PATTERN = re.compile(r'https?://freesound\.org/people/([^/]+)/sounds/(\d+)/?')

    def __init__(self, cache_dir: Optional[str] = None):
        """
        Initialize the FreesoundManager.

        Args:
            cache_dir: Override default cache directory (freesound.org/)
        """
        self.cache_dir = Path(cache_dir) if cache_dir else Path(self.CACHE_DIR)
        self._ensure_cache_dir()

    def _ensure_cache_dir(self) -> None:
        """Create cache directory if it doesn't exist."""
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def parse_url(self, url: str) -> Tuple[str, str]:
        """
        Parse a freesound.org URL to extract creator and sound ID.

        Args:
            url: Freesound URL like https://freesound.org/people/DJT4NN3R/sounds/449994/

        Returns:
            Tuple of (creator, sound_id)

        Raises:
            FreesoundError: If URL is not a valid freesound.org URL
        """
        match = self.URL_PATTERN.match(url)
        if not match:
            raise FreesoundError(f"Invalid freesound.org URL: {url}")
        return match.group(1), match.group(2)

    def _fetch_sound_name(self, url: str) -> str:
        """
        Fetch the sound name from the freesound.org webpage title.

        Args:
            url: Freesound URL

        Returns:
            Sound name extracted from page title
        """
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()

            # Extract title from HTML - format is usually "Sound Name - Freesound"
            title_match = re.search(r'<title>([^<]+)</title>', response.text, re.IGNORECASE)
            if title_match:
                title = title_match.group(1).strip()
                # Remove " - Freesound" suffix if present
                if " - Freesound" in title:
                    title = title.replace(" - Freesound", "")
                # Clean the title for use as filename
                return self._sanitize_filename(title)
        except Exception:
            pass

        # Fallback: use sound ID as name
        _, sound_id = self.parse_url(url)
        return f"sound_{sound_id}"

    def _sanitize_filename(self, name: str) -> str:
        """
        Sanitize a string for use as a filename.

        Args:
            name: Original name

        Returns:
            Sanitized filename-safe string
        """
        # Replace problematic characters with underscores
        sanitized = re.sub(r'[<>:"/\\|?*]', '_', name)
        # Replace spaces with underscores
        sanitized = sanitized.replace(' ', '_')
        # Remove leading/trailing underscores and dots
        sanitized = sanitized.strip('_.')
        # Collapse multiple underscores
        sanitized = re.sub(r'_+', '_', sanitized)
        return sanitized

    def _find_cached_file(self, creator: str, sound_id: str) -> Optional[Path]:
        """
        Find a cached file matching the creator and sound ID.

        Args:
            creator: Sound creator username
            sound_id: Freesound sound ID

        Returns:
            Path to cached file if found, None otherwise
        """
        pattern = f"{creator}_{sound_id}_*"
        matches = list(self.cache_dir.glob(pattern))
        if matches:
            return matches[0]
        return None

    def _download_sound(self, url: str, creator: str, sound_id: str, sound_name: str) -> Path:
        """
        Download a sound using yt-dlp.

        Args:
            url: Freesound URL
            creator: Sound creator username
            sound_id: Freesound sound ID
            sound_name: Name of the sound

        Returns:
            Path to downloaded file

        Raises:
            FreesoundError: If download fails
        """
        # Output template without extension - yt-dlp will add the correct one
        output_template = str(self.cache_dir / f"{creator}_{sound_id}_{sound_name}.%(ext)s")

        try:
            # Run yt-dlp to download the audio
            result = subprocess.run(
                [
                    "yt-dlp",
                    "--extract-audio",
                    "--audio-format", "best",
                    "--output", output_template,
                    "--no-playlist",
                    "--quiet",
                    url
                ],
                capture_output=True,
                text=True,
                timeout=120
            )

            if result.returncode != 0:
                raise FreesoundError(f"yt-dlp failed: {result.stderr}")

            # Find the downloaded file
            downloaded = self._find_cached_file(creator, sound_id)
            if not downloaded:
                raise FreesoundError("Download completed but file not found")

            return downloaded

        except subprocess.TimeoutExpired:
            raise FreesoundError("Download timed out")
        except FileNotFoundError:
            raise FreesoundError("yt-dlp not found. Install with: pip install yt-dlp")

    def get_sound(self, url: str) -> Tuple[Path, Dict[str, str]]:
        """
        Get a sound from freesound.org, downloading if necessary.

        Args:
            url: Freesound URL

        Returns:
            Tuple of (file_path, metadata_dict)
            metadata_dict contains: creator, sound_id, sound_name, filename

        Raises:
            FreesoundError: If URL is invalid or download fails
        """
        # Parse URL
        creator, sound_id = self.parse_url(url)

        # Check cache first
        cached = self._find_cached_file(creator, sound_id)
        if cached:
            # Extract sound name from filename
            filename = cached.name
            # Pattern: creator_id_soundname.ext
            parts = filename.split('_', 2)  # Split into max 3 parts
            if len(parts) >= 3:
                sound_name = parts[2].rsplit('.', 1)[0]  # Remove extension
            else:
                sound_name = f"sound_{sound_id}"

            return cached, {
                "creator": creator,
                "sound_id": sound_id,
                "sound_name": sound_name,
                "filename": filename
            }

        # Not cached - fetch name and download
        sound_name = self._fetch_sound_name(url)
        file_path = self._download_sound(url, creator, sound_id, sound_name)

        return file_path, {
            "creator": creator,
            "sound_id": sound_id,
            "sound_name": sound_name,
            "filename": file_path.name
        }

    def get_display_name(self, url: str) -> str:
        """
        Get display name for status bar.

        Args:
            url: Freesound URL

        Returns:
            Display string (sound name from title, already includes creator)
        """
        try:
            _, metadata = self.get_sound(url)
            # Convert underscores back to spaces for display
            # Title already includes "by creator" from freesound page
            return metadata["sound_name"].replace('_', ' ')
        except FreesoundError:
            return "freesound audio"

    def is_freesound_url(self, url: str) -> bool:
        """
        Check if a string is a valid freesound.org URL.

        Args:
            url: String to check

        Returns:
            True if valid freesound URL
        """
        return bool(self.URL_PATTERN.match(url))


# Convenience function for quick checks
def is_freesound_url(url: str) -> bool:
    """Check if a string is a valid freesound.org URL."""
    return bool(FreesoundManager.URL_PATTERN.match(url))
