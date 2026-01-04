# Immerse Yourself

An interactive ambient environment system that transforms your space with synchronized music, smart lighting, and sound effects.

## What It Does

Immerse Yourself creates immersive environments by controlling:
- **Spotify playback** - Context-specific playlists for each scene
- **WIZ smart lights** - Dynamic color animations and effects synchronized to the environment
- **Sound effects** - Ambient audio triggers for scene transitions

Perfect for tabletop gaming (D&D, Pathfinder), ambient workspaces, or just setting the mood.

## Features

### 26+ Pre-Built Environments

**Battle Scenes** - High-intensity lighting with danger sounds
- Battle Dungeon, Desert, Forest, Water, Environment

**Taverns** - Cozy, social atmosphere
- Standard Tavern, Dark Tavern, Mountain Tavern

**Travel** - Journey ambiance
- Desert, Boat, Night Travel, Spooky Routes

**Towns & Places**
- Town (Day/Night), Library, Shop, Summer Festival

**Special**
- Camping, Chill, Dungeon, Win Dungeon, Chill Jazz, Clowny

### GUI Launcher

- **Tabbed interface** organized by category (Combat, Social, Exploration, Relaxation, Special)
- **Keyboard shortcuts** (Q, W, E, R...) - displayed as badges, remap per tab
- **Tab navigation** with Ctrl+PgUp/PgDn
- **Visual feedback** - active lights environment stays highlighted
- **Sound effects** can trigger without interrupting current lights
- **Stop button** to turn off lights
- **Scalable buttons** - expand automatically when window is resized
- **Clear button layout** with:
  - Shortcut key badge (top-left, random pastel background)
  - Centered name and wrapped description
  - Emoji indicators below button with pastel backgrounds:
    - 🔊 Sound (peach) | 🎵 Spotify (mint) | 💡 Lights (yellow)

## Requirements

### Hardware
- **WIZ smart bulbs** (3+ bulbs recommended)
  - Backdrop bulbs (ambiance)
  - Overhead bulbs (main lighting)
  - Battlefield bulbs (optional, for combat scenes)
- **Spotify Premium account** (required for playback control)

### Software
- Python 3.7+
- PyQt5
- Dependencies (see `requirements.txt`)

## Installation

### 1. Clone the repository
```bash
git clone <repository-url>
cd immerse_yourself
```

### 2. Install Python dependencies
```bash
pip install -r requirements.txt
```

### 3. Set up Spotify API
1. Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
2. Create a new app
3. Note your **Client ID** and **Client Secret**
4. Add `http://localhost:8888/callback` as a Redirect URI in app settings

### 4. Create configuration files

Create `.spotify.ini` in the project root:
```ini
[DEFAULT]
username = your_spotify_username
client_id = your_client_id_from_step_3
client_secret = your_client_secret_from_step_3
redirectURI = http://localhost:8888/callback
```

Create `.wizbulb.ini` in the project root:
```ini
[DEFAULT]
backdrop_bulbs = 192.168.1.165 192.168.1.159 192.168.1.160
overhead_bulbs = 192.168.1.161 192.168.1.162
battlefield_bulbs = 192.168.1.163 192.168.1.164
```
*(Replace with your actual bulb IP addresses)*

### 5. Find your WIZ bulb IP addresses
```bash
# Install pywizlight if not already installed
pip install pywizlight

# Discover bulbs on your network
python3 -c "import asyncio; from pywizlight import discovery; asyncio.run(discovery.discover_lights())"
```

### 6. First authentication
Run any environment script to complete Spotify OAuth:
```bash
python3 environments/tavern.py
```
A browser will open - log in to Spotify and authorize the app. This creates a `.cache` file for future sessions.

## Usage

### Launch the GUI (Recommended)
```bash
python3 launcher.py
```

- Click any environment button to start
- Press Q, W, E, R... keys for shortcuts (shown as badges on buttons, remap per tab)
- Use Ctrl+PgUp/PgDn to switch between category tabs
- **Lights environments** replace each other (new lights stop old lights)
- **Sound-only buttons** (📢) play sounds without stopping lights
- Press the STOP button or close window to stop lights

