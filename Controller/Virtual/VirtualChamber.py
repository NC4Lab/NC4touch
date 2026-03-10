"""
Virtual Chamber - Complete virtualized touchscreen chamber for testing.
"""

import os
import time

from Virtual.VirtualDisplayDevice import VirtualDisplayDevice
from Virtual.VirtualBeamBreak import VirtualBeamBreak
from Virtual.VirtualBuzzer import VirtualBuzzer
from Virtual.VirtualLED import VirtualLED
from Virtual.VirtualReward import VirtualReward
from Config import Config

import logging
logger = logging.getLogger(f"session_logger.{__name__}")


class VirtualCamera:
    """Simple virtual camera placeholder."""
    def __init__(self, device="/dev/video0"):
        self.device = "VIRTUAL_CAMERA"
        logger.info(f"Virtual Camera initialized")

    def start_recording(self, filename):
        logger.info(f"Virtual Camera: recording to {filename}")

    def stop_recording(self):
        logger.info("Virtual Camera: recording stopped")


class VirtualChamber:
    """
    Virtual implementation of Chamber class for testing without physical hardware.
    Maintains the same API as the real Chamber class.
    """

    def __init__(self, chamber_config={}, chamber_config_file='~/chamber_config.yaml'):
        logger.info("="*60)
        logger.info("Initializing VIRTUAL Chamber")
        logger.info("="*60)

        self.config = Config(config=chamber_config, config_file=chamber_config_file)
        self.config.ensure_param("chamber_name", "VirtualChamber")
        self.config.ensure_param("name", "VirtualChamber")  # Alias for compatibility with Trainer
        self.config.ensure_param("reward_LED_pin", 21)
        self.config.ensure_param("reward_pump_pin", 27)
        self.config.ensure_param("beambreak_pin", 4)
        self.config.ensure_param("punishment_LED_pin", 17)
        self.config.ensure_param("house_LED_pin", 20)
        self.config.ensure_param("buzzer_pin", 16)
        self.config.ensure_param("reset_pins", [25, 5, 6])
        self.config.ensure_param("camera_device", "/dev/video0")
        self.config.ensure_param("display_width", 1920)
        self.config.ensure_param("display_height", 480)
        self.config.ensure_param("display_zone_widths", [320, 320, 320])
        self.config.ensure_param("display_zone_gaps", None)
        
        self.code_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Image directory for stimulus BMPs (mimics local display storage)
        # Default: <project_root>/data/images/
        default_image_dir = os.path.join(os.path.dirname(os.path.dirname(self.code_dir)), 'data', 'images')
        self.config.ensure_param("image_dir", default_image_dir)

        # No pigpio needed for virtual
        self.pi = None

        # Initialize virtual display-zone devices (legacy-compatible adapter)
        self.left_m0 = VirtualDisplayDevice(
            pi=self.pi,
            id="M0_0",
            reset_pin=self.config["reset_pins"][0],
            location="left",
            image_dir=self.config["image_dir"]
        )
        self.middle_m0 = VirtualDisplayDevice(
            pi=self.pi,
            id="M0_1",
            reset_pin=self.config["reset_pins"][1],
            location="middle",
            image_dir=self.config["image_dir"]
        )
        self.right_m0 = VirtualDisplayDevice(
            pi=self.pi,
            id="M0_2",
            reset_pin=self.config["reset_pins"][2],
            location="right",
            image_dir=self.config["image_dir"]
        )

        self.m0s = [self.left_m0, self.middle_m0, self.right_m0]

        # Initialize virtual peripherals
        self.reward_led = VirtualLED(
            pi=self.pi,
            pin=self.config["reward_LED_pin"],
            brightness=140
        )
        self.punishment_led = VirtualLED(
            pi=self.pi,
            pin=self.config["punishment_LED_pin"],
            brightness=255
        )
        self.house_led = VirtualLED(
            pi=self.pi,
            pin=self.config["house_LED_pin"],
            brightness=255
        )
        self.beambreak = VirtualBeamBreak(
            pi=self.pi,
            pin=self.config["beambreak_pin"]
        )
        self.buzzer = VirtualBuzzer(
            pi=self.pi,
            pin=self.config["buzzer_pin"]
        )
        self.reward = VirtualReward(
            pi=self.pi,
            pin=self.config["reward_pump_pin"]
        )
        self.camera = VirtualCamera(
            device=self.config["camera_device"]
        )

        # Virtual chamber state tracking
        self._state_history = []

        logger.info("Virtual Chamber initialized successfully")
        logger.info(f"  - 3 Virtual display zones (L/M/R)")
        logger.info(f"  - Virtual Reward Pump")
        logger.info(f"  - Virtual Beam Break Sensor")
        logger.info(f"  - 2 Virtual LEDs (reward/punishment)")
        logger.info(f"  - Virtual House LED")
        logger.info(f"  - Virtual Buzzer")
        logger.info("="*60)

    def get_left_m0(self):
        return self.left_m0

    def get_middle_m0(self):
        return self.middle_m0

    def get_right_m0(self):
        return self.right_m0

    def _normalize_zone(self, zone):
        zone_name = str(zone).strip().lower()
        if zone_name in {"left", "middle", "right", "all"}:
            return zone_name
        raise ValueError(f"Unknown display zone '{zone}'")

    def _zone_device(self, zone):
        zone_name = self._normalize_zone(zone)
        if zone_name == "left":
            return self.left_m0
        if zone_name == "middle":
            return self.middle_m0
        if zone_name == "right":
            return self.right_m0
        return None

    def get_display_device(self, zone):
        zone_name = self._normalize_zone(zone)
        if zone_name == "all":
            return None
        return self._zone_device(zone_name)

    # ---- Single-display API used by trainers ----
    def display_command(self, zone, command):
        zone_name = self._normalize_zone(zone)
        if zone_name == "all":
            for display_device in self.m0s:
                display_device.send_command(command)
            return
        self._zone_device(zone_name).send_command(command)

    def display_load_image(self, zone, image_name):
        self.display_command(zone, f"IMG:{image_name}")

    def display_show(self, zone):
        self.display_command(zone, "SHOW")

    def display_clear(self, zone="all"):
        zone_name = self._normalize_zone(zone)
        if zone_name == "all":
            self.display_command("all", "BLACK")
            return
        self.display_command(zone_name, "BLACK")

    def display_was_touched(self, zone):
        zone_name = self._normalize_zone(zone)
        if zone_name == "all":
            return any(display_device.was_touched() for display_device in self.m0s)
        return self._zone_device(zone_name).was_touched()

    def configure_display_zones(self, zone_widths=None, zone_gaps=None, center_layout=None):
        """Update virtual layout config used by VirtualChamberGUI rendering."""
        if zone_widths is not None:
            self.config["display_zone_widths"] = zone_widths
        if zone_gaps is not None:
            self.config["display_zone_gaps"] = zone_gaps

    def get_display_layout(self):
        """Return virtual single-display layout geometry for GUI rendering."""
        display_width = int(self.config["display_width"])
        display_height = int(self.config["display_height"])
        zone_widths = [int(v) for v in self.config["display_zone_widths"]]
        gaps = self.config["display_zone_gaps"]

        if gaps is None or gaps == "auto":
            zone_total = sum(zone_widths)
            leftover = max(0, display_width - zone_total)
            base = leftover // 4
            rem = leftover % 4
            gaps = [base + (1 if i < rem else 0) for i in range(4)]
        else:
            gaps = [int(v) for v in gaps]
            if len(gaps) != 4:
                gaps = [0, 0, 0, 0]

        left_x = gaps[0]
        middle_x = left_x + zone_widths[0] + gaps[1]
        right_x = middle_x + zone_widths[1] + gaps[2]

        return {
            "display_width": display_width,
            "display_height": display_height,
            "zone_widths": zone_widths,
            "gaps": gaps,
            "zones": {
                "left": {"x": left_x, "y": 0, "w": zone_widths[0], "h": display_height},
                "middle": {"x": middle_x, "y": 0, "w": zone_widths[1], "h": display_height},
                "right": {"x": right_x, "y": 0, "w": zone_widths[2], "h": display_height},
            },
        }

    def __del__(self):
        """Cleanup virtual resources."""
        if hasattr(self, 'm0s'):
            for display_device in self.m0s:
                display_device.stop()
        logger.info("Virtual Chamber cleaned up")

    def compile_sketch(self, sketch_path=None):
        """Virtual method - no compilation needed."""
        logger.info("Virtual Chamber: Sketch compilation skipped (virtual mode)")

    def arduino_cli_discover(self):
        """Virtual method - simulates board discovery."""
        logger.info("Virtual Chamber: Board discovery skipped (virtual mode)")
        self.discovered_boards = [f"VIRTUAL_PORT_{i}" for i in range(3)]

    def m0_discover(self):
        """Virtual method - simulates display-controller discovery."""
        logger.info("Virtual Chamber: display-controller discovery completed (virtual mode)")
        return {
            "M0_0": "VIRTUAL_PORT_0",
            "M0_1": "VIRTUAL_PORT_1",
            "M0_2": "VIRTUAL_PORT_2"
        }

    def m0_reset(self):
        """Virtual method - simulates display-controller reset."""
        logger.info("Virtual Chamber: display controllers reset (virtual mode)")

    def initialize_m0s(self):
        """Initialize all display-zone devices."""
        for display_device in self.m0s:
            display_device.initialize()
            time.sleep(0.1)
        logger.info("All virtual display-zone devices initialized")

    def initialize_display_devices(self):
        """Preferred alias for initialize_m0s()."""
        self.initialize_m0s()

    def m0_send_command(self, command):
        """
        Sends a command to all display-zone devices.
        """
        for display_device in self.m0s:
            display_device.send_command(command)
        logger.debug(f"Virtual Chamber: sent command '{command}' to all display zones")

    def send_display_command(self, command):
        """Preferred alias for m0_send_command()."""
        self.m0_send_command(command)

    def m0_show_image(self):
        """Virtual method - show images on all M0s."""
        self.m0_send_command("SHOW")

    def m0_clear(self):
        """Virtual method - clear images on all M0s."""
        self.m0_send_command("BLACK")

    def default_state(self):
        """
        Reset chamber to default state (all hardware off/clear).
        """
        self.m0_send_command("CLEAR")
        self.reward_led.deactivate()
        self.punishment_led.deactivate()
        self.house_led.deactivate()
        self.buzzer.deactivate()
        self.reward.stop()
        logger.info("Virtual Chamber: reset to default state")

    # ===== Virtual-specific methods for simulation and testing =====

    def get_state(self):
        """Get complete virtual chamber state."""
        left_device = self.get_display_device("left")
        middle_device = self.get_display_device("middle")
        right_device = self.get_display_device("right")

        left_state = {
            'is_touched': left_device.is_touched(),
            'current_image': left_device.get_current_image(),
            'touch_coords': left_device.get_touch_coordinates()
        }
        middle_state = {
            'is_touched': middle_device.is_touched(),
            'current_image': middle_device.get_current_image(),
            'touch_coords': middle_device.get_touch_coordinates()
        }
        right_state = {
            'is_touched': right_device.is_touched(),
            'current_image': right_device.get_current_image(),
            'touch_coords': right_device.get_touch_coordinates()
        }

        return {
            'timestamp': time.time(),
            'left_display': left_state,
            'middle_display': middle_state,
            'right_display': right_state,
            # Legacy keys retained for compatibility with older scripts/UI.
            'left_m0': left_state,
            'middle_m0': middle_state,
            'right_m0': right_state,
            'reward_led': self.reward_led.get_state(),
            'punishment_led': self.punishment_led.get_state(),
            'house_led': self.house_led.get_state(),
            'beambreak': {
                'state': self.beambreak.state,
                'last_break': self.beambreak.last_break_time
            },
            'buzzer': self.buzzer.get_state(),
            'reward': self.reward.get_state()
        }

    def log_state(self):
        """Log current state to history."""
        state = self.get_state()
        self._state_history.append(state)
        return state

    def get_state_history(self):
        """Get all logged states."""
        return self._state_history

    def clear_state_history(self):
        """Clear state history."""
        self._state_history = []
