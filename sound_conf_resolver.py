"""
Sound Configuration Resolver - Handles sound variation configs

Resolves sound_conf references like "sound_conf:squeaky_door" to a randomly
selected sound from the sound_conf/squeaky_door.yaml file.

Usage:
    from sound_conf_resolver import resolve_sound_conf, is_sound_conf_reference

    if is_sound_conf_reference("sound_conf:squeaky_door"):
        sound = resolve_sound_conf("sound_conf:squeaky_door")
        # sound is either a local file path or freesound URL
"""

import random
import yaml
from pathlib import Path
from typing import Optional, List, Dict, Any, Union


SOUND_CONF_PREFIX = "sound_conf:"
SOUND_CONF_DIR = "sound_conf"


def is_sound_conf_reference(sound_file: str) -> bool:
    """
    Check if a sound file reference points to a sound_conf YAML.

    Args:
        sound_file: Sound file string from config

    Returns:
        True if this is a sound_conf reference (e.g., "sound_conf:squeaky_door")
    """
    if not sound_file:
        return False
    return sound_file.startswith(SOUND_CONF_PREFIX)


def resolve_sound_conf(sound_ref: str, project_root: Optional[Path] = None) -> Optional[str]:
    """
    Resolve a sound_conf reference to a randomly selected sound.

    Args:
        sound_ref: Sound conf reference like "sound_conf:squeaky_door"
        project_root: Optional project root path (defaults to cwd)

    Returns:
        Either a local file path (e.g., "sounds/dooropen.wav") or
        freesound URL, or None if resolution fails
    """
    if not is_sound_conf_reference(sound_ref):
        return sound_ref

    # Extract the conf name
    conf_name = sound_ref[len(SOUND_CONF_PREFIX):].strip()
    if not conf_name:
        print(f"WARNING: Empty sound_conf reference: {sound_ref}")
        return None

    # Find and load the YAML
    root = project_root or Path.cwd()
    yaml_path = root / SOUND_CONF_DIR / f"{conf_name}.yaml"

    if not yaml_path.exists():
        print(f"WARNING: Sound conf file not found: {yaml_path}")
        return None

    try:
        with open(yaml_path, 'r') as f:
            config = yaml.safe_load(f)
    except Exception as e:
        print(f"WARNING: Failed to load sound conf {yaml_path}: {e}")
        return None

    # Get the sounds list
    sounds = config.get("sounds", [])
    if not sounds:
        print(f"WARNING: No sounds defined in {yaml_path}")
        return None

    # Randomly select one sound
    selected = random.choice(sounds)

    # Return either the file or URL
    if "file" in selected:
        return selected["file"]
    elif "url" in selected:
        return selected["url"]
    else:
        print(f"WARNING: Sound entry has neither 'file' nor 'url': {selected}")
        return None


def get_sound_conf_info(sound_ref: str, project_root: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    """
    Get information about a sound_conf without selecting a sound.

    Args:
        sound_ref: Sound conf reference like "sound_conf:squeaky_door"
        project_root: Optional project root path (defaults to cwd)

    Returns:
        Dict with 'name', 'description', 'count' keys, or None if not found
    """
    if not is_sound_conf_reference(sound_ref):
        return None

    conf_name = sound_ref[len(SOUND_CONF_PREFIX):].strip()
    if not conf_name:
        return None

    root = project_root or Path.cwd()
    yaml_path = root / SOUND_CONF_DIR / f"{conf_name}.yaml"

    if not yaml_path.exists():
        return None

    try:
        with open(yaml_path, 'r') as f:
            config = yaml.safe_load(f)

        return {
            "name": config.get("name", conf_name),
            "description": config.get("description", ""),
            "count": len(config.get("sounds", []))
        }
    except Exception:
        return None


def list_sound_confs(project_root: Optional[Path] = None) -> List[Dict[str, Any]]:
    """
    List all available sound_conf files.

    Args:
        project_root: Optional project root path (defaults to cwd)

    Returns:
        List of dicts with 'ref', 'name', 'description', 'count' keys
    """
    root = project_root or Path.cwd()
    conf_dir = root / SOUND_CONF_DIR

    if not conf_dir.exists():
        return []

    result = []
    for yaml_file in conf_dir.glob("*.yaml"):
        try:
            with open(yaml_file, 'r') as f:
                config = yaml.safe_load(f)

            conf_name = yaml_file.stem
            result.append({
                "ref": f"{SOUND_CONF_PREFIX}{conf_name}",
                "name": config.get("name", conf_name),
                "description": config.get("description", ""),
                "count": len(config.get("sounds", []))
            })
        except Exception:
            continue

    return result