### Run scenes directly
```bash
python3 environments/tavern.py
python3 environments/battle_dungeon.py
```
Press Ctrl+C to stop.

## Troubleshooting

### "Failed to start" error
**Cause**: Missing configuration files
**Fix**: Ensure `.spotify.ini`, `.wizbulb.ini`, and `.cache` exist in project root

### Script hangs waiting for URL input
**Cause**: Spotify OAuth token expired or missing
**Fix**: Run script from terminal, complete browser authentication to regenerate `.cache`

### Lights don't respond
**Causes**:
- Bulbs are offline or unreachable
- Wrong IP addresses in `.wizbulb.ini`

**Fix**:
1. Verify bulbs are powered on
2. Re-run bulb discovery to check IPs
3. Update `.wizbulb.ini` with correct addresses

### No sound effects play
**Cause**: Sound effect files missing
**Fix**: Ensure .mp3/.wav/.opus files exist in project root (check individual scene scripts for filenames)

### Deprecation warnings
Warnings about `get_access_token(as_dict=True)` can be safely ignored - they're from the spotipy library.

## Customization

### Create Your Own Scene
1. Copy an existing scene from `environments/`:
   ```bash
   cp environments/tavern.py environments/my_scene.py
   ```

2. Edit the new file:
   - Change `playlist` to your Spotify playlist URI
   - Adjust `sound_effect` filename
   - Modify RGB color values
   - Adjust `cycletime` (lower = faster animations)

3. Restart the launcher to see your new scene

### Modify Light Behavior
Each scene script controls lights via:
- `cycletime`: Speed of animation changes (seconds)
- RGB values: `rgb=(red, green, blue)` where each is 0-255
- `brightness`: 0-255 scale
- WIZ scene IDs: Pre-built animations (e.g., `scene=7` for campfire)

## Architecture

### Project Structure
```
immerse_yourself/
├── launcher.py              # PyQt5 GUI launcher (tabbed interface)
├── engines/                 # Modular engine components
│   ├── sound_engine.py     # Sound playback (sync and async)
│   ├── spotify_engine.py   # Spotify API integration
│   └── lights_engine.py    # WIZ bulb control (fire-and-forget)
├── env_conf/               # YAML environment configurations
│   ├── tavern.yaml
│   ├── battle_dungeon.yaml
│   └── ...
├── config_loader.py        # YAML config loading and validation
├── lighting_daemon.py      # Background lighting process
├── environments/           # Legacy scene scripts
├── .spotify.ini            # Spotify credentials (not in git)
├── .wizbulb.ini            # Bulb IP addresses (not in git)
├── .cache                  # OAuth token cache (not in git)
├── requirements.txt        # Python dependencies
└── *.mp3, *.wav            # Sound effect files
```

### How It Works
1. Launcher loads YAML configs and displays tabbed button grid
2. Clicking a button starts an EngineRunner (QThread)
3. Engines run independently: sound (async), Spotify (sync), lights (async loop)
4. Lights use fire-and-forget commands for instant response
5. Sound-only configs overlay on running lights without stopping them

## Contributing

### Adding Scenes
Submit PRs with new environment scripts in `environments/`. Follow existing patterns:
- Use consistent variable names (`cycletime`, `playlist`, `sound_effect`)
- Group bulbs by backdrop/overhead/battlefield
- Include try/except for sound effects (allow graceful degradation)

### Reporting Issues
Please include:
- Full error messages / stack traces
- Contents of terminal output when running from CLI
- Python version and OS

## License

*(Add your license here)*

## Credits

Built with:
- [Spotipy](https://spotipy.readthedocs.io/) - Spotify API wrapper
- [pywizlight](https://github.com/sbidy/pywizlight) - WIZ smart bulb control
- [PyQt5](https://www.riverbankcomputing.com/software/pyqt/) - GUI framework
- [playsound3](https://pypi.org/project/playsound3/) - Audio playback
