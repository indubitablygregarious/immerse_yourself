# Environment Launcher Setup Guide

## Overview

The `launcher.py` is a PyQt5-based GUI application that manages all your environment scripts. It allows you to:
- Launch any environment with a single click or keyboard shortcut
- Run only one environment at a time (previous environment automatically stops)
- See which environment is currently running (highlighted button)
- Access all 27 environments from a QWERTY-style keyboard grid

## Installation

### 1. Install Dependencies

First, make sure you have the required Python packages:

```bash
pip install -r requirements.txt
```

Or install individually:
```bash
pip install PyQt5 spotipy pywizlight playsound3
```

### 2. Verify Setup

The project should now have this structure:
```
/home/pete/immerse_yourself/
├── launcher.py              # Main GUI application
├── environments/            # Directory containing all environment scripts
│   ├── battle_desert.py
│   ├── tavern.py
│   ├── travel.py
│   └── ... (27 total)
├── .spotify.ini             # Spotify auth config (create if missing)
├── .wizbulb.ini             # Smart bulb config (create if missing)
├── *.wav, *.opus            # Sound effect files
└── LAUNCHER_SETUP.md        # This file
```

## Running the Launcher

### Basic Launch

```bash
python3 launcher.py
```

Or directly (if made executable):
```bash
./launcher.py
```

### What You'll See

A window titled "Immerse Yourself - Environment Launcher" with:
- **3 rows of buttons** matching the QWERTY keyboard layout:
  - Row 1: Q W E R T Y U I O P (10 environments)
  - Row 2: A S D F G H J K L ; (10 environments)
  - Row 3: Z X C V B N (6 environments)
- **Total: 26 keyboard shortcuts** for the first 26 alphabetical environments
- **27th environment** (travel.py) accessible via mouse click only
- **Status bar** at the bottom showing which environment is currently running

## Using the Launcher

### Launch an Environment

**Method 1: Keyboard Shortcut**
- Press any key Q-P, A-L, or Z-M to launch that environment
- Window must have focus for shortcuts to work
- Example: Press `T` to launch the environment in row 1, column 5

**Method 2: Mouse Click**
- Click any button to launch that environment
- Each button shows:
  - Environment display name (e.g., "Battle Dungeon")
  - Keyboard shortcut in parentheses (e.g., "(B)")

### Visual Feedback

- **Active Environment**: Button is highlighted in **green** with white text
- **Inactive Environments**: Buttons are light gray with black text
- **Status Bar**: Shows "Running: [Environment Name]"

### Switch Environments

- Simply press another key or click another button
- The current environment automatically stops
- The new environment starts immediately
- Active button highlighting updates

### Stop Current Environment

**Option 1**: Launch another environment (stops current one)

**Option 2**: Close the window
- A dialog will ask "Environment is running. Stop and exit?"
- Choose "Yes" to stop and close

## Keyboard Layout Reference

The button layout matches your keyboard:

```
Row 1 (Q row):  [Q] [W] [E] [R] [T] [Y] [U] [I] [O] [P]
Row 2 (A row):  [A] [S] [D] [F] [G] [H] [J] [K] [L] [;]
Row 3 (Z row):  [Z] [X] [C] [V] [B] [N]
```

Environment names are sorted alphabetically, so:
- Q = battle_desert.py
- W = battle_dungeon.py
- E = battle_environment.py
- (and so on...)

## Troubleshooting

### "Failed to start: [Environment Name]"

**Cause**: Environment script couldn't be launched

**Solutions**:
1. Verify `.spotify.ini` and `.wizbulb.ini` exist in the project root
2. Check that Spotify credentials are correct in `.spotify.ini`
3. Check that smart bulb IP addresses are correct in `.wizbulb.ini`
4. Ensure sound effect files exist (*.wav and *.opus files)
5. Verify all environments are in the `environments/` directory

### Keyboard Shortcuts Don't Work

**Cause**: Window doesn't have focus

**Solution**: Click the launcher window to give it focus, then try again

### Sound Effects Not Playing

**Cause**: Missing .wav or .opus files

**Solution**:
- Ensure all audio files are in the project root directory
- Files should be named: `chill.wav`, `danger.opus`, `dooropen.wav`, `dig.wav`, `win.wav`

### Smart Bulbs Not Responding

**Cause**: Bulb IP addresses incorrect or bulbs unreachable

**Solution**:
1. Verify bulb IP addresses in `.wizbulb.ini`
2. Ensure bulbs are powered on
3. Check that they're connected to the same network as your computer

### Process Doesn't Stop When Switching

**Cause**: Rare race condition

**Solution**: Close the launcher window and reopen it

## Advanced Usage

### Add More Environments

1. Create a new Python script in the `environments/` directory
2. Copy the structure from an existing environment script
3. Update the Spotify playlist URI and sound effect file
4. Save the file with a descriptive name (e.g., `my_scene.py`)
5. The launcher will auto-discover it on next restart

### Modify Button Order

Currently buttons are sorted alphabetically. To customize:
1. Edit `launcher.py`
2. Modify the `discover_environments()` method in the `EnvironmentDiscovery` class
3. Change the sorting logic or add custom ordering

### Environment Auto-Loading

The launcher scans the `environments/` directory on startup. It:
- Discovers all `.py` files (except `f.py`)
- Sorts them alphabetically
- Assigns the first 26 keyboard shortcuts
- Displays all in the grid (overflow buttons have no shortcut)

### Customizing Appearance

Button colors and styles can be changed:
- `ACTIVE_STYLE`: Color when environment is running (green)
- `INACTIVE_STYLE`: Color for normal buttons (light gray)
- `OVERFLOW_STYLE`: Color for buttons beyond 26 (darker gray)

Edit the class variables in `EnvironmentLauncher` class in `launcher.py`

## Technical Details

### Process Management

- Each environment runs as a separate subprocess
- Only one subprocess can run at a time
- When switching, the launcher sends SIGTERM for graceful shutdown
- If process doesn't stop in 2 seconds, SIGKILL is used

### Configuration File Access

Environment scripts run with the working directory set to the project root, so they can find:
- `.spotify.ini` (Spotify authentication)
- `.wizbulb.ini` (Smart bulb configuration)
- Sound effect files (*.wav, *.opus)

### Process Groups

On Linux/Mac, the launcher creates a new process group for each environment. This ensures that:
- Child processes (Spotify, bulb connections) are properly terminated
- No orphaned processes are left behind

## Tips

1. **Keep Window Focused**: For best keyboard shortcut experience, keep the launcher window in focus
2. **Test Environments**: After setup, test each environment briefly to verify everything works
3. **Monitor Status Bar**: Always check the status bar to confirm which environment is running
4. **Gradual Switching**: Give new environments 2-5 seconds to initialize (OAuth + bulb connections)
5. **Config Backups**: Keep backups of `.spotify.ini` and `.wizbulb.ini` in case you need to reset

## Future Enhancements

Potential improvements (not yet implemented):
- Environment categories (battles, travels, social, etc.)
- Custom keyboard shortcuts configuration
- Favorite environments/quick access
- Console output viewer for debugging
- Pre-loading of Spotify connections for faster switching
- Custom button arrangement
- Light transition effects when switching environments

## Support

If you encounter issues:
1. Check that all files are in the correct locations
2. Verify configuration files exist and are properly formatted
3. Check Python version (Python 3.6+ required)
4. Review the Troubleshooting section above
5. Check launcher output in the terminal for error messages
