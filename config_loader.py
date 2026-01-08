"""
Configuration Loader - Loads and validates YAML environment configurations
"""

from pathlib import Path
from typing import Dict, List, Any, Optional
import yaml


class ConfigValidationError(Exception):
    """Raised when a configuration file fails validation."""
    pass


class ConfigLoader:
    """
    Loads and validates YAML environment configurations.

    This class handles discovery, loading, and basic validation of
    environment configuration files. It also provides caching for
    improved performance.

    Attributes:
        config_dir: Path to directory containing YAML config files
        _cache: Dictionary caching loaded configurations
    """

    def __init__(self, config_dir: str = "env_conf"):
        """
        Initialize the Config Loader.

        Args:
            config_dir: Path to directory containing YAML files
        """
        self.config_dir = Path(config_dir)
        self._cache: Dict[str, Dict[str, Any]] = {}

        if not self.config_dir.exists():
            raise FileNotFoundError(
                f"Configuration directory not found: {config_dir}"
            )

    def load(self, filename: str, use_cache: bool = True) -> Dict[str, Any]:
        """
        Load and validate a single YAML configuration file.

        Args:
            filename: Name of YAML file (e.g., "tavern.yaml")
            use_cache: Whether to use cached version if available

        Returns:
            Validated configuration dictionary

        Raises:
            FileNotFoundError: If config file doesn't exist
            ConfigValidationError: If config fails validation
            yaml.YAMLError: If YAML parsing fails
        """
        # Check cache first
        if use_cache and filename in self._cache:
            return self._cache[filename]

        # Build full path
        config_path = self.config_dir / filename

        if not config_path.exists():
            raise FileNotFoundError(
                f"Configuration file not found: {config_path}"
            )

        # Load YAML
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise yaml.YAMLError(
                f"Failed to parse YAML in {filename}:\n{str(e)}"
            )

        # Validate structure
        try:
            self._validate_config(config, filename)
        except ConfigValidationError as e:
            raise ConfigValidationError(
                f"Invalid configuration in {filename}:\n{str(e)}"
            )

        # Cache and return
        self._cache[filename] = config
        return config

    def _validate_config(self, config: Dict[str, Any], filename: str) -> None:
        """
        Validate configuration structure.

        Performs basic structural validation to catch common errors.
        Does not validate all possible edge cases.

        Args:
            config: Configuration dictionary to validate
            filename: Filename (for error messages)

        Raises:
            ConfigValidationError: If validation fails
        """
        # Check required top-level fields
        required_fields = ["name", "category", "engines"]
        for field in required_fields:
            if field not in config:
                raise ConfigValidationError(
                    f"Missing required field: {field}"
                )

        # Validate name
        if not isinstance(config["name"], str) or not config["name"].strip():
            raise ConfigValidationError(
                "Field 'name' must be a non-empty string"
            )

        # Validate category
        valid_categories = ["combat", "social", "exploration", "relaxation", "special", "hidden", "freesound"]
        if config["category"] not in valid_categories:
            raise ConfigValidationError(
                f"Field 'category' must be one of: {', '.join(valid_categories)}\n"
                f"Got: {config['category']}"
            )

        # Validate engines
        if not isinstance(config["engines"], dict):
            raise ConfigValidationError(
                "Field 'engines' must be a dictionary"
            )

        engines = config["engines"]

        # Validate sound engine
        if "sound" in engines:
            self._validate_sound_engine(engines["sound"])

        # Validate spotify engine
        if "spotify" in engines:
            self._validate_spotify_engine(engines["spotify"])

        # Validate lights engine
        if "lights" in engines:
            self._validate_lights_engine(engines["lights"])

        # Validate atmosphere engine
        if "atmosphere" in engines:
            self._validate_atmosphere_engine(engines["atmosphere"])

        # Check mutual exclusivity: can't have both spotify and atmosphere enabled
        spotify_enabled = engines.get("spotify", {}).get("enabled", False)
        atmosphere_enabled = engines.get("atmosphere", {}).get("enabled", False)
        if spotify_enabled and atmosphere_enabled:
            raise ConfigValidationError(
                "Cannot enable both spotify and atmosphere engines. Choose one."
            )

    def _validate_sound_engine(self, sound_config: Dict[str, Any]) -> None:
        """Validate sound engine configuration."""
        if not isinstance(sound_config, dict):
            raise ConfigValidationError(
                "engines.sound must be a dictionary"
            )

        if "enabled" not in sound_config:
            raise ConfigValidationError(
                "engines.sound.enabled is required"
            )

        if not isinstance(sound_config["enabled"], bool):
            raise ConfigValidationError(
                "engines.sound.enabled must be a boolean"
            )

        if sound_config["enabled"]:
            if "file" not in sound_config:
                raise ConfigValidationError(
                    "engines.sound.file is required when enabled=true"
                )
            if not isinstance(sound_config["file"], str):
                raise ConfigValidationError(
                    "engines.sound.file must be a string"
                )

    def _validate_spotify_engine(self, spotify_config: Dict[str, Any]) -> None:
        """Validate Spotify engine configuration."""
        if not isinstance(spotify_config, dict):
            raise ConfigValidationError(
                "engines.spotify must be a dictionary"
            )

        if "enabled" not in spotify_config:
            raise ConfigValidationError(
                "engines.spotify.enabled is required"
            )

        if not isinstance(spotify_config["enabled"], bool):
            raise ConfigValidationError(
                "engines.spotify.enabled must be a boolean"
            )

        if spotify_config["enabled"]:
            if "context_uri" not in spotify_config:
                raise ConfigValidationError(
                    "engines.spotify.context_uri is required when enabled=true"
                )
            if not isinstance(spotify_config["context_uri"], str):
                raise ConfigValidationError(
                    "engines.spotify.context_uri must be a string"
                )
            # Basic URI format check
            uri = spotify_config["context_uri"]
            if not uri.startswith("spotify:"):
                raise ConfigValidationError(
                    f"engines.spotify.context_uri must start with 'spotify:'\n"
                    f"Got: {uri}"
                )

    def _validate_atmosphere_engine(self, atmosphere_config: Dict[str, Any]) -> None:
        """Validate atmosphere engine configuration."""
        if not isinstance(atmosphere_config, dict):
            raise ConfigValidationError(
                "engines.atmosphere must be a dictionary"
            )

        if "enabled" not in atmosphere_config:
            raise ConfigValidationError(
                "engines.atmosphere.enabled is required"
            )

        if not isinstance(atmosphere_config["enabled"], bool):
            raise ConfigValidationError(
                "engines.atmosphere.enabled must be a boolean"
            )

        if atmosphere_config["enabled"]:
            if "mix" not in atmosphere_config:
                raise ConfigValidationError(
                    "engines.atmosphere.mix is required when enabled=true"
                )

            mix = atmosphere_config["mix"]
            if not isinstance(mix, list):
                raise ConfigValidationError(
                    "engines.atmosphere.mix must be a list"
                )

            if len(mix) == 0:
                raise ConfigValidationError(
                    "engines.atmosphere.mix must contain at least one sound"
                )

            # Validate min_sounds and max_sounds if present
            min_sounds = atmosphere_config.get("min_sounds", 2)
            max_sounds = atmosphere_config.get("max_sounds", 6)

            if not isinstance(min_sounds, int) or min_sounds < 1:
                raise ConfigValidationError(
                    "engines.atmosphere.min_sounds must be a positive integer"
                )

            if not isinstance(max_sounds, int) or max_sounds < 1:
                raise ConfigValidationError(
                    "engines.atmosphere.max_sounds must be a positive integer"
                )

            if min_sounds > max_sounds:
                raise ConfigValidationError(
                    f"engines.atmosphere.min_sounds ({min_sounds}) cannot exceed max_sounds ({max_sounds})"
                )

            # Validate each sound in the mix
            for i, sound in enumerate(mix):
                if not isinstance(sound, dict):
                    raise ConfigValidationError(
                        f"engines.atmosphere.mix[{i}] must be a dictionary"
                    )

                if "url" not in sound:
                    raise ConfigValidationError(
                        f"engines.atmosphere.mix[{i}].url is required"
                    )

                if not isinstance(sound["url"], str):
                    raise ConfigValidationError(
                        f"engines.atmosphere.mix[{i}].url must be a string"
                    )

                # Validate volume if present (optional, defaults to 100)
                if "volume" in sound:
                    vol = sound["volume"]
                    if not isinstance(vol, (int, float)):
                        raise ConfigValidationError(
                            f"engines.atmosphere.mix[{i}].volume must be a number"
                        )
                    if vol < 0 or vol > 100:
                        raise ConfigValidationError(
                            f"engines.atmosphere.mix[{i}].volume must be 0-100"
                        )

                # Validate optional flag if present
                if "optional" in sound:
                    if not isinstance(sound["optional"], bool):
                        raise ConfigValidationError(
                            f"engines.atmosphere.mix[{i}].optional must be a boolean"
                        )

                # Validate probability if present (only valid with optional=true)
                if "probability" in sound:
                    prob = sound["probability"]
                    if not isinstance(prob, (int, float)):
                        raise ConfigValidationError(
                            f"engines.atmosphere.mix[{i}].probability must be a number"
                        )
                    if prob < 0.0 or prob > 1.0:
                        raise ConfigValidationError(
                            f"engines.atmosphere.mix[{i}].probability must be 0.0-1.0"
                        )
                    if not sound.get("optional", False):
                        raise ConfigValidationError(
                            f"engines.atmosphere.mix[{i}].probability requires optional=true"
                        )

                # Validate pool if present (only valid with optional=true)
                if "pool" in sound:
                    if not isinstance(sound["pool"], str):
                        raise ConfigValidationError(
                            f"engines.atmosphere.mix[{i}].pool must be a string"
                        )
                    if not sound.get("optional", False):
                        raise ConfigValidationError(
                            f"engines.atmosphere.mix[{i}].pool requires optional=true"
                        )

    def _validate_lights_engine(self, lights_config: Dict[str, Any]) -> None:
        """Validate lights engine configuration."""
        if not isinstance(lights_config, dict):
            raise ConfigValidationError(
                "engines.lights must be a dictionary"
            )

        if "enabled" not in lights_config:
            raise ConfigValidationError(
                "engines.lights.enabled is required"
            )

        if not isinstance(lights_config["enabled"], bool):
            raise ConfigValidationError(
                "engines.lights.enabled must be a boolean"
            )

        if lights_config["enabled"]:
            if "animation" not in lights_config:
                raise ConfigValidationError(
                    "engines.lights.animation is required when enabled=true"
                )

            animation = lights_config["animation"]
            if not isinstance(animation, dict):
                raise ConfigValidationError(
                    "engines.lights.animation must be a dictionary"
                )

            # Validate groups exist
            if "groups" not in animation:
                raise ConfigValidationError(
                    "engines.lights.animation.groups is required"
                )

            groups = animation["groups"]
            if not isinstance(groups, dict):
                raise ConfigValidationError(
                    "engines.lights.animation.groups must be a dictionary"
                )

            # Validate at least one group is defined
            valid_groups = ["backdrop", "overhead", "battlefield"]
            if not any(group in groups for group in valid_groups):
                raise ConfigValidationError(
                    f"At least one bulb group must be defined: {', '.join(valid_groups)}"
                )

            # Validate each group
            for group_name, group_config in groups.items():
                if group_name not in valid_groups:
                    raise ConfigValidationError(
                        f"Invalid bulb group: {group_name}\n"
                        f"Valid groups: {', '.join(valid_groups)}"
                    )

                self._validate_group_config(group_config, group_name)

    def _validate_group_config(self, group_config: Dict[str, Any], group_name: str) -> None:
        """Validate a single bulb group configuration."""
        if not isinstance(group_config, dict):
            raise ConfigValidationError(
                f"Group '{group_name}' must be a dictionary"
            )

        if "type" not in group_config:
            raise ConfigValidationError(
                f"Group '{group_name}' missing required field 'type'"
            )

        group_type = group_config["type"]
        valid_types = ["rgb", "scene", "inherit_backdrop", "inherit_overhead", "off"]

        if group_type not in valid_types:
            raise ConfigValidationError(
                f"Group '{group_name}' has invalid type: {group_type}\n"
                f"Valid types: {', '.join(valid_types)}"
            )

        # Type-specific validation
        if group_type == "rgb":
            if "rgb" not in group_config:
                raise ConfigValidationError(
                    f"Group '{group_name}' with type 'rgb' requires 'rgb' field"
                )
        elif group_type == "scene":
            if "scenes" not in group_config:
                raise ConfigValidationError(
                    f"Group '{group_name}' with type 'scene' requires 'scenes' field"
                )

    def discover_all(self) -> List[Dict[str, Any]]:
        """
        Discover and load all YAML configuration files.

        Returns:
            List of loaded configuration dictionaries

        Raises:
            ConfigValidationError: If any config fails validation
        """
        configs = []

        # Find all .yaml and .yml files
        for yaml_file in sorted(self.config_dir.glob("*.yaml")):
            if yaml_file.name == "README.yaml":  # Skip README if it exists
                continue
            try:
                config = self.load(yaml_file.name)
                configs.append(config)
            except Exception as e:
                print(f"WARNING: Failed to load {yaml_file.name}: {str(e)}")
                # Continue loading other files even if one fails

        for yml_file in sorted(self.config_dir.glob("*.yml")):
            try:
                config = self.load(yml_file.name)
                configs.append(config)
            except Exception as e:
                print(f"WARNING: Failed to load {yml_file.name}: {str(e)}")

        return configs

    def get_by_category(self, category: str) -> List[Dict[str, Any]]:
        """
        Get all configurations for a specific category.

        Args:
            category: Category name (e.g., "combat", "social")

        Returns:
            List of configurations matching the category
        """
        all_configs = self.discover_all()
        return [c for c in all_configs if c.get("category") == category]

    def clear_cache(self) -> None:
        """Clear the configuration cache."""
        self._cache.clear()

    def reload(self, filename: str) -> Dict[str, Any]:
        """
        Reload a configuration file, bypassing cache.

        Args:
            filename: Name of YAML file to reload

        Returns:
            Freshly loaded configuration
        """
        # Remove from cache
        if filename in self._cache:
            del self._cache[filename]

        # Load fresh
        return self.load(filename, use_cache=False)
