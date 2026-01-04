# Environment Configuration Schema

This directory contains YAML configuration files for all Immerse Yourself environments. Each YAML file defines how an environment behaves: what sound effects to play, which Spotify playlist to use, and how to animate the lights.

## Quick Start

Create a new environment by copying an existing YAML file and modifying it, or create a new file from scratch following the schema below.

**Minimal Example:**
```yaml
name: "My Environment"
category: "special"
icon: "🎮"

metadata:
  tags: ["custom"]
  intensity: "medium"

engines:
  sound:
    enabled: true
    file: "chill.wav"

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

## Complete Schema Reference

### Top-Level Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Display name shown in launcher |
| `category` | string | Yes | Category for tab organization: `combat`, `social`, `exploration`, `relaxation`, `special` |
| `description` | string | No | Short description (shown below button) |
| `icon` | string | No | Emoji displayed as semi-transparent background on button (e.g., `"🍺"`) |
| `metadata` | object | No | Additional metadata for UI/filtering |
| `engines` | object | Yes | Configuration for sound, spotify, and lights engines |

### Metadata Fields

| Field | Type | Description |
|-------|------|-------------|
| `tags` | array of strings | Tags for filtering (e.g., `["indoor", "cozy", "medieval"]`) |
| `intensity` | string | Intensity level: `low`, `medium`, `high` |
| `suitable_for` | array of strings | Use cases (e.g., `["tabletop gaming", "background ambiance"]`) |

### Engines Configuration

The `engines` object contains three sub-objects for each engine type.

#### Sound Engine

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `enabled` | boolean | Yes | Whether to play sound effect |
| `file` | string | If enabled | Filename relative to project root (e.g., `"dooropen.wav"`) |

**Example:**
```yaml
engines:
  sound:
    enabled: true
    file: "danger.opus"
```

To disable sound:
```yaml
engines:
  sound:
    enabled: false
```

#### Spotify Engine

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `enabled` | boolean | Yes | Whether to play Spotify content |
| `context_uri` | string | If enabled | Spotify URI for playlist/album/episode |

**Supported URI formats:**
- Playlist: `spotify:playlist:XXXXXXXXXXXXXXXXXXXX`
- Album: `spotify:album:XXXXXXXXXXXXXXXXXXXX`
- Episode: `spotify:episode:XXXXXXXXXXXXXXXXXXXX`

**Example:**
```yaml
engines:
  spotify:
    enabled: true
    context_uri: "spotify:playlist:5Q8DWZnPe7o7GA96SARmOK"
```

To disable Spotify:
```yaml
engines:
  spotify:
    enabled: false
```

#### Lights Engine

The lights engine is the most complex, supporting multiple bulb groups with different animation patterns.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `enabled` | boolean | Yes | Whether to control lights |
| `animation` | object | If enabled | Animation configuration |

**Animation Configuration:**

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `cycletime` | number | No | 12 | Seconds for one animation cycle (lower = faster) |
| `flash_variance` | number | No | 25 | Variance in flash brightness (legacy, not currently used) |
| `groups` | object | Yes | - | Configuration for each bulb group |

**Bulb Groups:**

Three bulb groups are available:
- `backdrop`: Background ambiance bulbs
- `overhead`: Main lighting bulbs
- `battlefield`: Tactical/accent bulbs

Each group can have its own configuration:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `type` | string | Yes | Animation type: `rgb`, `scene`, `inherit_backdrop`, `inherit_overhead` |
| `rgb` | object | If type=rgb | RGB color configuration |
| `scene` | object | If type=scene | WIZ scene configuration |
| `brightness` | object | No | Brightness range |
| `flash` | object | No | Flash effect configuration |

**RGB Configuration:**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `base` | array [R, G, B] | [128, 128, 128] | Base RGB color (0-255 each) |
| `variance` | array [R, G, B] | [20, 20, 20] | Random variance added to each channel |

**Scene Configuration:**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `ids` | array of numbers | [5, 28, 31] | WIZ scene IDs to randomly choose from |
| `speed_min` | number | 10 | Minimum animation speed (1-200) |
| `speed_max` | number | 190 | Maximum animation speed (1-200) |

**Common WIZ Scene IDs:**
- `4`: Party
- `5`: Fireplace
- `7`: Campfire
- `12`: Sun
- `23`: Ocean
- `28`: Torch 1
- `30`: Desert
- `31`: Torch 2

**Brightness Configuration:**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `min` | number | 100 | Minimum brightness (0-255) |
| `max` | number | 255 | Maximum brightness (0-255) |

**Flash Configuration:**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `probability` | number | 0.05 | Chance of flash per bulb update (0.0-1.0) |
| `color` | array [R, G, B] | [255, 255, 255] | Flash color |
| `brightness` | number | 255 | Flash brightness |
| `duration` | number | 1.0 | Flash duration in seconds |

## Complete Examples

### Example 1: Tavern (Social Environment)

```yaml
name: "Tavern"
category: "social"
description: "Cozy medieval tavern atmosphere with warm lighting"

