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

    # Get category from tags - exact match with existing, or use tag as new category
    existing = ["combat", "exploration", "social"]
    category = select_category_from_tags(["rain", "storm"], existing)  # Returns "rain" (new category)
    category = select_category_from_tags(["combat", "war"], existing)  # Returns "combat" (existing)
"""

import os
import re
import subprocess
import configparser
from pathlib import Path
from typing import Optional, Tuple, Dict, List
from urllib.parse import urlparse
import requests


def _get_ignore_ssl_setting() -> bool:
    """Read the ignore_ssl_errors setting from settings.ini."""
    settings_path = Path("settings.ini")
    if settings_path.exists():
        config = configparser.ConfigParser()
        config.read(settings_path)
        return config.get("downloads", "ignore_ssl_errors", fallback="false").lower() == "true"
    return False


# Keyword mappings for sound-only configs (no lights/atmosphere)
# Maps category name -> list of keywords that should map to it
SOUND_CATEGORY_MAPPINGS = {
    "nature": ["birds", "bird", "insects", "insect", "frogs", "frog", "cicadas", "wildlife", "animal", "cricket", "owl", "songbird", "chirp", "chirping"],
    "water": ["water", "river", "stream", "rain", "drip", "splash", "waves", "brook", "waterfall", "pond", "lake", "ocean", "sea"],
    "fire": ["fire", "fireplace", "campfire", "crackling", "flames", "burning", "bonfire", "hearth", "ember"],
    "wind": ["wind", "breeze", "gust", "howling", "rustling", "leaves", "windy", "blowing"],
    "crowd": ["crowd", "people", "chatter", "murmur", "applause", "laughter", "talking", "voices", "audience", "bar", "pub", "tavern"],
    "footsteps": ["footsteps", "walking", "steps", "gravel", "floor", "boots", "running", "feet"],
    "reactions": ["gasp", "scream", "groan", "sigh", "cough", "sneeze", "bruh", "shock", "surprise", "yell", "shout"],
    "combat_sfx": ["sword", "weapon", "impact", "hit", "slash", "clang", "bone", "metal", "punch", "stab", "fight", "battle"],
    "ambient": ["ambient", "room", "tone", "hum", "drone", "atmosphere", "background", "loop", "ambience", "ambiance"],
    "creatures": ["monster", "creature", "growl", "howl", "roar", "beast", "wolf", "dragon", "demonic", "demon"],
}

# Environment category mappings (for configs with lights/atmosphere enabled)
# Currently not used for freesound downloads since they're sound-only
ENVIRONMENT_CATEGORY_MAPPINGS = {
    "tavern": ["tavern", "inn", "pub", "bar", "drinking", "medieval_interior", "ale", "mead"],
    "town": ["town", "city", "village", "market", "street", "urban", "festival", "square", "plaza"],
    "travel": ["travel", "journey", "path", "road", "walking", "hiking", "exploration", "adventure"],
    "forest": ["forest", "woods", "woodland", "grove", "jungle", "trees", "canopy", "thicket"],
    "coastal": ["beach", "ocean", "sea", "shore", "waves", "boat", "ship", "sailing", "coastal", "maritime"],
    "desert": ["desert", "sand", "dunes", "arid", "canyon", "mesa", "oasis", "sahara"],
    "mountain": ["mountain", "alpine", "peak", "cliff", "cave", "underground", "cavern", "heights"],
    "dungeon": ["dungeon", "crypt", "tomb", "ruins", "catacomb", "prison", "cell", "torture"],
    "combat": ["battle", "combat", "fight", "war", "clash", "skirmish", "siege", "attack"],
    "spooky": ["spooky", "creepy", "haunted", "eerie", "horror", "dark", "scary", "nightmare"],
    "weather": ["storm", "rain", "thunder", "snow", "wind", "blizzard", "lightning", "tempest"],
    "relaxation": ["chill", "calm", "peaceful", "meditation", "zen", "ambient", "lofi", "relax"],
    "celestial": ["heaven", "hell", "divine", "infernal", "otherworldly", "ethereal", "magical", "angelic", "demonic"],
}


def select_category_from_tags(tags: List[str], existing_categories: List[str] = None, default_category: str = "misc") -> str:
    """
    Select a category based on sound tags using keyword mappings.

    Priority:
    1. Exact match with existing categories
    2. Match via SOUND_CATEGORY_MAPPINGS keywords
    3. Fallback to default_category

    Args:
        tags: List of tags from the freesound page
        existing_categories: List of existing category names from loaded YAML configs
        default_category: Category to use if no match found (default: "misc")

    Returns:
        Category name from predefined mappings or existing categories
    """
    if not tags:
        return default_category

    existing_categories = existing_categories or []

    # Normalize for comparison
    normalized_tags = [t.lower().strip() for t in tags]
    normalized_existing = {cat.lower(): cat for cat in existing_categories}

    # First: Check for exact match with existing categories
    for tag in normalized_tags:
        if tag in normalized_existing:
            return normalized_existing[tag]  # Return original casing

    # Second: Check keyword mappings (for sound-only configs)
    for tag in normalized_tags:
        for category, keywords in SOUND_CATEGORY_MAPPINGS.items():
            if tag in keywords:
                return category

    # Fallback
    return default_category


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
            verify_ssl = not _get_ignore_ssl_setting()
            response = requests.get(url, timeout=10, verify=verify_ssl)
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
            # Build yt-dlp command
            cmd = [
                "yt-dlp",
                "--extract-audio",
                "--audio-format", "best",
                "--output", output_template,
                "--no-playlist",
                "--quiet",
            ]

            # Add SSL bypass flag if configured (for VPN/proxy environments)
            if _get_ignore_ssl_setting():
                cmd.append("--no-check-certificates")

            cmd.append(url)

            # Run yt-dlp to download the audio
            result = subprocess.run(
                cmd,
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
