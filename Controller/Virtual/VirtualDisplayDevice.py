"""
Virtual display-zone device for touchscreen simulation.

Provides a legacy-compatible touchscreen interface without requiring physical hardware.
"""

import time
import threading
from enum import Enum
import os

import logging
logger = logging.getLogger(f"session_logger.{__name__}")


class DisplayDeviceMode(Enum):
    UNINITIALIZED = 0
    PORT_OPEN = 1
    SERIAL_COMM = 2
    PORT_CLOSED = 3
    UD = 4


class VirtualDisplayDevice:
    """
    Virtual implementation of the legacy touchscreen device API.
    Maintains legacy-compatible methods for existing trainer and script code.
    """

    def __init__(self, pi=None, id=None, reset_pin=None,
                 port=None, baudrate=115200, location=None, image_dir=None):
        self.id = id
        self.location = location
        self.image_dir = image_dir or os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'data', 'images')

        # Virtual touchscreen state
        self._is_touched = False
        self._touch_coordinates = (0, 0)
        self._current_image = None
        self._current_image_path = None
        self._display_enabled = True
        self._loaded_image = None

        logger.info(f"[{self.id}] Virtual display device initialized")

    def __del__(self):
        pass

    def stop(self):
        """Virtual stop (no-op for single-display)."""
        pass

    def initialize(self):
        """Virtual initialize (no-op for single-display)."""
        logger.debug(f"[{self.id}] Virtual device initialized")

    def send_command(self, command):
        """
        Send a command to the virtual device.
        """
        logger.debug(f"[{self.id}] Virtual command sent: {command}")
        
        # Simulate responses for known commands
        if command == "WHOAREYOU?":
            logger.info(f"[{self.id}] ID:{self.id}")
        elif command.startswith("IMG:"):
            # Load image (IMG:A01 resolves to A01.bmp)
            image_name = command.split(":", 1)[1]
            image_path = self._resolve_image_path(image_name)
            if image_path:
                self._loaded_image = image_name
                logger.debug(f"[{self.id}] Loaded image: {image_name} from {image_path}")
            else:
                logger.warning(f"[{self.id}] Image not found: {image_name}")
        elif command == "SHOW":
            # Display the loaded image
            if self._loaded_image:
                self._current_image = self._loaded_image
                self._current_image_path = self._resolve_image_path(self._loaded_image)
                logger.debug(f"[{self.id}] Showing image: {self._current_image}")
            else:
                logger.warning(f"[{self.id}] SHOW called but no image loaded")
        elif command == "BLACK":
            # Clear display to black
            self._current_image = None
            self._current_image_path = None
            self._loaded_image = None
            logger.debug(f"[{self.id}] Display cleared (BLACK)")
        elif command.startswith("DISPLAY:"):
            # Legacy support: DISPLAY:path displays directly
            image_path = command.split(":", 1)[1]
            self._current_image = image_path
            self._current_image_path = image_path
            logger.debug(f"[{self.id}] Displaying image: {image_path}")
        elif command == "CLEAR":
            # Legacy support
            self._current_image = None
            self._current_image_path = None
            logger.debug(f"[{self.id}] Display cleared")
        elif command == "SCREENSHARE":
            logger.debug(f"[{self.id}] Screenshare mode activated")

    def is_touched(self):
        """
        Check if the touchscreen is currently being touched.
        Method kept for compatibility with existing trainer/script code.
        """
        return self._is_touched

    def was_touched(self):
        """Return touch edge state and reset, matching physical device API."""
        touched = self._is_touched
        self._is_touched = False
        return touched

    # ===== Virtual-specific methods for simulation =====

    def simulate_touch(self, x=None, y=None, duration=0.1):
        """
        Simulate a touch event on the virtual touchscreen.
        
        Args:
            x: X coordinate (0-320)
            y: Y coordinate (0-480)
            duration: How long the touch lasts in seconds
        """
        if x is None:
            x = 160  # Center
        if y is None:
            y = 240  # Center
            
        self._touch_coordinates = (x, y)
        self._is_touched = True
        logger.info(f"[{self.id}] Virtual touch at ({x}, {y})")

        # Auto-release after duration
        def release_touch():
            time.sleep(duration)
            self._is_touched = False
            logger.debug(f"[{self.id}] Touch released")

        threading.Thread(target=release_touch, daemon=True).start()

    def _resolve_image_path(self, image_name):
        """Resolve image name to full file path."""
        # If already a full path, return as-is
        if os.path.isabs(image_name) or '/' in image_name:
            return image_name
        
        # Try with .bmp extension
        bmp_path = os.path.join(self.image_dir, f"{image_name}.bmp")
        if os.path.exists(bmp_path):
            return bmp_path
        
        # Try without extension (in case it's included)
        direct_path = os.path.join(self.image_dir, image_name)
        if os.path.exists(direct_path):
            return direct_path
        
        logger.warning(f"[{self.id}] Image file not found: {image_name} in {self.image_dir}")
        return None

    def get_current_image(self):
        """Get the currently displayed image name."""
        return self._current_image
    
    def get_current_image_path(self):
        """Get the full path to the currently displayed image file."""
        return self._current_image_path

    def get_touch_coordinates(self):
        """Get the last touch coordinates."""
        return self._touch_coordinates

    def set_display_enabled(self, enabled):
        """Enable or disable the virtual display."""
        self._display_enabled = enabled
        logger.debug(f"[{self.id}] Display {'enabled' if enabled else 'disabled'}")