metadata:
  tags: ["social", "indoor", "cozy", "medieval"]
  intensity: "low"
  suitable_for: ["tabletop gaming", "social scenes", "downtime"]

engines:
  sound:
    enabled: true
    file: "dooropen.wav"

  spotify:
    enabled: true
    context_uri: "spotify:playlist:5Q8DWZnPe7o7GA96SARmOK"

  lights:
    enabled: true
    animation:
      cycletime: 12
      flash_variance: 25

      groups:
        backdrop:
          type: "rgb"
          rgb:
            base: [128, 128, 128]
            variance: [20, 20, 20]
          brightness:
            min: 74
            max: 255
          flash:
            probability: 0.05
            color: [255, 255, 255]
            brightness: 230
            duration: 1.0

        overhead:
          type: "scene"
          scenes:
            ids: [5, 28, 31]  # Torch scenes
            speed_min: 10
            speed_max: 190
          brightness:
            min: 195
            max: 255

        battlefield:
          type: "inherit_overhead"
```

### Example 2: Battle Dungeon (High-Intensity Combat)

```yaml
name: "Battle Dungeon"
category: "combat"
description: "High-intensity dungeon combat with danger sounds and red flashing"

metadata:
  tags: ["combat", "intense", "dungeon", "underground"]
  intensity: "high"
  suitable_for: ["boss fights", "combat encounters", "tense moments"]

engines:
  sound:
    enabled: true
    file: "danger.opus"

  spotify:
    enabled: true
    context_uri: "spotify:playlist:6FohP6m1ipvNjgllOH4HLt"

  lights:
    enabled: true
    animation:
      cycletime: 2  # Fast animation

      groups:
        backdrop:
          type: "scene"
          scenes:
            ids: [5, 28, 31]
            speed_min: 10
            speed_max: 190
          brightness:
            min: 68
            max: 128

        overhead:
          type: "rgb"
          rgb:
            base: [32, 32, 32]  # Dark base
            variance: [30, 30, 30]
          brightness:
            min: 64
            max: 84

        battlefield:
          type: "rgb"
          rgb:
            base: [32, 32, 32]
            variance: [30, 30, 30]
          brightness:
            min: 32
            max: 52
          flash:
            probability: 0.25  # High flash rate
            color: [255, 0, 0]  # Red danger flash
            brightness: 255
            duration: 1.0
```

### Example 3: Chill (Relaxation)

```yaml
name: "Chill"
category: "relaxation"
description: "Ultra-relaxed ambient atmosphere for meditation and downtime"

metadata:
  tags: ["relaxation", "ambient", "slow", "peaceful"]
  intensity: "low"
  suitable_for: ["meditation", "reading", "background music"]

engines:
  sound:
    enabled: true
    file: "chill.wav"

  spotify:
    enabled: true
    context_uri: "spotify:playlist:0vvXsWCC9xrXsKd4FyS8kM"

  lights:
    enabled: true
    animation:
      cycletime: 60  # Very slow

      groups:
        backdrop:
          type: "rgb"
          rgb:
            base: [128, 128, 64]
            variance: [20, 20, 20]
          brightness:
            min: 100
            max: 220
          flash:
            probability: 0.05
            color: [255, 255, 255]
            brightness: 220
            duration: 1.0

        overhead:
          type: "inherit_backdrop"

        battlefield:
          type: "inherit_backdrop"
```

### Example 4: Sound-Only Environment

```yaml
name: "Applause"
category: "special"
description: "Victory celebration with applause sound"

