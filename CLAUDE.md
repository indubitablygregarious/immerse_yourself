# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is the "Immerse Yourself" project—an interactive ambient environment system that combines:
- **Spotify music playback**: Different playlists for various scenes/moods
- **Smart light control**: WIZ smart bulbs that respond to scene context with synchronized color and animation patterns
- **Sound effects**: Local audio files that play when scenes are triggered

Each scene is a standalone Python script that orchestrates both music and lighting for a specific ambiance (taverns, dungeons, travel routes, battles, etc).

## Architecture

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

These files are NOT in git (see `.gitignore`):

### `.spotify.ini`
```ini
[DEFAULT]
username = <spotify_username>
client_id = <spotify_app_client_id>
client_secret = <spotify_app_client_secret>
redirectURI = http://localhost:8888/callback
```

### `.wizbulb.ini`
```ini
[DEFAULT]
backdrop_bulbs = 192.168.1.165 192.168.1.159 192.168.1.160
overhead_bulbs = 192.168.1.161 192.168.1.162
battlefield_bulbs = 192.168.1.163 192.168.1.164
```

## Common Development Tasks

### Run a Scene
```bash
python3 tavern.py
```

Each scene is executable directly. It will:
1. Load configuration
2. Connect to Spotify and start playback
3. Connect to all configured smart bulbs
4. Enter an infinite animation loop

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

- **Async loops**: All scenes use `asyncio.run_until_complete()` for concurrent light updates
- **Config reading**: Always read `.spotify.ini` first, then `.wizbulb.ini`
- **Error handling**: Bare `except:` blocks for missing sound files are standard
- **Randomization**: Use `random.random()` for variance in brightness, colors, and animation speeds
- **Time control**: `time.sleep()` is used inside async loops for timing animations
- **Bulb grouping**: Initialize backdrop, overhead, and battlefield bulbs separately for independent control

## Known Issues / Quirks

- Sound effects must exist as .wav or .opus files; missing files are silently caught with a try/except
- The WIZ bulb library may fail silently on network connection issues—ensure bulbs are on and reachable
- `asyncio.get_event_loop()` is deprecated in newer Python versions; future refactors should use `asyncio.run()`
- IP addresses are hardcoded in scenes; consider moving all bulb configs to `.wizbulb.ini` for more flexibility
