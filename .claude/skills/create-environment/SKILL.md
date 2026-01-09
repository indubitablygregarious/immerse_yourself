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

## Entry Sound (sound_conf)

Use predefined sound_conf collections for entry sounds. These randomly select from multiple variations.

### Available sound_confs:
| Reference | Description | Use For |
|-----------|-------------|---------|
| `sound_conf:transition` | Whooshes, magic chimes, swooshes (14 sounds) | General scene changes, travel |
| `sound_conf:squeaky_door` | Door creaks and squeaks (7 sounds) | Entering buildings, taverns, shops |
| `sound_conf:battle_intro` | Sword draws, war drums, danger stings (8 sounds) | Combat encounters |
| `sound_conf:camp_setup` | Digging, shoveling, setup sounds (7 sounds) | Camping, making camp |
| `sound_conf:victory` | Fanfares, triumph sounds (7 sounds) | Winning, celebrations |
| `sound_conf:applause` | Crowd clapping, cheering (7 sounds) | Performances, celebrations |

### Selecting Entry Sound:
- **Indoor/buildings**: `sound_conf:squeaky_door`
- **Travel/outdoor**: `sound_conf:transition`
- **Combat**: `sound_conf:battle_intro`
- **Camping/rest**: `sound_conf:camp_setup`
- **Victory/celebration**: `sound_conf:victory` or `sound_conf:applause`

## YAML Template

```yaml
name: "Environment Name"
category: "category_name"
description: "Brief atmospheric description"
icon: "emoji"

metadata:
  tags: ["tag1", "tag2", "atmosphere"]
  intensity: "low|medium|high"
  suitable_for: ["boss fights", "exploration", "social encounters"]  # Searchable scenarios

engines:
  sound:
    enabled: true
    file: "sound_conf:transition"  # Use appropriate sound_conf for entry

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

## Time-of-Day Variants

Most environments should have morning/afternoon/night variants for immersive campaigns.

### Naming Convention
```
{base_name}_morning.yaml
{base_name}_afternoon.yaml
{base_name}_night.yaml
```

### Time-Specific Adjustments

| Time | RGB Colors | Brightness | Cycletime | Sounds |
|------|------------|------------|-----------|--------|
| Morning | Warm gold `[200, 170, 130]`, pink `[200, 160, 150]` | min: 120-150, max: 200-230 | 12-16s (slower) | Dawn chorus, roosters, morning birds |
| Afternoon | Bright saturated, sky blue `[70, 90, 180]` | min: 170-200, max: 235-255 | 8-12s (medium) | Cicadas, insects, busy activity |
| Night | Dark blue `[30, 40, 70]`, purple `[50, 40, 80]` | min: 20-60, max: 80-120 | 14-20s (slow) | Crickets, owls, wolves, frogs |

### Typical freesound.org sounds by time:

**Morning sounds:**
- Dawn chorus: search "dawn chorus birds"
- Rooster: search "rooster morning"
- Morning birds: `https://freesound.org/people/klankbeeld/sounds/625333/`

**Afternoon sounds:**
- Cicadas/insects: `https://freesound.org/people/harryScary/sounds/268958/`
- Afternoon birds: `https://freesound.org/people/klankbeeld/sounds/625003/`

**Night sounds:**
- Crickets: `https://freesound.org/people/kyles/sounds/450995/`
- Owl: `https://freesound.org/people/Anthousai/sounds/398734/`
- Wolf howl: `https://freesound.org/people/Taure/sounds/380156/`
- Night frogs: `https://freesound.org/people/felix.blume/sounds/135561/`

### Night-specific lighting effects

Add occasional moonbeam flashes for night environments:
```yaml
flash:
  probability: 0.03
  color: [180, 200, 220]  # Pale moonlight
  brightness: 120
  duration: 2.0
```

### Example: Creating forest variants

If user asks for "forest environment", create all three:

1. `forest_morning.yaml` - Golden dawn light, bird chorus, misty feel
2. `forest_afternoon.yaml` - Bright dappled sunlight, insects buzzing
3. `forest_night.yaml` - Dark with moonbeams, crickets, owls

## Reference Files

Read existing environments for patterns:

### Basic Examples
- `env_conf/tavern.yaml` - Indoor social example
- `env_conf/forest.yaml` - Nature example (base)
- `env_conf/dungeon.yaml` - Dark/enclosed example
- `env_conf/travel_storm.yaml` - Weather example

### Time Variants
- `env_conf/forest_morning.yaml` - Morning variant example
- `env_conf/forest_afternoon.yaml` - Afternoon variant example
- `env_conf/forest_night.yaml` - Night variant example
- `env_conf/graveyard_night.yaml` - Spooky night example

### Fantasy Gaming Locations
- `env_conf/mine.yaml` - Underground tunnels with pickaxe sounds
- `env_conf/wizard_tower.yaml` - Arcane lab with magical effects
- `env_conf/castle_courtyard.yaml` - Noble outdoor space
- `env_conf/arena.yaml` - Gladiatorial combat with crowds
- `env_conf/docks.yaml` - Harbor with ships and seagulls
- `env_conf/crypt.yaml` - Burial chambers with undead atmosphere
- `env_conf/fey_wild.yaml` - Enchanted forest with fairy bells
- `env_conf/thieves_guild.yaml` - Criminal hideout with shadows
- `env_conf/war_camp.yaml` - Military encampment with drums
- `env_conf/dragons_lair.yaml` - Boss cave with treasure
- `env_conf/haunted_manor.yaml` - Ghost-filled mansion
- `env_conf/monastery.yaml` - Peaceful retreat with chanting

### Combat Examples
- `env_conf/battle_dungeon.yaml` - Combat with Spotify music
- `env_conf/battle_forest.yaml` - Forest combat theme
- `env_conf/arena.yaml` - Tournament/gladiator combat