metadata:
  tags: ["celebration", "special", "one-shot"]
  intensity: "medium"
  suitable_for: ["victories", "achievements"]

engines:
  sound:
    enabled: true
    file: "applause-4.mp3"

  spotify:
    enabled: false

  lights:
    enabled: false
```

### Example 5: Lights-Only Environment

```yaml
name: "Firelight Ambiance"
category: "relaxation"
description: "Gentle firelight animation without sound"

metadata:
  tags: ["ambient", "visual-only", "firelight"]
  intensity: "low"
  suitable_for: ["silent sessions", "visual ambiance"]

engines:
  sound:
    enabled: false

  spotify:
    enabled: false

  lights:
    enabled: true
    animation:
      cycletime: 20

      groups:
        backdrop:
          type: "scene"
          scenes:
            ids: [7]  # Campfire scene
            speed_min: 50
            speed_max: 100
          brightness:
            min: 150
            max: 200

        overhead:
          type: "inherit_backdrop"

        battlefield:
          type: "inherit_backdrop"
```

## Group Inheritance

Use `type: "inherit_backdrop"` or `type: "inherit_overhead"` to copy configuration from another group:

```yaml
groups:
  backdrop:
    type: "rgb"
    rgb:
      base: [255, 100, 0]
      variance: [20, 20, 20]
    brightness:
      min: 100
      max: 200

  overhead:
    type: "inherit_backdrop"  # Uses same config as backdrop

  battlefield:
    type: "inherit_backdrop"  # Also uses backdrop config
```

## Tuning Guide

### Animation Speed
- **Very Slow (60s+)**: Chill, meditation, background ambiance
- **Slow (20-40s)**: Social scenes, taverns, towns
- **Medium (6-12s)**: Travel, exploration
- **Fast (2-4s)**: Combat, high-intensity scenes
- **Very Fast (<2s)**: Panic, chaos, extreme action

### Flash Probability
- **0.01-0.05**: Rare, subtle flickers
- **0.05-0.15**: Occasional flashes for interest
- **0.15-0.30**: Frequent flashes for intensity
- **0.30+**: Constant flashing (use for extreme effects only)

### RGB Color Palettes
- **Warm** (taverns, fire): High red, medium green, low blue (e.g., [200, 100, 50])
- **Cool** (night, water): Low red, medium green, high blue (e.g., [50, 100, 200])
- **Neutral** (default): Balanced (e.g., [128, 128, 128])
- **Vibrant**: High all channels with high variance (e.g., [200, 200, 200] ± [50, 50, 50])
- **Dark**: Low all channels (e.g., [32, 32, 32])

### Brightness Ranges
- **Dim** (0-100): Subtle, background lighting
- **Medium** (100-180): Normal room lighting
- **Bright** (180-255): Main lighting, high visibility
- **Flash**: Always use 200-255 for noticeable flashes

## Validation

After creating a YAML file, validate it by running:

```bash
python3 -c "from config_loader import ConfigLoader; ConfigLoader('env_conf').load('your_file.yaml')"
```

Or use the Makefile:

```bash
make validate-configs
```

## Tips

1. **Start from an example**: Copy a similar environment and modify it
2. **Test incrementally**: Change one parameter at a time to see the effect
3. **Use inheritance**: Avoid duplication with `inherit_backdrop`/`inherit_overhead`
4. **Comment your configs**: YAML supports comments with `#`
5. **Keep backups**: Git tracks your changes, so experiment freely

## Troubleshooting

**Lights not animating:**
- Check that `enabled: true` under `engines.lights`
- Verify bulb IP addresses in `.wizbulb.ini`
- Check cycletime isn't too high (>60s makes animations very slow)

**Sound not playing:**
- Verify sound file exists in project root
- Check file extension matches (`.wav`, `.opus`, `.mp3`)
- Try `enabled: false` if sound isn't critical

**Spotify not playing:**
- Check `.spotify.ini` credentials are correct
- Verify `.cache` file exists (run any environment once to create it)
- Check Spotify URI format is correct
- Ensure an active Spotify device is available

## Contributing

When creating new environments:
1. Use descriptive names
2. Fill in all metadata fields
3. Tag appropriately for organization
4. Test with actual hardware before committing
5. Document any unusual configurations in comments
