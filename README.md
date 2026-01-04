# Immerse Yourself

An interactive ambient environment system that transforms your space with synchronized music, smart lighting, and sound effects.

![Immerse Yourself Screenshot](https://raw.githubusercontent.com/indubitablygregarious/immerse_yourself/refs/heads/main/immerse_yourself_screenshot.jpg)

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
- Desert, Boat, Night Travel, Spooky Routes, Dawn, Afternoon, Rainy, Storm

**Towns & Places**
- Town (Day/Night), Library, Shop, Summer Festival

**Relaxation**
- Chill, Beach Day, Beach Afternoon, Beach Night, Heaven

**Special**
- Camping, Dungeon, Win Dungeon, Chill Jazz, Clowny

**Intense**
- Hell (infernal hellscape with chaotic fire)

### GUI Launcher

- **File menu** (Alt+F) with Settings and Quit options
- **Settings dialog** with three configuration panels:
  - **Appearance** - Light/Dark/System theme
  - **Spotify** - API credentials and startup behavior:
    - Credentials: Client ID, Secret, Username, Redirect URI
    - Startup options: Ask / Start locally / Use remote device / Disabled
  - **WIZ Bulbs** - IP addresses for backdrop/overhead/battlefield bulb groups
  - Status indicators show [✓] configured or [!] needs setup
  - Built-in "Discover Bulbs" button scans your network for WIZ bulbs
  - Step-by-step setup instructions for new users
- **Left sidebar navigation** - categories listed vertically (15% width)
- **Dark mode support** - choose Light, Dark, or auto-detect from GNOME/KDE system theme
- **Search bar** (Ctrl+L) - fuzzy search across all environments by name, description, and tags
  - Only focuses on click or Ctrl+L (keyboard shortcuts work immediately)
  - Selected environment's button pulses green and gets focus
  - Press Enter twice: once to select search result, again to activate
- **Keyboard shortcuts** (Q, W, E, R...) - displayed as badges with white text and black outline
- **Category navigation** with Ctrl+PgUp/PgDn
- **Visual feedback** - active lights environment stays highlighted
- **Default transition sound** - `sounds/chill.wav` plays for any environment with lights or Spotify
- **Three stop buttons**:
  - **STOP LIGHTS** (red) - turn off light animations
  - **STOP SOUND** (orange, Spacebar) - stop all playing sound effects
  - **STOP SPOTIFY** (green) - pause Spotify playback
- **Scalable buttons** - expand automatically when window is resized
- **Clear button layout** with:
  - Background icon emoji (large, semi-transparent, scales with button size)
  - Shortcut key badge (top-left, random pastel background, scales with button size)
  - Centered environment name
  - Emoji indicators below button with pastel backgrounds:
    - 🔊 Sound (peach) | 🎵 Spotify (mint) | 💡 Lights (yellow)
  - Description box below indicators
- **Startup behavior**:
  - Auto-checks Spotify connection on launch
  - If Spotify ready, auto-plays "Travel" environment
  - If not, shows options: Start Spotify / Connect to remote device / Skip music
  - "Remember my choice" checkbox saves preference
- **Exit cleanup**:
  - Stops Spotify playback
  - Sets all lights to soft warm white

## Requirements

### Hardware (Optional)
- **WIZ smart bulbs** (3+ bulbs recommended) - for lighting effects
  - Backdrop bulbs (ambiance)
  - Overhead bulbs (main lighting)
  - Battlefield bulbs (optional, for combat scenes)
- **Spotify Premium account** - for music playback

*Note: The app works without either! Sound effects play independently, and you can configure Spotify/bulbs later via Settings.*

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

### 3. Configure via Settings (Recommended)

Launch the app and go to **File > Settings** to configure:

**Spotify** (optional - for music playback):
1. Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
2. Create a new app and note your **Client ID** and **Client Secret**
3. Add `http://127.0.0.1:8888/callback` as a Redirect URI in app settings
4. Enter credentials in Settings > Spotify panel
5. First environment click will open browser for OAuth authorization

**WIZ Bulbs** (optional - for lighting effects):
1. Click "Discover Bulbs on Network" in Settings > WIZ Bulbs panel
2. Copy discovered IPs into the appropriate bulb groups
3. Save settings

### Alternative: Manual Configuration Files

You can also create config files directly in the project root:

`.spotify.ini`:
```ini
[DEFAULT]
username = your_spotify_username
client_id = your_client_id
client_secret = your_client_secret
redirectURI = http://127.0.0.1:8888/callback
```

`.wizbulb.ini`:
```ini
[DEFAULT]
backdrop_bulbs = 192.168.1.165 192.168.1.159 192.168.1.160
overhead_bulbs = 192.168.1.161 192.168.1.162
battlefield_bulbs = 192.168.1.163 192.168.1.164
```

## Usage

### Launch the GUI (Recommended)
```bash
python3 launcher.py
```

- Click any environment button to start
- Press **Ctrl+L** to search environments (fuzzy match by name, description, tags)
- Press Q, W, E, R... keys for shortcuts (shown as badges on buttons, remap per category)
- Use Ctrl+PgUp/PgDn to switch between categories
- **Lights environments** replace each other (new lights stop old lights)
- **Sound-only buttons** (📢) play sounds without stopping lights
- Press **STOP LIGHTS** or close window to stop lights
- Press **Spacebar** or **STOP SOUND** button to stop playing sounds
- Press **Escape** to clear search and return focus to main window

### Run scenes directly
```bash
python3 environments/tavern.py
python3 environments/battle_dungeon.py
```
Press Ctrl+C to stop.

## Troubleshooting

### Music not playing
**Cause**: Spotify not configured or OAuth expired
**Fix**:
1. Go to File > Settings > Spotify
2. Ensure Client ID and Client Secret are entered
3. Click an environment with music - browser will open for authorization
4. If still failing, delete `.cache` file and re-authorize

### Lights don't respond
**Causes**:
- Bulbs not configured
- Bulbs are offline or unreachable
- Wrong IP addresses

**Fix**:
1. Go to File > Settings > WIZ Bulbs
2. Click "Discover Bulbs on Network"
3. Copy discovered IPs to appropriate groups
4. Verify bulbs are powered on and connected to WiFi

### No sound effects play
**Cause**: Sound effect files missing or audio player not available
**Fix**:
- Ensure .mp3/.wav/.opus files exist in `sounds/` directory
- Install ffmpeg for ffplay support: `sudo apt install ffmpeg`

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
│   ├── sound_engine.py     # Sound playback (stoppable via subprocess)
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
├── settings.ini            # User preferences (auto-created)
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
