"""
Virtual LED for visual feedback simulation.
"""

import logging
logger = logging.getLogger(f"session_logger.{__name__}")


class VirtualLED:
    # Virtual LED class - mimics physical LED API

    def __init__(self, pi=None, pin=21, rgb_pins=None, frequency=5000, range=255, brightness=140):
        self.pin = pin
        self.frequency = frequency
        self.range = range
        self.brightness = brightness
        self.color = (brightness, brightness, brightness)

        # RGB support
        if rgb_pins is not None and len(rgb_pins) == 3:
            self.r_pin, self.g_pin, self.b_pin = rgb_pins
            self.show_color = True
        else:
            self.r_pin = None
            self.g_pin = None
            self.b_pin = None
            self.show_color = False

        # Virtual state
        self._is_on = False
        self._current_brightness = 0
        self._current_color = (0, 0, 0)

        logger.info(f"Virtual LED initialized on pin {self.pin} "
                   f"({'RGB' if self.show_color else 'white'})")

    def on(self, brightness=None):
        """Turn the LED on."""
        if brightness is not None:
            self.brightness = brightness
        self._is_on = True
        self._current_brightness = self.brightness
        logger.info(f"Virtual LED ON (pin {self.pin}, brightness={self.brightness})")

    def off(self):
        """Turn the LED off."""
        self._is_on = False
        self._current_brightness = 0
        logger.info(f"Virtual LED OFF (pin {self.pin})")

    def set_brightness(self, brightness):
        """Set LED brightness (0-255)."""
        self.brightness = brightness
        if self._is_on:
            self._current_brightness = brightness
        logger.debug(f"Virtual LED brightness set to {brightness}")

    def set_color(self, color):
        # Set LED color - accepts list/tuple [r, g, b]
        if not self.show_color:
            logger.warning("Virtual LED does not support RGB")
            return

        r, g, b = color[0], color[1], color[2]
        self.color = (r, g, b)
        if self._is_on:
            self._current_color = (r, g, b)
        logger.info(f"Virtual LED color set to RGB({r}, {g}, {b})")

    def pulse(self, duration=1.0):
        # Pulse effect
        logger.info(f"Virtual LED pulsing for {duration}s")
        self.on()

    def activate(self):
        """Activate the LED (alias for on() to match physical LED API)."""
        self.on()

    def deactivate(self):
        """Deactivate the LED (alias for off() to match physical LED API)."""
        self.off()

    # ===== Virtual-specific methods =====

    def get_state(self):
        # Return current LED state
        return {
            'is_on': self._is_on,
            'brightness': self._current_brightness,
            'color': self._current_color if self.show_color else None,
            'pin': self.pin
        }
