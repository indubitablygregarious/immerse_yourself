# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is the "Immerse Yourself" project—an interactive ambient environment system that combines:
- **Spotify music playback**: Different playlists for various scenes/moods
- **Smart light control**: WIZ smart bulbs that respond to scene context with synchronized color and animation patterns
- **Sound effects**: Local audio files that play when scenes are triggered

## Current Architecture (Refactored)

The project has been refactored from individual Python scripts into a modular engine-based architecture:

### Core Components

- **Three Engines** (`engines/` directory):
  - **Sound Engine**: Plays sound effects with graceful error handling
  - **Spotify Engine**: Manages Spotify authentication and playback
  - **Lights Engine**: Controls WIZ bulbs with async animations and hot-swapping support

- **YAML Configuration** (`env_conf/` directory):
  - Environments defined in YAML files instead of Python scripts
  - See `env_conf/README.md` for complete schema documentation
  - Example configs: `tavern.yaml`, `battle_dungeon.yaml`, `chill.yaml`, etc.

- **Lighting Daemon** (`lighting_daemon.py`):
  - Separate process for background light animation
  - Keeps lights running while switching environments (no flicker/blackout)
  - Communicates via JSON over stdin/stdout
  - Hot-swaps animation configs without restarting

- **Config Loader** (`config_loader.py`):
  - Loads and validates YAML environment configurations
  - Caching and discovery of all configs
  - Category filtering

