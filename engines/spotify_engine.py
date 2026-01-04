"""
Spotify Engine - Manages Spotify authentication and playback control
"""

import configparser
import shutil
import subprocess
import threading
import time
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from typing import Optional, Callable, List, Dict, Any
from urllib.parse import urlparse, parse_qs
import spotipy
from spotipy.oauth2 import SpotifyOAuth


class SpotifyNoActiveDeviceError(Exception):
    """Raised when Spotify has no active playback device."""
    pass


class SpotifyNotRunningError(Exception):
    """Raised when Spotify is not running and cannot be started."""
    pass


class ReusableHTTPServer(HTTPServer):
    """HTTPServer that allows port reuse."""
    allow_reuse_address = True


class OAuthCallbackHandler(BaseHTTPRequestHandler):
    """HTTP request handler that captures OAuth callback."""

    auth_code: Optional[str] = None
    error: Optional[str] = None

    def do_GET(self):
        """Handle GET request from OAuth redirect."""
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)

        if 'code' in params:
            OAuthCallbackHandler.auth_code = params['code'][0]
            self._send_success_response()
        elif 'error' in params:
            OAuthCallbackHandler.error = params['error'][0]
            self._send_error_response(params['error'][0])
        else:
            self._send_error_response("No authorization code received")

    def _send_success_response(self):
        """Send success HTML response."""
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        html = """
        <html>
        <head><title>Spotify Authorization</title></head>
        <body style="font-family: sans-serif; text-align: center; padding: 50px;">
            <h1 style="color: #1DB954;">✓ Authorization Successful!</h1>
            <p>You can close this window and return to Immerse Yourself.</p>
            <script>setTimeout(function() { window.close(); }, 2000);</script>
        </body>
        </html>
        """
        self.wfile.write(html.encode())

    def _send_error_response(self, error: str):
        """Send error HTML response."""
        self.send_response(400)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        html = f"""
        <html>
        <head><title>Spotify Authorization Failed</title></head>
        <body style="font-family: sans-serif; text-align: center; padding: 50px;">
            <h1 style="color: #f44336;">✗ Authorization Failed</h1>
            <p>Error: {error}</p>
            <p>Please try again from the application.</p>
        </body>
        </html>
        """
        self.wfile.write(html.encode())

    def log_message(self, format, *args):
        """Suppress server logs."""
        pass


