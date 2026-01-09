---
name: sound-conf
description: Create sound variation configs (sound_conf) with multiple sound alternatives, and find freesound.org replacements for local audio files. Use when building sound collections, finding freesound alternatives, or creating audio variation configs.
allowed-tools: Read, Write, Glob, Grep, Bash(python3:*), WebFetch
---

# Sound Configuration Builder

Build sound variation configs and find freesound.org alternatives for local audio files.

## Overview

Sound configs (`sound_conf/`) define collections of similar sounds where one is randomly selected at runtime. This provides variety - e.g., different door squeaks, footstep variations, or sword clash sounds.

## Use Cases

1. **Build a new sound_conf** - Create a collection of sound variations
2. **Find freesound replacements** - Search freesound.org for alternatives to local wav/mp3 files
3. **Expand existing sound_conf** - Add more variations to an existing collection

## Sound Conf Format

```yaml
# sound_conf/example.yaml
name: "Human-readable Name"
description: "What these sounds represent"

sounds:
  # Local file reference
  - file: "sounds/original.wav"
    description: "Original sound from sounds/ directory"

  # Freesound.org URL reference
  - url: "https://freesound.org/people/CREATOR/sounds/ID/"
    description: "Brief description of this variation"

  # More variations...
  - url: "https://freesound.org/people/CREATOR/sounds/ID/"
    description: "Another variation"
```

## How Sound Confs Are Used

Environment configs reference sound_confs with the `sound_conf:` prefix:

```yaml
# In env_conf/tavern.yaml
engines:
  sound:
    enabled: true
    file: "sound_conf:squeaky_door"  # References sound_conf/squeaky_door.yaml
```

At runtime, one sound is randomly selected from the collection.

## Process: Building a Sound Conf

### Step 1: Identify the Sound Type
Ask the user:
- What type of sound? (door, footsteps, sword, scream, etc.)
- Any existing local file to include?
- How many variations desired? (recommend 5-10)

### Step 2: Search Freesound.org
Use WebFetch to search freesound.org for variations:

```
https://freesound.org/search/?q=SEARCH_TERMS
```

Good search strategies:
- **Doors**: "door creak", "door squeak", "wooden door", "old door hinge"
- **Footsteps**: "footsteps wood", "boots walking", "gravel footsteps"
- **Swords**: "sword clash", "metal sword", "sword swing", "blade hit"
- **Reactions**: "human gasp", "surprised scream", "pain groan"
- **Nature**: "bird chirp", "owl hoot", "wolf howl"

### Step 3: Evaluate Results
For each sound, check:
- Duration (prefer 1-5 seconds for one-shots)
- Quality (sample rate, clarity)
- License (all freesound sounds are CC licensed)
- Downloads/ratings as quality indicator

### Step 4: Build the YAML
Create `sound_conf/name.yaml` with:
- Descriptive name
- Brief description
- 5-10 sound entries mixing local files and freesound URLs

### Step 5: Validate
```bash
python3 -c "
from sound_conf_resolver import resolve_sound_conf, get_sound_conf_info
info = get_sound_conf_info('sound_conf:NAME')
print(f'Loaded: {info}')
for i in range(3):
    print(f'Random selection {i+1}: {resolve_sound_conf(\"sound_conf:NAME\")}')
"
```

## Process: Finding Freesound Replacements

### Step 1: Identify Local Files
Find wav/mp3 files in the project:
```bash
find sounds/ -name "*.wav" -o -name "*.mp3"
```

Or check what's used in configs:
```bash
grep -r "file:.*sounds/" env_conf/
```

### Step 2: Analyze the Sound
Read the filename and any context to understand what the sound is:
- `dooropen.wav` → door opening/creaking sound
- `danger.wav` → alert/warning sound
- `chill.wav` → relaxation transition sound

### Step 3: Search Freesound
Use WebFetch to find alternatives:
```
https://freesound.org/search/?q=door+creak+wood
```

### Step 4: Create or Extend Sound Conf
Either:
- Create new sound_conf with original + alternatives
- Add alternatives to existing sound_conf

## Freesound URL Format

Valid freesound URLs look like:
```
https://freesound.org/people/USERNAME/sounds/ID/
```

Example:
```
https://freesound.org/people/kyles/sounds/451813/
```

## Example Sound Confs

### Door Sounds (squeaky_door.yaml)
```yaml
name: "Squeaky Door"
description: "Various door creaking and squeaking sounds"

sounds:
  - file: "sounds/dooropen.wav"
    description: "Original door open sound"
  - url: "https://freesound.org/people/callyrobyn/sounds/417968/"
    description: "Door creak by callyrobyn"
  - url: "https://freesound.org/people/kyles/sounds/451813/"
    description: "Door squeak by kyles"
```

### Sword Clashes (sword_clash.yaml)
```yaml
name: "Sword Clash"
description: "Metal sword impact and clash sounds"

sounds:
  - url: "https://freesound.org/people/CGEffex/sounds/93136/"
    description: "Sword clash impact"
  - url: "https://freesound.org/people/Yoyodaman234/sounds/183015/"
    description: "Metal sword hit"
  - url: "https://freesound.org/people/EminYILDIRIM/sounds/541462/"
    description: "Sword blade clash"
```

