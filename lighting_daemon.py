#!/usr/bin/env python3
"""
Lighting Daemon - Background process for persistent light animation

This daemon runs as a separate process, receiving commands via stdin and
sending status/errors via stdout. It keeps lights running continuously
while allowing hot-swapping of animation configurations.

Communication Protocol:
- Input (stdin): JSON commands, one per line
- Output (stdout): JSON responses, one per line

Commands:
  {"command": "update_animation", "config": {...}}
  {"command": "stop"}

Responses:
  {"type": "status", "message": "...", ...}
  {"type": "error", "message": "...", "timestamp": "..."}
"""

import asyncio
import json
import sys
import signal
from datetime import datetime
from typing import Dict, Any, Optional
from engines.lights_engine import LightsEngine


class LightingDaemon:
    """
    Lighting daemon process for background light control.

    This daemon manages a LightsEngine instance and handles IPC commands
    to update animations or stop the daemon gracefully.

    Attributes:
        lights_engine: LightsEngine instance
        running: Whether daemon is running
        animation_running: Whether animation loop is active
    """

    def __init__(self):
        """Initialize the lighting daemon."""
        self.lights_engine: Optional[LightsEngine] = None
        self.running = True
        self.animation_running = False
        self._setup_signal_handlers()

    def _setup_signal_handlers(self) -> None:
        """Setup signal handlers for graceful shutdown."""
        signal.signal(signal.SIGTERM, self._handle_shutdown)
        signal.signal(signal.SIGINT, self._handle_shutdown)

    def _handle_shutdown(self, signum, frame) -> None:
        """Handle shutdown signals."""
        self.running = False
        self._send_response({
            "type": "status",
            "message": "Received shutdown signal"
        })

    def _send_response(self, response: Dict[str, Any]) -> None:
        """
        Send JSON response to stdout.

        Args:
            response: Dictionary to send as JSON
        """
        try:
            json_str = json.dumps(response)
            print(json_str, flush=True)
        except Exception as e:
            # Fallback if JSON encoding fails
            print(json.dumps({
                "type": "error",
                "message": f"Failed to encode response: {str(e)}"
            }), flush=True)

    def _send_error(self, message: str, exception: Optional[Exception] = None) -> None:
        """
        Send error response.

        Args:
            message: Error message
            exception: Optional exception that caused the error
        """
        error_response = {
            "type": "error",
            "message": message,
            "timestamp": datetime.now().isoformat()
        }

        if exception:
            error_response["exception"] = str(exception)
            error_response["exception_type"] = type(exception).__name__

        self._send_response(error_response)

    async def _initialize_lights_engine(self) -> bool:
        """
        Initialize the lights engine.

        Returns:
            True if successful, False otherwise
        """
        try:
            self.lights_engine = LightsEngine()
            self._send_response({
                "type": "status",
                "message": "Lights engine initialized",
                "bulb_groups": list(self.lights_engine.bulb_groups.keys())
            })
            return True
        except FileNotFoundError as e:
            self._send_error(
                "Failed to initialize lights engine: .wizbulb.ini not found",
                e
            )
            return False
        except Exception as e:
            self._send_error(
                "Failed to initialize lights engine",
                e
            )
            return False

    async def _handle_update_animation(self, config: Dict[str, Any]) -> None:
        """
        Handle update_animation command.

        Args:
            config: Animation configuration dictionary
        """
        if self.lights_engine is None:
            self._send_error("Lights engine not initialized")
            return

        try:
            if self.animation_running:
                # Hot-swap configuration
                await self.lights_engine.update_config(config)
                self._send_response({
                    "type": "status",
                    "message": "Animation configuration updated (hot-swapped)"
                })
            else:
                # Start new animation
                await self.lights_engine.start(config)
                self.animation_running = True
                self._send_response({
                    "type": "status",
                    "message": "Animation started"
                })
        except Exception as e:
            self._send_error(
                "Failed to update animation",
                e
            )

    async def _handle_stop(self) -> None:
        """Handle stop command."""
        if self.lights_engine is None:
            self._send_response({
                "type": "status",
                "message": "Lights engine not initialized, nothing to stop"
            })
            return

        try:
            if self.animation_running:
                await self.lights_engine.stop()
                self.animation_running = False
                self._send_response({
                    "type": "status",
                    "message": "Animation stopped"
                })
            else:
                self._send_response({
                    "type": "status",
                    "message": "No animation running"
                })
        except Exception as e:
            self._send_error(
                "Failed to stop animation",
                e
            )

    async def _process_command(self, command_str: str) -> None:
        """
        Process a command from stdin.

        Args:
            command_str: JSON command string
        """
        try:
            command = json.loads(command_str)
        except json.JSONDecodeError as e:
            self._send_error(
                f"Invalid JSON command: {command_str}",
                e
            )
            return

        if not isinstance(command, dict):
            self._send_error(
                f"Command must be a JSON object, got: {type(command).__name__}"
            )
            return

        cmd_type = command.get("command")

        if cmd_type == "update_animation":
            config = command.get("config")
            if config is None:
                self._send_error("update_animation command requires 'config' field")
                return
            await self._handle_update_animation(config)

        elif cmd_type == "stop":
            await self._handle_stop()

        elif cmd_type == "ping":
            # Health check
            self._send_response({
                "type": "status",
                "message": "pong",
                "animation_running": self.animation_running
            })

        else:
            self._send_error(
                f"Unknown command: {cmd_type}"
            )

    async def run(self) -> None:
        """
        Main daemon loop.

        Reads commands from stdin and processes them until shutdown.
        """
        # Initialize lights engine
        if not await self._initialize_lights_engine():
            self._send_error("Daemon startup failed")
            return

        self._send_response({
            "type": "status",
            "message": "Lighting daemon ready"
        })

        # Main command processing loop
        loop = asyncio.get_event_loop()

        try:
            while self.running:
                # Read command from stdin (non-blocking with timeout)
                try:
                    line = await asyncio.wait_for(
                        loop.run_in_executor(None, sys.stdin.readline),
                        timeout=0.1
                    )

                    if not line:
                        # EOF reached
                        break

                    line = line.strip()
                    if line:
                        await self._process_command(line)

                except asyncio.TimeoutError:
                    # No input available, continue loop
                    # This allows the animation task to run
                    await asyncio.sleep(0.01)

                except Exception as e:
                    self._send_error(
                        "Error reading command",
                        e
                    )
                    await asyncio.sleep(0.1)

        finally:
            # Cleanup
            if self.lights_engine and self.animation_running:
                await self.lights_engine.stop()

            self._send_response({
                "type": "status",
                "message": "Lighting daemon shut down"
            })


async def main():
    """Main entry point for lighting daemon."""
    daemon = LightingDaemon()

    try:
        await daemon.run()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(json.dumps({
            "type": "error",
            "message": f"Daemon crashed: {str(e)}",
            "exception_type": type(e).__name__
        }), flush=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
