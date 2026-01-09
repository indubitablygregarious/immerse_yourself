---
name: findfsaudio
description: Search freesound.org for audio files by keywords. Returns URLs, descriptions, and tags. Use for finding replacement sounds or new audio for environments.
allowed-tools: Read, Write, Edit, Glob, Grep, Bash(python3:*)
---

# Find Freesound Audio

Search freesound.org for sounds by keywords and get URLs suitable for use in environment configs.

## Usage

```
/findfsaudio outdoor crowd ambience
/findfsaudio rope rigging ship creaking
/findfsaudio medieval market vendors
```

## Process

1. **Run the search script** with the user's keywords:

```bash
python3 tools/freesound_search.py "KEYWORDS"
```

2. **Review the results** - the script outputs:
   - Numbered list of sounds with URLs, descriptions, duration, and tags
   - Ready-to-use YAML snippet for env_conf files

3. **Present results to user** and help them:
   - Select appropriate sounds for their use case
   - Update environment YAML files with new URLs
   - Replace broken/404 URLs with working alternatives

## Example Output

```
Searching freesound.org for: outdoor crowd ambience
Search URL: https://freesound.org/search/?q=outdoor+crowd+ambience

============================================================
[1] Outdoor Crowd Chatter
    URL: https://freesound.org/people/Leandros.Ntounis/sounds/163612/
    By: Leandros.Ntounis
    Duration: 2:30
    Description: Crowd talking outdoors at a festival...
    Tags: crowd, outdoor, chatter, people, ambience

============================================================
YAML format for env_conf:
      # Outdoor Crowd Chatter (2:30)
      - url: "https://freesound.org/people/Leandros.Ntounis/sounds/163612/"
        volume: 50
```

## Common Search Terms

| Sound Type | Keywords to Try |
|------------|-----------------|
| Crowd/ambient | outdoor crowd, market crowd, town ambience, people talking |
| Medieval market | medieval market, vendors, merchant, bazaar |
| Nautical | ship rigging, rope creaking, sailing, marina, harbor |
| Nature | forest ambience, birds chirping, wind trees |
| Combat | sword clash, battle, armor, war drums |

## Tips

- Use multiple keyword variations if first search doesn't find good results
- Check duration - ambient loops work best at 1-5 minutes
- Shorter sounds (1-5 seconds) work better for one-shot effects
- Look at tags to find related sounds