- **Launcher** (`launcher.py`):
  - PyQt5 GUI for launching environments
  - Tabbed interface organized by category (Combat, Social, Exploration, etc.)
  - **Dark mode support**: Detects GNOME/KDE system theme via `gsettings` and `kdeglobals`
  - Uses Fusion style with custom dark palette when dark mode detected
  - Per-tab keyboard shortcuts (Q, W, E, R... remap when switching tabs)
  - Ctrl+PgUp/PgDn to navigate between tabs
  - Stop button for stopping lights
  - Scalable buttons that expand with window size (using `ButtonContainer` widget)
  - **Background icon**: Large semi-transparent emoji from config's `icon` field (`IconButton` class)
  - **Shortcut key badge**: Top-left corner with random pastel background, white text with black outline (`OutlinedLabel` class)
  - Centered environment name (17px font)
  - Emoji indicators displayed below button (overlapping) with pastel backgrounds:
    - 🔊/📢 Sound (peach #FFCBA4)
    - 🎵 Spotify (mint #B4F0A8)
    - 💡 Lights (yellow #FFF9B0)
  - Description box below emoji indicators (11px font, bordered)
  - Distinct handling of sound-only (📢) vs full environment (🔊🎵💡) buttons

### Key Innovation: Background Lighting Persistence

The lighting daemon runs independently, allowing lights to continue animating while you switch between environments. Configuration updates are hot-swapped without turning lights off, resulting in smooth transitions.

### Performance Optimizations

The lights engine uses **fire-and-forget** for bulb commands:
- `LightBulbGroup.apply_pilot()` creates async tasks without awaiting responses
- Bulb commands are sent instantly; errors are logged via callbacks
- Uses `asyncio.sleep()` (not `time.sleep()`) to allow event loop to process tasks
- Light initialization is instant (no cycletime-based delays)

### Sound-Only vs Lights Configs

The launcher handles these differently:
- **Lights configs**: Button stays highlighted, lights runner persists until stopped or replaced
- **Sound-only configs**: Button highlights while sound plays, then reverts to showing active lights
- Sound plays asynchronously via `SoundEngine.play_async()` with completion callback
- Triggering a sound-only config does NOT stop running lights

## Architecture (Detailed)

See `ARCHITECTURE.md` for complete architectural documentation including:
- Component descriptions and APIs
- Data flow diagrams
- Design decisions and rationale
- IPC protocol specification
- Testing strategy

## Common Development Tasks (New Architecture)

### Using the Makefile

```bash
make help           # Show all available commands
make install        # Install dependencies
make validate-configs  # Validate all YAML configs
make run            # Start launcher
make daemon         # Start lighting daemon manually (for debugging)
make test           # Run tests (when available)
make clean          # Remove cache files
```

### Creating a New Environment

1. Create a new YAML file in `env_conf/`:

```yaml
name: "My Custom Environment"
category: "special"
description: "Brief description"
icon: "🎮"  # Emoji displayed as semi-transparent background on button

metadata:
  tags: ["custom", "experimental"]
  intensity: "medium"

engines:
  sound:
    enabled: true
    file: "your_sound.wav"

  spotify:
    enabled: true
    context_uri: "spotify:playlist:YOUR_PLAYLIST_ID"

  lights:
    enabled: true
    animation:
      cycletime: 12
      groups:
        backdrop:
          type: "rgb"
          rgb:
            base: [128, 128, 128]
            variance: [20, 20, 20]
          brightness:
            min: 100
            max: 255
```

2. Validate the config:

```bash
make validate-configs
# or
python3 -c "from config_loader import ConfigLoader; ConfigLoader('env_conf').load('your_file.yaml')"
```

3. Restart the launcher to see your new environment

### Testing the Engines Individually

**Sound Engine:**
```python
from engines import SoundEngine
engine = SoundEngine()
engine.play("chill.wav")  # Blocking
engine.play_async("chill.wav")  # Non-blocking, fire-and-forget
engine.play_async("chill.wav", on_complete=lambda: print("Done!"))  # With callback
```

**Spotify Engine:**
```python
from engines import SpotifyEngine
engine = SpotifyEngine()
engine.play_context("spotify:playlist:XXXX...")
```

**Lights Engine:**
```python
import asyncio
from engines import LightsEngine

config = {
    "cycletime": 10,
    "groups": {
        "backdrop": {
            "type": "rgb",
            "rgb": {"base": [255, 0, 0], "variance": [20, 20, 20]},
            "brightness": {"min": 100, "max": 200}
        }
    }
}

async def test():
    engine = LightsEngine()
    await engine.start(config)
    await asyncio.sleep(30)  # Run for 30 seconds
    await engine.stop()

asyncio.run(test())
```

### Testing the Lighting Daemon

Start the daemon manually:
```bash
python3 lighting_daemon.py
```

Send commands via stdin (JSON, one per line):
```json
{"command": "update_animation", "config": {"cycletime": 5, "groups": {...}}}
{"command": "ping"}
{"command": "stop"}
```

Watch stdout for responses:
```json
{"type": "status", "message": "Animation started"}
{"type": "error", "message": "Bulb unreachable", "timestamp": "..."}
```

### Modifying Light Behavior

Edit the YAML config file for an environment:

- **Speed up/slow down**: Change `cycletime` (lower = faster)
- **Change colors**: Modify `rgb.base` values `[R, G, B]`
- **More variety**: Increase `rgb.variance` values
- **Brightness**: Adjust `brightness.min` and `brightness.max`
- **Flash rate**: Change `flash.probability` (0.0 to 1.0)
- **Flash color**: Modify `flash.color` `[R, G, B]`

## Legacy Architecture (Pre-Refactoring)

### Scene Structure
Each scene follows a consistent pattern:
1. **Configuration loading** (`.spotify.ini` for Spotify auth, `.wizbulb.ini` for bulb IP addresses)
2. **Spotify setup**: Authenticate with OAuth and prepare to play a scene-specific playlist
3. **Bulb initialization**: Create wizlight objects grouped by location (backdrop, overhead, battlefield)
4. **Async loop**: Continuously animate lights with random variations while music plays

### Light Bulb Groups
Bulbs are organized into three groups (configured in `.wizbulb.ini`):
- `backdrop_bulbs`: Set scenes and general ambiance
- `overhead_bulbs`: Brighten with specific colors, represent the main light source
- `battlefield_bulbs`: Low-brightness dramatic lighting for combat scenarios

### Scene Variations
Scenes are organized by context and time of day:
- **Battle scenes**: `battle_*.py` - High-speed light flashing (cycletime 2-3s) with danger sound
- **Travel scenes**: `travel_*.py` - Medium speed (cycletime 4-6s), various environments (desert, boat, spooky, night)
- **Town/social**: `tavern.py`, `town.py`, `library.py`, `shop.py` - Slower cycles, comfortable lighting
- **Special**: `camping.py`, `chill.py`, `win_dungeon.py`, `dungeon.py`

The `cycletime` variable controls how fast lights animate; lower values = faster changes.

## Key Dependencies

- **playsound3**: Plays local .wav and .opus sound effect files
- **spotipy**: Spotify API client for authentication and playback control
- **pywizlight**: Controls WIZ smart bulbs asynchronously
- **configparser**: Reads `.spotify.ini` and `.wizbulb.ini` config files

## Configuration Files

These files are NOT in git (see `.gitignore`) and must be present in the project root:

### `.spotify.ini`
Contains Spotify API credentials. Required for music playback.
```ini
[DEFAULT]
username = <spotify_username>
client_id = <spotify_app_client_id>
client_secret = <spotify_app_client_secret>
redirectURI = http://localhost:8888/callback
```

### `.wizbulb.ini`
Contains IP addresses of WIZ smart bulbs. Required for light control.
```ini
[DEFAULT]
backdrop_bulbs = 192.168.1.165 192.168.1.159 192.168.1.160
overhead_bulbs = 192.168.1.161 192.168.1.162
battlefield_bulbs = 192.168.1.163 192.168.1.164
```

### `.cache`
Spotify OAuth token cache (auto-generated by spotipy). This file is created after first authentication and prevents repeated OAuth prompts. If missing, the first script run will open a browser for Spotify login.

## Common Development Tasks

### Using the GUI Launcher (Recommended)
```bash
python3 launcher.py
```

The launcher provides:
- Tabbed grid layout of all available environments (organized by category)
- Keyboard shortcuts (Q-N keys) displayed as badges, remap per tab
- Visual feedback showing which environment is active
- Scalable buttons that grow with window size
- Automatic process management (stops previous lights when starting new lights config)

### Run a Scene Directly
```bash
python3 environments/tavern.py
```

Each scene is executable directly. It will:
1. Load configuration
2. Connect to Spotify and start playback
3. Connect to all configured smart bulbs
4. Enter an infinite animation loop

### First-Time Setup for New Checkouts
When cloning or creating a new checkout, you need three config files in the project root:
1. Copy `.spotify.ini` from an existing checkout
2. Copy `.wizbulb.ini` from an existing checkout
3. Copy `.cache` from an existing checkout OR run any environment script once to authenticate via browser

### Modify Light Behavior
Light behavior is controlled by:
- **Color values**: RGB tuples (e.g., `rgb=(128, 100, 128)`)
- **Brightness**: 0-255 scale
- **Scene ID**: Preset animated scenes from WIZ bulbs (e.g., scene=7 for campfire)
- **Speed**: Animation speed parameter (1-200)
- **Cycletime**: Sleep duration between updates

Example modifications:
- Change `cycletime` to speed up/slow down animations
- Adjust RGB values to shift color palette
- Modify `flash_variance` to change intensity of flashes
- Switch between `PilotBuilder(scene=X)` and `PilotBuilder(rgb=(...))` for different effects

### Add a New Scene
1. Copy an existing similar scene (e.g., `tavern.py` for social, `battle_dungeon.py` for combat)
2. Update the `playlist` variable with a new Spotify URI
3. Update the `sound_effect` filename
4. Adjust color values, cycletime, and other lighting parameters
5. Name the file descriptively and make it executable

### Testing Scene Logic Without Full Setup
To test light color/animation logic without Spotify or actual bulbs:
```python
# Comment out or mock these lines:
# spotify.start_playback(context_uri=playlist)
# await light_bulb.turn_on(...)
```

## Code Patterns to Maintain

- **Fire-and-forget bulb commands**: Use `asyncio.create_task()` without awaiting for bulb operations
- **Async sleep only**: Use `await asyncio.sleep()` (never `time.sleep()`) in async contexts to allow event loop to process tasks
- **Config reading**: Always read `.spotify.ini` first, then `.wizbulb.ini`
- **Error handling**: Use callbacks for async error logging, bare `except:` for sound files
- **Randomization**: Use `random.random()` for variance in brightness, colors, and animation speeds
- **Bulb grouping**: Initialize backdrop, overhead, and battlefield bulbs separately for independent control
- **QThread safety**: Keep references to QThread objects until `finished` signal to avoid "destroyed while running" crashes
- **Sound callbacks**: Use `play_async(file, on_complete=callback)` when you need to know when sound finishes

## Debugging

### Launcher Output
The launcher runs environment scripts as subprocesses. As of the latest update, stdout/stderr are passed through to the terminal, so you can see all errors and stack traces when running `python3 launcher.py` from the command line.

If errors are suppressed, check `launcher.py:98-104` to ensure `stdout=subprocess.PIPE` and `stderr=subprocess.PIPE` are NOT set (they should be removed or commented out).

### Common Issues
1. **Missing config files**: Launcher will show "Failed to start" and environment scripts will crash immediately
   - Solution: Ensure `.spotify.ini`, `.wizbulb.ini`, and `.cache` exist in project root

2. **OAuth prompts block the GUI**: If `.cache` is missing or expired, scripts will wait for interactive browser authentication
   - Solution: Run any environment script once from terminal to complete OAuth, then `.cache` will be created

3. **Silent failures with lights**: WIZ bulbs may be unreachable on the network
   - Solution: Check bulb IP addresses are correct and bulbs are powered on

4. **Deprecation warning about `get_access_token(as_dict=True)`**: This is a spotipy library warning, can be ignored for now

## Known Issues / Quirks

- Sound effects must exist as .wav/.mp3/.opus files; missing files are logged but don't crash
- The WIZ bulb library may fail silently on network connection issues—errors logged via callbacks
- Spotify OAuth tokens expire periodically; if authentication fails, delete `.cache` and re-authenticate
- Sound-only configs can run alongside lights configs; only lights configs replace each other
- Button shortcuts are per-tab; same key triggers different buttons on different tabs