### Footsteps on Wood (footsteps_wood.yaml)
```yaml
name: "Wood Footsteps"
description: "Footsteps on wooden floors and boards"

sounds:
  - url: "https://freesound.org/people/Kostas17/sounds/536365/"
    description: "Wood floor creak"
  - url: "https://freesound.org/people/deleted_user_7146007/sounds/383067/"
    description: "Wooden footsteps"
```

## Search Tips

### Freesound Search Modifiers
- Use quotes for exact phrases: `"door creak"`
- Combine terms: `door creak wood old`
- Filter by duration in search results page

### Quality Indicators
- Higher download counts = more popular/useful
- Check ratings if available
- Preview sounds on freesound.org before adding

### Sound Categories to Consider
| Category | Search Terms |
|----------|--------------|
| Doors | door creak, hinge squeak, wooden door, gate |
| Footsteps | footsteps, walking, boots, running, gravel |
| Combat | sword, metal clash, punch, hit, impact |
| Nature | birds, wind, rain, thunder, water |
| Reactions | gasp, scream, groan, sigh, laugh |
| Ambient | room tone, crowd murmur, tavern, market |

## Time-of-Day Atmosphere Sounds

Common freesound.org URLs used for time-variant environments:

### Morning Sounds
| Sound | URL | Use For |
|-------|-----|---------|
| Dawn chorus | `https://freesound.org/people/klankbeeld/sounds/625333/` | Morning bird sounds |
| Rooster/morning | `https://freesound.org/people/Nightwatcher98/sounds/818470/` | Rural morning |
| Forest spring morning | `https://freesound.org/people/klankbeeld/sounds/273162/` | Forest mornings |

### Afternoon Sounds
| Sound | URL | Use For |
|-------|-----|---------|
| Cicadas/insects | `https://freesound.org/people/kvv_audio_joosthogervorst/sounds/717893/` | Hot afternoon |
| Afternoon birds | `https://freesound.org/people/klankbeeld/sounds/414907/` | Daytime outdoor |
| Summer meadow | `https://freesound.org/people/brunoacaleto/sounds/810412/` | Peaceful afternoon |

### Night Sounds
| Sound | URL | Use For |
|-------|-----|---------|
| Night crickets | `https://freesound.org/people/MessyAcousticApocalypse666/sounds/594779/` | General night |
| Owl hooting | `https://freesound.org/people/Anthousai/sounds/398734/` | Spooky/forest night |
| Wolf howl | `https://freesound.org/people/Taure/sounds/380156/` | Wilderness night |
| Night frogs | `https://freesound.org/people/felix.blume/sounds/673259/` | Swamp/pond night |
| Night fields | `https://freesound.org/people/klankbeeld/sounds/583866/` | Open night areas |

### Universal Sounds (work at any time)
| Sound | URL | Use For |
|-------|-----|---------|
| Fireplace | `https://freesound.org/people/hansende/sounds/263994/` | Indoor warmth |
| Fire crackling | `https://freesound.org/people/NickTayloe/sounds/813328/` | Campfire/forge |
| Wind through trees | `https://freesound.org/people/klankbeeld/sounds/702233/` | Forest/outdoor |
| Eerie wind | `https://freesound.org/people/Kinoton/sounds/558840/` | Ruins/spooky |
| Tavern crowd | `https://freesound.org/people/Robinhood76/sounds/700022/` | Social indoor |
| Torch crackling | `https://freesound.org/people/LordStirling/sounds/483692/` | Night torch ambience |

### Fantasy Location Sounds
| Sound | URL | Use For |
|-------|-----|---------|
| Pickaxe mining | `https://freesound.org/people/qubodup/sounds/187592/` | Mine, quarry |
| Magical humming | `https://freesound.org/people/quetzalcontla/sounds/612813/` | Wizard tower, arcane |
| Bubbling potion | `https://freesound.org/people/Breviceps/sounds/456826/` | Alchemy, wizard |
| Armor clanking | `https://freesound.org/people/CaCtUs2003/sounds/117885/` | Guards, military |
| Fountain water | `https://freesound.org/people/sss_samples/sounds/612682/` | Courtyard, plaza |
| Seagulls | `https://freesound.org/people/bruno.auzet/sounds/690332/` | Docks, coastal |
| Ship creaking | `https://freesound.org/people/WolfOWI/sounds/588310/` | Ships, docks |
| Bone rattling | `https://freesound.org/people/spookymodem/sounds/202091/` | Crypt, undead |
| Ghostly whispers | `https://freesound.org/people/Matio888/sounds/796514/` | Haunted, spooky |
| Fairy bells/chimes | `https://freesound.org/people/bone666138/sounds/198877/` | Fey wild, magical |
| Coins clinking | `https://freesound.org/people/Ridiculously_Decent_Audio/sounds/743389/` | Thieves, treasure |
| War drums | `https://freesound.org/people/Zott820/sounds/209984/` | War camp, battle |
| Crowd cheering | `https://freesound.org/people/Breviceps/sounds/445958/` | Arena, tournament |
| Monk chanting | `https://freesound.org/people/Sonic_Salad/sounds/398687/` | Monastery, temple |
| Clock ticking | `https://freesound.org/people/InspectorJ/sounds/343130/` | Manor, library |

## Reference Files

- `sound_conf/squeaky_door.yaml` - Example door sound collection
- `sound_conf_resolver.py` - Resolution logic for sound_conf references
- `env_conf/tavern.yaml` - Example usage of sound_conf in environment
