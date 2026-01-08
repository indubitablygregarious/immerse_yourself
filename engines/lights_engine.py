"""
Lights Engine - Controls WIZ smart bulbs with async animations

This engine manages WIZ smart bulbs with sophisticated animation loops.
It supports RGB color modes, WIZ scene presets, flash effects, and
hot-swapping configurations without stopping the lights.
"""

import asyncio
import configparser
import random
from pathlib import Path
from typing import Dict, List, Optional, Any
from pywizlight import wizlight, PilotBuilder


# Global flag to disable lights for the session
# When True, all lights operations become no-ops
_lights_disabled_for_session = False


def disable_lights_for_session():
    """Disable all lights operations for this session."""
    global _lights_disabled_for_session
    _lights_disabled_for_session = True


def enable_lights_for_session():
    """Re-enable lights operations for this session."""
    global _lights_disabled_for_session
    _lights_disabled_for_session = False


def are_lights_disabled() -> bool:
    """Check if lights are disabled for this session."""
    return _lights_disabled_for_session


class LightBulbGroup:
    """
    Represents a group of bulbs with shared animation behavior.

    Bulbs are organized into groups (backdrop, overhead, battlefield)
    that can be controlled independently with their own animation configs.

    Attributes:
        name: Group identifier ("backdrop", "overhead", "battlefield")
        bulbs: List of wizlight bulb instances
    """

    def __init__(self, name: str, ip_addresses: List[str]):
        """
        Initialize a light bulb group.

        Args:
            name: Group identifier
            ip_addresses: List of IP addresses for bulbs in this group
        """
        self.name = name
        self.bulbs = [wizlight(ip) for ip in ip_addresses]

    def apply_pilot(self, pilot: PilotBuilder) -> None:
        """
        Apply a pilot configuration to all bulbs in the group (fire-and-forget).

        Args:
            pilot: PilotBuilder with desired light state
        """
        for bulb in self.bulbs:
            # Fire-and-forget: create task without awaiting response
            task = asyncio.create_task(self._send_to_bulb(bulb, pilot))
            task.add_done_callback(self._handle_bulb_error)

    async def _send_to_bulb(self, bulb: wizlight, pilot: PilotBuilder) -> None:
        """Send command to a single bulb."""
        await bulb.turn_on(pilot)

    def _handle_bulb_error(self, task: asyncio.Task) -> None:
        """Handle errors from fire-and-forget bulb commands."""
        try:
            task.result()
        except Exception as e:
            print(f"WARNING: Failed to control bulb in {self.name} group: {e}")

    def turn_off(self) -> None:
        """Turn off all bulbs in the group (fire-and-forget)."""
        for bulb in self.bulbs:
            # Fire-and-forget: create task without awaiting response
            task = asyncio.create_task(self._turn_off_bulb(bulb))
            task.add_done_callback(self._handle_turnoff_error)

    async def _turn_off_bulb(self, bulb: wizlight) -> None:
        """Turn off a single bulb."""
        await bulb.turn_off()

    def _handle_turnoff_error(self, task: asyncio.Task) -> None:
        """Handle errors from fire-and-forget turn off commands."""
        try:
            task.result()
        except Exception as e:
            print(f"WARNING: Failed to turn off bulb in {self.name} group: {e}")


