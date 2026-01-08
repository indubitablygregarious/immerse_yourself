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
  - **Sound Engine**: Plays sound effects via subprocess (ffplay/paplay/aplay) for stoppable playback; `stop_all_sounds()` terminates all playing sounds; default "chill.wav" plays on all environment switches
  - **Spotify Engine**: Manages Spotify authentication and playback
    - GUI-friendly OAuth flow with local HTTP server (no terminal prompts)
    - Device detection: `get_local_computer_device()`, `get_remote_devices()`
    - Auto-start Spotify: `is_spotify_running()`, `start_spotify()`
    - Helper functions exported: `is_spotify_in_path()`, `wait_for_spotify_device()`
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
  - **File menu** (Alt+F): Settings (Ctrl+,) and Quit (Ctrl+Q)
  - **Settings dialog** (`SettingsDialog` class): Icon navigation on left, settings panels on right
    - **Appearance panel**: Light/Dark/System theme selection
    - **Spotify panel**: Configure API credentials and startup behavior
      - Credentials: username, client_id, client_secret, redirect_uri
      - **Startup behavior** setting (when Spotify not playing on this PC):
        - "Ask me what to do" - shows dialog with options
        - "Start Spotify on this PC" - auto-starts local Spotify
        - "Connect to another device" - uses remote device (e.g., Echo, phone)
        - "Run without music" - silently skips music
    - **WIZ Bulbs panel**: Configure bulb IPs with "Discover Bulbs" network scanner
    - Navigation items show status: `[✓]` configured, `[!]` needs setup
  - **Config managers**:
    - `SettingsManager` class: Reads/writes `settings.ini` (appearance preferences)
    - `SpotifyConfigManager` class: Reads/writes `.spotify.ini` (Spotify API credentials)
    - `WizBulbConfigManager` class: Reads/writes `.wizbulb.ini` (bulb IP addresses)
  - **Left sidebar navigation**: Categories in QListWidget (15% width), content in QStackedWidget
  - **Search bar** (Ctrl+L): Fuzzy search across ALL metadata fields
    - Searches: name, description, category, icon, intensity, tags, suitable_for
    - `FuzzySearchBar` class with substring matching
    - `ClickFocus` policy - only focuses on click or Ctrl+L (keyboard shortcuts work immediately)
    - Escape clears and unfocuses search
    - Selected button pulses green for 3 seconds (`_pulse_button` method)
    - **Enter twice to activate**: Search result gets focus, press Enter again to trigger
  - **Dark mode support**: Three options in Settings - Light, Dark, or Use OS setting
    - OS detection via `gsettings` (GNOME/GTK) and `kdeglobals` (KDE)
  - Uses Fusion style with custom dark palette when dark mode enabled
  - Per-category keyboard shortcuts (Q, W, E, R... remap when switching categories)
  - Ctrl+PgUp/PgDn to navigate between categories
  - **Default transition sound**: `sounds/chill.wav` plays for any environment with lights or Spotify
  - **Three stop buttons**:
    - STOP LIGHTS (red #f44336) - stops light animations
    - STOP SOUND (orange #FF9800, Spacebar shortcut with badge) - stops all playing sounds
    - STOP SPOTIFY (green #1DB954) - pauses Spotify playback
  - Scalable buttons that expand with window size (using `ButtonContainer` widget)
  - **Background icon**: Semi-transparent emoji from config's `icon` field, scales with button size (`IconButton` class, 50% of smaller dimension, min 24pt)
  - **Shortcut key badge**: Top-left corner with random pastel background, scales with button size (`OutlinedLabel` class, badge 18% of smaller dimension min 25px, font 50% of badge min 8pt)
  - Centered environment name (17px font)
  - Emoji indicators displayed below button (overlapping) with pastel backgrounds:
    - 🔊/📢 Sound (peach #FFCBA4)
    - 🎵 Spotify (mint #B4F0A8)
    - 💡 Lights (yellow #FFF9B0)
  - Description box below emoji indicators (11px font, bordered)
  - Distinct handling of sound-only (📢) vs full environment (🔊🎵💡) buttons
  - **Startup behavior** (`_check_startup_spotify` method):
    - On launch, checks if Spotify is configured and ready
    - If local device available, auto-plays "Travel" environment
    - If not, shows dialog based on settings (ask/start_local/use_remote/disabled)
    - Polls for Spotify readiness after starting, with 5-second delay before playback
  - **Exit cleanup** (`_cleanup_on_exit` method):
    - Stops Spotify playback
    - Sets all configured lights (backdrop/overhead/battlefield) to soft warm white

### Key Innovation: Background Lighting Persistence

The lighting daemon runs independently, allowing lights to continue animating while you switch between environments. Configuration updates are hot-swapped without turning lights off, resulting in smooth transitions.

**Smooth transitions**: When switching between environments, lights transition directly without flashing to warm white. The `_stop_lights(set_warm_white=False)` parameter prevents jarring flashes. Warm white only activates on explicit stops (STOP LIGHTS button) or app exit.

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

### Time-of-Day Variants

Most environments have morning/afternoon/night variants with different lighting and sounds:

**Naming Convention**: `{base_name}_{time}.yaml` where time is `morning`, `afternoon`, or `night`

**Examples**:
- `forest.yaml` (base) → `forest_morning.yaml`, `forest_afternoon.yaml`, `forest_night.yaml`
- `tavern.yaml` (base) → `tavern_morning.yaml`, `tavern_afternoon.yaml`, `tavern_night.yaml`

**Time-specific differences**:
| Time | Lighting | Brightness | Sounds | Cycletime |
|------|----------|------------|--------|-----------|
| Morning | Warm gold/pink, soft | Medium (130-210) | Dawn chorus, roosters | Slower (12-16s) |
| Afternoon | Bright, saturated | High (170-255) | Insects, busy activity | Medium (8-12s) |
| Night | Dark blue/purple, low | Low (20-100) | Crickets, owls, wolves | Slow (14-20s) |

**Environments with full time variants** (50 new configs):
- Outdoor: forest, ancient_ruins, graveyard, swamp, marketplace, travel_snow
- Town: town (morning/afternoon), marketplace (all three)
- Indoor: tavern, library, shop, blacksmith, temple, throne_room, prison
- Semi-outdoor: camping, travel_boat

### Common Fantasy Environments

Beyond travel and social scenes, these environments cover typical tabletop gaming locations:

| Environment | Icon | Category | Use For |
|-------------|------|----------|---------|
| Mine | ⛏️ | dungeon | Kobold encounters, rescue missions, resource quests |
| Wizard's Tower | 🧙 | celestial | Arcane research, wizard NPCs, magical discoveries |
| Castle Courtyard | 🏰 | town | Noble encounters, political intrigue, guard interactions |
| Arena | 🏟️ | combat | Gladiator fights, tournaments, public executions |
| Docks | ⚓ | town | Ship boarding, smugglers, coastal adventures |
| Crypt | 💀 | dungeon | Undead encounters, tomb raiding, necromancer lairs |
| Fey Wild | 🧚 | celestial | Fairy courts, enchanted locations, magical quests |
| Thieves' Guild | 🗡️ | dungeon | Criminal contacts, black market, heist planning |
| War Camp | ⚔️ | combat | Military briefings, mercenary camps, siege prep |
| Dragon's Lair | 🐉 | combat | Boss fights, treasure discovery, epic confrontations |
| Haunted Manor | 👻 | spooky | Ghost encounters, horror sessions, mystery investigations |
| Monastery | 🔔 | relaxation | Monk NPCs, healing rest, training montages |

### Battle Environments

Battle environments use Spotify playlists for music instead of atmosphere mixes. The atmosphere configurations are preserved as comments for future reference.

Available battle themes: `battle_dungeon`, `battle_desert`, `battle_forest`, `battle_water`, `battle_environment`

### Sound Variation System (sound_conf)

Entry sounds can use `sound_conf:` references for randomized variety:

- **`sound_conf/` directory**: Contains YAML files defining sound collections
- **Random selection**: One sound is randomly chosen at runtime from the collection
- **Mixed sources**: Collections can include local files AND freesound.org URLs

**Available sound_confs:**
| Reference | Description | Sounds |
|-----------|-------------|--------|
| `sound_conf:transition` | Whooshes, magic chimes, swooshes | 14 |
| `sound_conf:squeaky_door` | Door creaks and squeaks | 7 |
| `sound_conf:battle_intro` | Sword draws, war drums, danger stings | 8 |
| `sound_conf:camp_setup` | Digging, shoveling, setup sounds | 7 |
| `sound_conf:victory` | Fanfares, triumph sounds | 7 |
| `sound_conf:applause` | Crowd clapping, cheering | 7 |

**Usage in environment YAML:**
```yaml
engines:
  sound:
    enabled: true
    file: "sound_conf:squeaky_door"  # Randomly selects from collection
```

**sound_conf YAML format:**
```yaml
name: "Squeaky Door"
description: "Various door sounds"
sounds:
  - file: "sounds/dooropen.wav"      # Local file
  - url: "https://freesound.org/..."  # Freesound URL (auto-downloaded)
```

**Key files:**
- `sound_conf_resolver.py` - Resolution logic for sound_conf references
- `sound_conf/*.yaml` - Sound collection definitions

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
    file: "sound_conf:transition"  # Use sound_conf for variety (see sound_conf/ dir)

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
from engines import SoundEngine, stop_all_sounds
engine = SoundEngine()
engine.play("chill.wav")  # Blocking (uses ffplay/paplay/aplay subprocess)
engine.play_async("chill.wav")  # Non-blocking, stoppable
engine.play_async("chill.wav", on_complete=lambda: print("Done!"))  # With callback

# Stop all playing sounds
stopped_count = stop_all_sounds()  # Returns number of sounds stopped
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

- **ffplay/paplay/aplay**: Subprocess-based audio playback (preferred, stoppable); falls back to playsound3
- **playsound3**: Fallback audio player (cannot be stopped mid-playback)
- **spotipy**: Spotify API client for authentication and playback control
- **pywizlight**: Controls WIZ smart bulbs asynchronously
- **configparser**: Reads `.spotify.ini` and `.wizbulb.ini` config files

## Configuration Files

These files are NOT in git (see `.gitignore`) and can be configured via **File > Settings** or created manually:

### `.spotify.ini`
Contains Spotify API credentials. Optional - for music playback.
**Configure via:** Settings > Spotify panel (or create manually)
```ini
[DEFAULT]
username = <spotify_username>
client_id = <spotify_app_client_id>
client_secret = <spotify_app_client_secret>
redirectURI = http://127.0.0.1:8888/callback
```
Managed by `SpotifyConfigManager` class in `launcher.py`.

### `.wizbulb.ini`
Contains IP addresses of WIZ smart bulbs. Optional - for light control.
**Configure via:** Settings > WIZ Bulbs panel (includes "Discover Bulbs" button)
```ini
[DEFAULT]
backdrop_bulbs = 192.168.1.165 192.168.1.159 192.168.1.160
overhead_bulbs = 192.168.1.161 192.168.1.162
battlefield_bulbs = 192.168.1.163 192.168.1.164
```
Managed by `WizBulbConfigManager` class in `launcher.py`.

### `.cache`
Spotify OAuth token cache (auto-generated by spotipy). Created after first authentication. If expired/missing, clicking an environment with Spotify opens browser for re-authorization.

### `settings.ini`
User preferences (auto-created on first launch). Managed by `SettingsManager` class.
```ini
[appearance]
theme = light  # Options: light, dark, system

[spotify]
auto_start = ask  # Options: ask, start_local, use_remote, disabled
startup_playlist =  # Optional playlist URI to play on startup
```

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
When cloning or creating a new checkout:
1. Run `python3 launcher.py` - the app works immediately for sound effects
2. Go to **File > Settings > Spotify** to configure music (optional)
3. Go to **File > Settings > WIZ Bulbs** to configure lighting (optional)
4. Click "Discover Bulbs" to find WIZ bulbs on your network

Alternatively, copy config files from an existing checkout:
- `.spotify.ini` - Spotify API credentials
- `.wizbulb.ini` - Bulb IP addresses
- `.cache` - OAuth token (or re-authenticate via browser)

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
1. **Spotify not working**: Check File > Settings > Spotify for credentials
   - Status shows `[!]` if not configured
   - First use opens browser for OAuth authorization
   - If `.cache` expires, delete it and re-authorize

2. **Lights not responding**: Check File > Settings > WIZ Bulbs
   - Use "Discover Bulbs" to find bulbs on network
   - Verify bulbs are on and connected to WiFi
   - Status shows `[!]` if no bulbs configured

3. **Silent failures with lights**: WIZ bulbs may be unreachable on the network
   - Solution: Check bulb IP addresses are correct and bulbs are powered on

4. **Deprecation warning about `get_access_token(as_dict=True)`**: This is a spotipy library warning, can be ignored for now

## Known Issues / Quirks

- Sound effects must exist as .wav/.mp3/.opus files; missing files are logged but don't crash
- The WIZ bulb library may fail silently on network connection issues—errors logged via callbacks
- Spotify OAuth tokens expire periodically; if authentication fails, delete `.cache` and re-authenticate
- Sound-only configs can run alongside lights configs; only lights configs replace each other
- Button shortcuts are per-tab; same key triggers different buttons on different tabs
- Sound playback uses subprocess (ffplay/paplay/aplay) for stoppability; spacebar stops all sounds
- If no subprocess player is available, falls back to playsound3 (sounds cannot be stopped)
