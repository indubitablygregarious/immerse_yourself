"""
Spotify Engine - Manages Spotify authentication and playback control
"""

import configparser
from pathlib import Path
from typing import Optional
import spotipy
from spotipy.oauth2 import SpotifyOAuth


class SpotifyEngine:
    """
    Manages Spotify authentication and playback control.

    This engine encapsulates all Spotify OAuth complexity and provides
    a simple interface for controlling music playback. It handles
    authentication automatically using credentials from .spotify.ini.

    Attributes:
        config_file: Path to Spotify configuration file
        spotify_client: Authenticated Spotify client instance
    """

    def __init__(self, config_file: str = ".spotify.ini"):
        """
        Initialize the Spotify Engine and authenticate.

        Args:
            config_file: Path to Spotify configuration file
                        (default: .spotify.ini in current directory)

        Raises:
            FileNotFoundError: If config file doesn't exist
            KeyError: If config file is missing required fields
        """
        self.config_file = config_file
        self.spotify_client: Optional[spotipy.Spotify] = None
        self._authenticate()

    def _authenticate(self) -> None:
        """
        Load Spotify credentials and create authenticated client.

        Reads configuration from .spotify.ini file with format:
        [DEFAULT]
        username = your_spotify_username
        client_id = your_app_client_id
        client_secret = your_app_client_secret
        redirectURI = http://localhost:8888/callback

        The authentication uses OAuth with the following scopes:
        - ugc-image-upload
        - user-read-playback-state
        - user-modify-playback-state
        - user-read-currently-playing
        - app-remote-control
        - streaming
        """
        # Verify config file exists
        if not Path(self.config_file).exists():
            raise FileNotFoundError(
                f"Spotify config file not found: {self.config_file}\n"
                "Please create .spotify.ini with your Spotify app credentials."
            )

        # Load configuration
        config = configparser.ConfigParser()
        config.read(self.config_file)

        try:
            username = config["DEFAULT"]["username"]
            spotify_id = config["DEFAULT"]["client_id"]
            spotify_secret = config["DEFAULT"]["client_secret"]
            redirect_uri = config["DEFAULT"]["redirectURI"]
        except KeyError as e:
            raise KeyError(
                f"Missing required field in {self.config_file}: {e}\n"
                "Required fields: username, client_id, client_secret, redirectURI"
            )

        # OAuth scope for playback control
        scope = (
            "ugc-image-upload user-read-playback-state "
            "user-modify-playback-state user-read-currently-playing "
            "app-remote-control streaming"
        )

        # Create OAuth object and get token
        oauth_object = SpotifyOAuth(
            client_id=spotify_id,
            client_secret=spotify_secret,
            redirect_uri=redirect_uri,
            scope=scope,
        )

        # Get access token (may open browser for auth if .cache doesn't exist)
        token_dict = oauth_object.get_access_token()
        token = token_dict["access_token"]

        # Create authenticated Spotify client
        self.spotify_client = spotipy.Spotify(auth=token)

    def play_context(self, context_uri: Optional[str]) -> bool:
        """
        Start playback of a Spotify context (playlist, album, or episode).

        Args:
            context_uri: Spotify URI in format:
                        - "spotify:playlist:XXXXXXXXXXXXXXXXXXXX" for playlists
                        - "spotify:album:XXXXXXXXXXXXXXXXXXXX" for albums
                        - "spotify:episode:XXXXXXXXXXXXXXXXXXXX" for podcast episodes
                        - None to skip playback

        Returns:
            True if playback started successfully, False otherwise

        Examples:
            >>> engine = SpotifyEngine()
            >>> engine.play_context("spotify:playlist:5Q8DWZnPe7o7GA96SARmOK")
            True
            >>> engine.play_context(None)
            False
        """
        if context_uri is None:
            return False

        if self.spotify_client is None:
            print("ERROR: Spotify client not authenticated")
            return False

        try:
            self.spotify_client.start_playback(context_uri=context_uri)
            return True
        except Exception as e:
            print(f"ERROR: Failed to start Spotify playback")
            print(f"       Context URI: {context_uri}")
            print(f"       Reason: {str(e)}")
            return False

    def stop(self) -> bool:
        """
        Pause current Spotify playback.

        Returns:
            True if playback was paused successfully, False otherwise
        """
        if self.spotify_client is None:
            print("ERROR: Spotify client not authenticated")
            return False

        try:
            self.spotify_client.pause_playback()
            return True
        except Exception as e:
            print(f"WARNING: Failed to pause Spotify playback: {str(e)}")
            return False

    def get_client(self) -> Optional[spotipy.Spotify]:
        """
        Get the raw Spotify client for advanced operations.

        Returns:
            Authenticated Spotify client instance, or None if not authenticated
        """
        return self.spotify_client

    def is_authenticated(self) -> bool:
        """
        Check if Spotify client is authenticated and ready.

        Returns:
            True if authenticated, False otherwise
        """
        return self.spotify_client is not None