class LightsEngine:
    """
    Manages WIZ smart bulb animations with async control.

    This engine controls multiple groups of WIZ bulbs with sophisticated
    animation patterns including RGB colors, scenes, flashes, and randomization.
    Supports hot-swapping configurations without stopping the animation loop.

    Attributes:
        config_file: Path to WIZ bulb configuration file
        bulb_groups: Dictionary of LightBulbGroup instances
        animation_task: Current async animation task
        should_stop: Flag to gracefully stop animation loop
        current_config: Currently active animation configuration
    """

    def __init__(self, config_file: str = ".wizbulb.ini"):
        """
        Initialize the Lights Engine.

        Args:
            config_file: Path to WIZ bulb configuration file
                        (default: .wizbulb.ini in current directory)

        Raises:
            FileNotFoundError: If config file doesn't exist (unless lights disabled)
        """
        self.config_file = config_file
        self.bulb_groups: Dict[str, LightBulbGroup] = {}
        self.animation_task: Optional[asyncio.Task] = None
        self.should_stop = False
        self.current_config: Optional[Dict[str, Any]] = None
        self._config_lock = asyncio.Lock()
        self._disabled = _lights_disabled_for_session

        # Skip loading bulbs if lights are disabled
        if not self._disabled:
            self._load_bulbs()

    def _load_bulbs(self) -> None:
        """
        Load bulb IP addresses from config file and create groups.

        Expected config format:
        [DEFAULT]
        backdrop_bulbs = 192.168.1.165 192.168.1.159 192.168.1.160
        overhead_bulbs = 192.168.1.161 192.168.1.162
        battlefield_bulbs = 192.168.1.163 192.168.1.164
        """
        if not Path(self.config_file).exists():
            raise FileNotFoundError(
                f"WIZ bulb config file not found: {self.config_file}\n"
                "Please create .wizbulb.ini with your bulb IP addresses."
            )

        config = configparser.ConfigParser()
        config.read(self.config_file)

        try:
            # Load bulb groups from config
            backdrop_ips = config["DEFAULT"]["backdrop_bulbs"].split()
            overhead_ips = config["DEFAULT"]["overhead_bulbs"].split()
            battlefield_ips = config["DEFAULT"]["battlefield_bulbs"].split()

            # Create bulb group objects
            self.bulb_groups["backdrop"] = LightBulbGroup("backdrop", backdrop_ips)
            self.bulb_groups["overhead"] = LightBulbGroup("overhead", overhead_ips)
            self.bulb_groups["battlefield"] = LightBulbGroup("battlefield", battlefield_ips)

        except KeyError as e:
            raise KeyError(
                f"Missing required field in {self.config_file}: {e}\n"
                "Required fields: backdrop_bulbs, overhead_bulbs, battlefield_bulbs"
            )

    def _resolve_inheritance(self, group_config: Dict[str, Any], all_configs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Resolve group inheritance (inherit_backdrop, inherit_overhead).

        Args:
            group_config: Configuration for a single bulb group
            all_configs: All group configurations for resolving inheritance

        Returns:
            Resolved configuration with inheritance applied
        """
        if group_config.get("type") == "inherit_backdrop":
            return all_configs.get("backdrop", group_config)
        elif group_config.get("type") == "inherit_overhead":
            return all_configs.get("overhead", group_config)
        else:
            return group_config

    def _is_group_enabled(self, group_config: Dict[str, Any]) -> bool:
        """
        Check if a group is enabled.

        Groups can be disabled with 'enabled: false' or 'type: off'.

        Args:
            group_config: Configuration for a single bulb group

        Returns:
            True if group should be animated, False if it should be off
        """
        if group_config.get("enabled") is False:
            return False
        if group_config.get("type") == "off":
            return False
        return True

    def _apply_to_group(self, group: LightBulbGroup, config: Dict[str, Any]) -> None:
        """
        Apply lighting configuration to a group (no sleep, fire-and-forget).

        Args:
            group: Light bulb group to control
            config: Animation configuration for this group
        """
        group_type = config.get("type", "rgb")

        if group_type == "rgb":
            # RGB color mode
            rgb_config = config.get("rgb", {})
            base = rgb_config.get("base", [128, 128, 128])
            variance = rgb_config.get("variance", [20, 20, 20])

            # Calculate color with random variance
            r = base[0] + int(random.random() * variance[0])
            g = base[1] + int(random.random() * variance[1])
            b = base[2] + int(random.random() * variance[2])

            # Clamp to valid range
            r = max(0, min(255, r))
            g = max(0, min(255, g))
            b = max(0, min(255, b))

            # Calculate brightness
            brightness_config = config.get("brightness", {})
            min_bright = brightness_config.get("min", 100)
            max_bright = brightness_config.get("max", 255)
            brightness = min_bright + int(random.random() * (max_bright - min_bright))

            pilot = PilotBuilder(rgb=(r, g, b), brightness=brightness)
            group.apply_pilot(pilot)

        elif group_type == "scene":
            # WIZ scene mode
            scenes_config = config.get("scenes", {})
            scene_ids = scenes_config.get("ids", [5, 28, 31])
            speed_min = scenes_config.get("speed_min", 10)
            speed_max = scenes_config.get("speed_max", 190)

            # Random scene and speed
            scene_id = random.choice(scene_ids)
            speed = speed_min + int(random.random() * (speed_max - speed_min))

            # Calculate brightness
            brightness_config = config.get("brightness", {})
            min_bright = brightness_config.get("min", 100)
            max_bright = brightness_config.get("max", 255)
            brightness = min_bright + int(random.random() * (max_bright - min_bright))

            pilot = PilotBuilder(scene=scene_id, speed=speed, brightness=brightness)
            group.apply_pilot(pilot)

    async def _animate_group(
        self,
        group: LightBulbGroup,
        config: Dict[str, Any],
        cycletime: float,
        bulb_count: int
    ) -> None:
        """
        Apply animation to a group with timing delay.

        Args:
            group: Light bulb group to animate
            config: Animation configuration for this group
            cycletime: Time for full animation cycle
            bulb_count: Total number of bulbs (for timing calculation)
        """
        # Handle flash effect
        flash_config = config.get("flash", {})
        flash_prob = flash_config.get("probability", 0.0)
        if random.random() < flash_prob:
            # Flash effect
            flash_color = flash_config.get("color", [255, 255, 255])
            flash_brightness = flash_config.get("brightness", 255)
            flash_duration = flash_config.get("duration", 1.0)

            pilot = PilotBuilder(
                rgb=tuple(flash_color),
                brightness=flash_brightness
            )
            group.apply_pilot(pilot)
            await asyncio.sleep(flash_duration)

        # Apply the lighting config
        self._apply_to_group(group, config)

        # Sleep based on cycletime and number of bulbs
        await asyncio.sleep(cycletime / bulb_count)

    async def _initialize_lights(self, config: Dict[str, Any]) -> None:
        """
        Set initial state for all bulbs based on configuration.

        Args:
            config: Animation configuration
        """
        groups_config = config.get("groups", {})

        # Resolve inheritance for each group
        resolved_configs = {}
        for group_name in ["backdrop", "overhead", "battlefield"]:
            if group_name in groups_config:
                group_config = groups_config[group_name]
                resolved_configs[group_name] = self._resolve_inheritance(
                    group_config, groups_config
                )

        # Initialize each group (instant, no sleep)
        for group_name, group_config in resolved_configs.items():
            if group_name in self.bulb_groups:
                group = self.bulb_groups[group_name]
                if self._is_group_enabled(group_config):
                    self._apply_to_group(group, group_config)
                else:
                    # Turn off disabled groups
                    group.turn_off()

    async def run_animation_loop(self, animation_config: Dict[str, Any]) -> None:
        """
        Main animation loop - runs indefinitely until stopped.

        Configuration structure:
        {
            "cycletime": 12,
            "flash_variance": 25,
            "groups": {
                "backdrop": {
                    "type": "rgb" | "scene" | "inherit_backdrop" | "inherit_overhead",
                    "rgb": {
                        "base": [128, 128, 128],
                        "variance": [20, 20, 20]
                    },
                    "scene": {
                        "ids": [5, 28, 31],
                        "speed_min": 10,
                        "speed_max": 190
                    },
                    "brightness": {
                        "min": 74,
                        "max": 255
                    },
                    "flash": {
                        "probability": 0.05,
                        "color": [255, 255, 255],
                        "brightness": 230,
                        "duration": 1.0
                    }
                },
                "overhead": { ... },
                "battlefield": { ... }
            }
        }

        Args:
            animation_config: Animation configuration dictionary
        """
        async with self._config_lock:
            self.current_config = animation_config

        # Initialize lights
        await self._initialize_lights(animation_config)

        # Get configuration
        cycletime = animation_config.get("cycletime", 12)
        groups_config = animation_config.get("groups", {})

        # Resolve inheritance for each group
        resolved_configs = {}
        for group_name in ["backdrop", "overhead", "battlefield"]:
            if group_name in groups_config:
                group_config = groups_config[group_name]
                resolved_configs[group_name] = self._resolve_inheritance(
                    group_config, groups_config
                )

        # Build list of enabled bulb groups for shuffling
        all_groups = []
        for group_name, group_config in resolved_configs.items():
            if group_name in self.bulb_groups and self._is_group_enabled(group_config):
                all_groups.append((self.bulb_groups[group_name], group_config))

        # Count total bulbs for timing
        total_bulbs = sum(len(group.bulbs) for group, _ in all_groups)

        # Main animation loop
        while not self.should_stop:
            print("Light animation cycle start")

            # Check if config was updated
            async with self._config_lock:
                if self.current_config != animation_config:
                    # Config was hot-swapped, use new config
                    animation_config = self.current_config
                    cycletime = animation_config.get("cycletime", 12)
                    groups_config = animation_config.get("groups", {})

                    # Re-resolve inheritance
                    resolved_configs = {}
                    for group_name in ["backdrop", "overhead", "battlefield"]:
                        if group_name in groups_config:
                            group_config = groups_config[group_name]
                            resolved_configs[group_name] = self._resolve_inheritance(
                                group_config, groups_config
                            )

                    # Rebuild group list (only enabled groups)
                    all_groups = []
                    for group_name, group_config in resolved_configs.items():
                        if group_name in self.bulb_groups and self._is_group_enabled(group_config):
                            all_groups.append((self.bulb_groups[group_name], group_config))

                    total_bulbs = sum(len(group.bulbs) for group, _ in all_groups)

            # Shuffle for variety
            random.shuffle(all_groups)

            # Animate each group
            for group, group_config in all_groups:
                if self.should_stop:
                    break
                await self._animate_group(group, group_config, cycletime, total_bulbs)

    async def start(self, animation_config: Dict[str, Any]) -> None:
        """
        Start animation loop in background task.

        Args:
            animation_config: Animation configuration dictionary
        """
        # No-op if lights disabled for session
        if self._disabled:
            return

        self.should_stop = False
        self.animation_task = asyncio.create_task(
            self.run_animation_loop(animation_config)
        )

    async def stop(self) -> None:
        """Stop animation loop gracefully."""
        # No-op if lights disabled for session
        if self._disabled:
            return

        self.should_stop = True
        if self.animation_task:
            self.animation_task.cancel()
            try:
                await self.animation_task
            except asyncio.CancelledError:
                pass

    async def update_config(self, animation_config: Dict[str, Any]) -> None:
        """
        Hot-swap animation configuration without stopping lights.

        This allows changing environments while keeping lights running,
        preventing blackouts during transitions.

        Args:
            animation_config: New animation configuration
        """
        # No-op if lights disabled for session
        if self._disabled:
            return

        async with self._config_lock:
            self.current_config = animation_config
        print("Light configuration updated (hot-swapped)")

    def is_running(self) -> bool:
        """
        Check if animation loop is currently running.

        Returns:
            True if running, False otherwise
        """
        if self._disabled:
            return False
        return self.animation_task is not None and not self.animation_task.done()