class GUISpotifyOAuth(SpotifyOAuth):
    """
    SpotifyOAuth subclass that handles authorization in a GUI-friendly way.

    Instead of prompting in the terminal, this:
    1. Starts a local HTTP server to catch the OAuth callback
    2. Opens the browser for authorization
    3. Automatically captures the auth code from the callback
    4. Falls back to a dialog if running in a GUI context
    """

    def __init__(self, *args, auth_dialog_callback: Optional[Callable] = None, **kwargs):
        """
        Initialize with optional GUI dialog callback.

        Args:
            auth_dialog_callback: Optional callback function that shows a dialog
                                  for manual URL entry. Called with (auth_url) and
                                  should return the redirect URL or None.
        """
        super().__init__(*args, **kwargs)
        self.auth_dialog_callback = auth_dialog_callback
        self._server = None
        self._server_thread = None

    def get_auth_response(self, open_browser=True):
        """
        Get authorization response using a local server or dialog.

        Overrides the default terminal-based prompt with a GUI-friendly flow.
        """
        # Reset state
        OAuthCallbackHandler.auth_code = None
        OAuthCallbackHandler.error = None

        # Parse redirect URI to get port
        parsed = urlparse(self.redirect_uri)
        port = parsed.port or 8888

        auth_url = self.get_authorize_url()

        # Try to start local server (ReusableHTTPServer allows port reuse)
        # Use 127.0.0.1 explicitly (Spotify requires this, not 'localhost')
        server_started = False
        try:
            self._server = ReusableHTTPServer(('127.0.0.1', port), OAuthCallbackHandler)
            self._server.timeout = 120  # 2 minute timeout
            server_started = True
        except OSError as e:
            print(f"Could not start OAuth server on port {port}: {e}")
            server_started = False

        if server_started:
            # Open browser and wait for callback
            if open_browser:
                webbrowser.open(auth_url)

            # Wait for the callback (blocking with timeout)
            try:
                while OAuthCallbackHandler.auth_code is None and OAuthCallbackHandler.error is None:
                    self._server.handle_request()
            except Exception as e:
                print(f"Server error: {e}")
            finally:
                self._server.server_close()

            if OAuthCallbackHandler.auth_code:
                return OAuthCallbackHandler.auth_code
            elif OAuthCallbackHandler.error:
                raise spotipy.SpotifyOauthError(f"Authorization failed: {OAuthCallbackHandler.error}")

        # Fallback: use dialog callback if available
        if self.auth_dialog_callback:
            redirect_url = self.auth_dialog_callback(auth_url)
            if redirect_url:
                # Extract code from redirect URL
                parsed = urlparse(redirect_url)
                params = parse_qs(parsed.query)
                if 'code' in params:
                    return params['code'][0]

        # Last resort: use terminal prompt (original behavior)
        return super().get_auth_response(open_browser=open_browser)


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

        # Create OAuth object using GUI-friendly subclass
        oauth_object = GUISpotifyOAuth(
            client_id=spotify_id,
            client_secret=spotify_secret,
            redirect_uri=redirect_uri,
            scope=scope,
        )

        # Get access token (automatically handles OAuth via local server)
        token_dict = oauth_object.get_access_token()
        token = token_dict["access_token"]

        # Create authenticated Spotify client
        self.spotify_client = spotipy.Spotify(auth=token)

    def play_context(self, context_uri: Optional[str]) -> bool:
        """
        Start playback of a Spotify context (playlist, album, or episode).

        Automatically enables shuffle and skips to next track for maximum
        variability across sessions.

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
            # Enable shuffle for variability
            try:
                self.spotify_client.shuffle(True)
            except Exception:
                pass  # Shuffle may fail if no active device yet

            # Start playback
            self.spotify_client.start_playback(context_uri=context_uri)

            # Skip to next track so each session starts differently
            try:
                self.spotify_client.next_track()
            except Exception:
                pass  # Next may fail briefly after starting playback

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

    def get_devices(self) -> List[Dict[str, Any]]:
        """
        Get list of available Spotify playback devices.

        Returns:
            List of device dictionaries with keys: id, name, type, is_active
        """
        if self.spotify_client is None:
            return []

        try:
            result = self.spotify_client.devices()
            return result.get("devices", [])
        except Exception as e:
            print(f"WARNING: Failed to get devices: {e}")
            return []

    def get_active_device(self) -> Optional[Dict[str, Any]]:
        """
        Get the currently active playback device.

        Returns:
            Device dictionary if active device exists, None otherwise
        """
        devices = self.get_devices()
        for device in devices:
            if device.get("is_active"):
                return device
        return None

    def transfer_to_device(self, device_id: str, start_playback: bool = False) -> bool:
        """
        Transfer playback to a specific device.

        Args:
            device_id: The Spotify device ID to transfer to
            start_playback: Whether to start playback after transfer

        Returns:
            True if transfer was successful, False otherwise
        """
        if self.spotify_client is None:
            return False

        try:
            self.spotify_client.transfer_playback(device_id, force_play=start_playback)
            return True
        except Exception as e:
            print(f"WARNING: Failed to transfer playback: {e}")
            return False

    def get_local_computer_device(self) -> Optional[Dict[str, Any]]:
        """
        Find a Spotify device running on THIS computer.

        Only returns devices that are:
        - Type "Computer"
        - Running on the local machine (checking hostname)

        Returns:
            Device dictionary if found, None otherwise
        """
        import socket
        hostname = socket.gethostname().lower()

        devices = self.get_devices()
        for device in devices:
            if device.get("type") == "Computer":
                device_name = device.get("name", "").lower()
                # Check if device name contains hostname or common local identifiers
                if (hostname in device_name or
                    device_name in hostname or
                    "this computer" in device_name or
                    device_name == hostname):
                    return device
        return None

    def get_remote_devices(self) -> List[Dict[str, Any]]:
        """
        Get list of remote Spotify devices (not this computer).

        Returns:
            List of remote device dictionaries
        """
        import socket
        hostname = socket.gethostname().lower()

        devices = self.get_devices()
        remote = []
        for device in devices:
            device_name = device.get("name", "").lower()
            device_type = device.get("type", "")

            # Skip if it looks like the local computer
            if device_type == "Computer":
                if (hostname in device_name or
                    device_name in hostname or
                    "this computer" in device_name):
                    continue

            remote.append(device)
        return remote

    def activate_local_device(self) -> bool:
        """
        Try to activate a local Spotify device for playback.

        Only activates devices running on THIS computer, not remote devices.

        Returns:
            True if a local device was activated, False otherwise
        """
        local_device = self.get_local_computer_device()
        if local_device:
            return self.transfer_to_device(local_device["id"], start_playback=False)
        return False

    def activate_any_device(self) -> bool:
        """
        Activate any available Spotify device (local or remote).

        Returns:
            True if a device was activated, False otherwise
        """
        devices = self.get_devices()
        if devices:
            return self.transfer_to_device(devices[0]["id"], start_playback=False)
        return False

    def play_context_with_device_check(self, context_uri: Optional[str]) -> bool:
        """
        Start playback, automatically handling 'no active device' errors.

        This method will:
        1. Try to play normally
        2. If no active device, try to activate a LOCAL device only
        3. Retry playback after activation

        Does NOT automatically activate remote devices - that should be a user choice.

        Args:
            context_uri: Spotify URI to play

        Returns:
            True if playback started successfully

        Raises:
            SpotifyNoActiveDeviceError: If no local device can be activated
        """
        if context_uri is None:
            return False

        if self.spotify_client is None:
            print("ERROR: Spotify client not authenticated")
            return False

        # First attempt
        try:
            return self._do_playback(context_uri)
        except spotipy.exceptions.SpotifyException as e:
            if "NO_ACTIVE_DEVICE" in str(e) or "No active device" in str(e):
                # Try to activate a LOCAL device only (not remote)
                if self.activate_local_device():
                    # Wait a moment for device to be ready
                    time.sleep(0.5)
                    # Retry playback
                    try:
                        return self._do_playback(context_uri)
                    except Exception as retry_e:
                        print(f"ERROR: Retry failed: {retry_e}")
                        raise SpotifyNoActiveDeviceError(
                            "No active Spotify device found and could not activate local device"
                        ) from retry_e
                else:
                    # No local device - signal caller to handle (may offer remote options)
                    raise SpotifyNoActiveDeviceError(
                        "No active local Spotify device found"
                    ) from e
            else:
                raise

    def _do_playback(self, context_uri: str) -> bool:
        """
        Internal method to perform actual playback.

        Args:
            context_uri: Spotify URI to play

        Returns:
            True if playback started successfully
        """
        # Enable shuffle for variability
        try:
            self.spotify_client.shuffle(True)
        except Exception:
            pass  # Shuffle may fail if no active device yet

        # Start playback
        self.spotify_client.start_playback(context_uri=context_uri)

        # Skip to next track so each session starts differently
        try:
            self.spotify_client.next_track()
        except Exception:
            pass  # Next may fail briefly after starting playback

        return True


def is_spotify_running() -> bool:
    """
    Check if Spotify is currently running on this system.

    Returns:
        True if Spotify process is found, False otherwise
    """
    try:
        # Linux: check for spotify process
        result = subprocess.run(
            ["pgrep", "-x", "spotify"],
            capture_output=True,
            timeout=5
        )
        if result.returncode == 0:
            return True

        # Also check for snap/flatpak versions
        result = subprocess.run(
            ["pgrep", "-f", "spotify"],
            capture_output=True,
            timeout=5
        )
        return result.returncode == 0
    except (subprocess.SubprocessError, FileNotFoundError):
        return False


def is_spotify_in_path() -> bool:
    """
    Check if Spotify executable is available in PATH.

    Returns:
        True if spotify command is found, False otherwise
    """
    # Check standard command
    if shutil.which("spotify"):
        return True

    # Check common Linux locations
    common_paths = [
        "/usr/bin/spotify",
        "/snap/bin/spotify",
        "/var/lib/flatpak/exports/bin/com.spotify.Client",
        str(Path.home() / ".local/bin/spotify"),
    ]

    for path in common_paths:
        if Path(path).exists():
            return True

    return False


def get_spotify_path() -> Optional[str]:
    """
    Get the path to the Spotify executable.

    Returns:
        Path to spotify executable, or None if not found
    """
    # Check standard command
    path = shutil.which("spotify")
    if path:
        return path

    # Check common Linux locations
    common_paths = [
        "/usr/bin/spotify",
        "/snap/bin/spotify",
        "/var/lib/flatpak/exports/bin/com.spotify.Client",
        str(Path.home() / ".local/bin/spotify"),
    ]

    for path in common_paths:
        if Path(path).exists():
            return path

    return None


def start_spotify() -> bool:
    """
    Start the Spotify application.

    Returns:
        True if Spotify was started successfully, False otherwise
    """
    spotify_path = get_spotify_path()
    if not spotify_path:
        return False

    try:
        # Start Spotify in background, detached from this process
        subprocess.Popen(
            [spotify_path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True
        )
        return True
    except Exception as e:
        print(f"ERROR: Failed to start Spotify: {e}")
        return False


def wait_for_spotify_device(engine: "SpotifyEngine", timeout: float = 10.0) -> bool:
    """
    Wait for a Spotify device to become available after starting Spotify.

    Args:
        engine: SpotifyEngine instance to check for devices
        timeout: Maximum time to wait in seconds

    Returns:
        True if a device became available, False if timeout
    """
    start_time = time.time()
    while time.time() - start_time < timeout:
        devices = engine.get_devices()
        if devices:
            return True
        time.sleep(0.5)
    return False
