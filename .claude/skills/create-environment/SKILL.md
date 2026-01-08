---
name: create-environment
description: Generate complete environment YAML configs with atmosphere sounds and lighting from a text description. Use when creating new scenes, ambiences, or immersive environments.
allowed-tools: Read, Write, Glob, Grep, Bash(python3:*), WebFetch
---

# Create Environment Generator

Generate complete environment YAML configurations from natural language descriptions.

## Usage

When invoked, ask the user for:
1. **Description** - What is the scene/environment? (e.g., "A spooky graveyard at midnight")
2. **Name** - Short name for the environment (e.g., "Graveyard")

Then generate a complete YAML with atmosphere sounds and lighting.

## Environment Categories

Choose the appropriate category based on the description:

**Environment categories** (have lights + atmosphere):
- `tavern` - Indoor social spaces (taverns, inns)
- `town` - Populated areas (towns, markets, shops, libraries, festivals)
- `travel` - Journey/movement scenes (paths, roads)
- `forest` - Wooded natural areas
- `coastal` - Beach, ocean, boats
- `desert` - Arid/hot landscapes
- `mountain` - High altitude, caves
- `dungeon` - Dark enclosed spaces
- `combat` - Active battle scenes
- `spooky` - Eerie/horror atmospheres
- `weather` - Storm, rain focused
- `relaxation` - Calm, peaceful
- `celestial` - Supernatural (heaven, hell, magical)

## Lighting Guidelines

### Cycletime (animation speed)
- **Fast (2-4s)**: Combat, danger, tension
- **Medium (6-8s)**: Exploration, travel
- **Slow (10-14s)**: Relaxation, peaceful, tavern

### Color Palettes
- **Warm** (tavern, fire): `[255, 150, 50]`, `[200, 100, 50]`
- **Cool** (night, spooky): `[50, 50, 150]`, `[100, 50, 200]`
- **Nature** (forest): `[50, 150, 50]`, `[100, 200, 100]`
- **Desert** (hot): `[255, 200, 100]`, `[200, 150, 50]`
- **Ocean** (coastal): `[50, 150, 200]`, `[100, 200, 255]`
- **Fire/Hell**: `[255, 50, 0]`, `[255, 100, 0]`
- **Divine**: `[255, 255, 200]`, `[200, 200, 255]`

### Brightness Ranges
- **Dim** (dungeon, spooky): min 30-80, max 100-150
- **Normal** (travel, town): min 80-120, max 180-220
- **Bright** (celestial, beach): min 150-200, max 230-255

## Atmosphere Sounds

Search freesound.org for appropriate ambient sounds. Use 3-6 sounds in the mix.

### Sound Selection Strategy
1. **Base layer** (required): Primary ambient sound (e.g., forest ambience, crowd murmur)
2. **Secondary layer** (required): Supporting sound (e.g., wind, water)
3. **Detail layers** (optional): Specific sounds with probability (e.g., bird calls, footsteps)

### Example freesound URLs by theme:
- Fire/crackling: search "fireplace crackling loop"
- Crowd/tavern: search "tavern ambience crowd"
- Forest: search "forest ambience birds"
- Ocean: search "ocean waves loop"
- Rain: search "rain ambient loop"
- Wind: search "wind howling ambient"
- Dungeon: search "dungeon dripping echo"

## YAML Template

```yaml
name: "Environment Name"
category: "category_name"
description: "Brief atmospheric description"
icon: "emoji"

metadata:
  tags: ["tag1", "tag2", "atmosphere"]
  intensity: "low|medium|high"

engines:
  sound:
    enabled: true
    file: "sounds/transition.wav"  # Entry sound effect

  spotify:
    enabled: false

  atmosphere:
    enabled: true
    min_sounds: 2
    max_sounds: 4
    mix:
      - url: "https://freesound.org/people/CREATOR/sounds/ID/"
        volume: 80
      - url: "https://freesound.org/people/CREATOR/sounds/ID/"
        volume: 60
        optional: true
        probability: 0.7

  lights:
    enabled: true
    animation:
      cycletime: 10
      groups:
        backdrop:
          type: "rgb"
          rgb:
            base: [R, G, B]
            variance: [20, 20, 20]
          brightness:
            min: 100
            max: 200
        overhead:
          type: "rgb"
          rgb:
            base: [R, G, B]
            variance: [30, 30, 30]
          brightness:
            min: 120
            max: 230
        battlefield:
          type: "rgb"
          rgb:
            base: [R, G, B]
            variance: [20, 20, 20]
          brightness:
            min: 80
            max: 150
```

## Process

1. **Parse description** to determine category, mood, and key elements
2. **Search freesound.org** for 3-6 appropriate ambient sounds using WebFetch
3. **Design lighting** based on mood (colors, speed, brightness)
4. **Generate YAML** with all components
5. **Save to env_conf/** with snake_case filename
6. **Validate** with: `python3 -c "from config_loader import ConfigLoader; ConfigLoader('env_conf').load('filename.yaml')"`

## Example

**Input**: "A cozy mountain cabin during a snowstorm with a crackling fire"

**Output**: `mountain_cabin.yaml` in the `tavern` category with:
- Fireplace crackling sound (required)
- Wind/blizzard outside (required)
- Snow against windows (optional, 50%)
- Warm orange/red lighting, slow cycle (12s)
- Medium brightness

## Reference Files

Read existing environments for patterns:
- `env_conf/tavern.yaml` - Indoor social example
- `env_conf/forest.yaml` - Nature example
- `env_conf/dungeon.yaml` - Dark/enclosed example
- `env_conf/travel_storm.yaml` - Weather example
