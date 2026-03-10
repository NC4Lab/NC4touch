# Chamber class for the touchscreen chamber
#
# Manu Madhav
# 2025

try:
    import pigpio
except ImportError:
    pigpio = None

from LED import LED
from Reward import Reward
from BeamBreak import BeamBreak
from Buzzer import Buzzer
from Display import DisplayManager, DisplayZone, DisplayZoneDevice
from Camera import Camera
from Config import Config

import logging
logger = logging.getLogger(f"session_logger.{__name__}")


class Chamber:
    """Single-display chamber for NC4Touch."""

    def __init__(self, chamber_config={}, chamber_config_file='~/chamber_config.yaml'):
        logger.info("Initializing Chamber...")
        self.config = Config(config=chamber_config, config_file=chamber_config_file)
        self.config.ensure_param("chamber_name", "Chamber0")
        self.config.ensure_param("reward_LED_pins", [13, 21, 26])
        self.config.ensure_param("reward_pump_pin", 27)
        self.config.ensure_param("beambreak_pin", 4)
        self.config.ensure_param("punishment_LED_pins", [18, 19, 17])
        self.config.ensure_param("house_LED_pin", 20)
        self.config.ensure_param("buzzer_pin", 16)
        self.config.ensure_param("camera_device", "/dev/video0")
        self.config.ensure_param("reward_led_brightness", 140)
        self.config.ensure_param("punishment_led_brightness", 255)
        self.config.ensure_param("house_led_brightness", 100)
        self.config.ensure_param("buzzer_volume", 60)
        self.config.ensure_param("buzzer_frequency", 6000)
        self.config.ensure_param("beambreak_memory", 0.2)

        # Single-display config
        self.config.ensure_param("display_width", 1920)
        self.config.ensure_param("display_height", 480)
        self.config.ensure_param("display_image_folder", "../data/images")
        self.config.ensure_param("display_zone_widths", [320, 320, 320])
        self.config.ensure_param("display_zone_gaps", None)
        self.config.ensure_param("display_center_layout", True)

        # LED colors
        self.config.ensure_param("reward_led_color", [0, 255, 0])
        self.config.ensure_param("punishment_led_color", [255, 0, 0])

        self.pi = pigpio.pi() if pigpio is not None else None

        logger.info("Using single Raspberry Pi display backend.")
        self.display = DisplayManager(
            width=self.config["display_width"],
            height=self.config["display_height"],
            image_folder=self.config["display_image_folder"],
            zone_widths=self.config["display_zone_widths"],
            zone_gaps=self.config["display_zone_gaps"],
            center_layout=self.config["display_center_layout"],
        )

        # Retained names for UI and virtual tooling compatibility.
        self.left_m0 = DisplayZoneDevice(self.display, DisplayZone.LEFT, "DISPLAY_LEFT")
        self.middle_m0 = DisplayZoneDevice(self.display, DisplayZone.MIDDLE, "DISPLAY_MIDDLE")
        self.right_m0 = DisplayZoneDevice(self.display, DisplayZone.RIGHT, "DISPLAY_RIGHT")
        self.display_devices = {
            "left": self.left_m0,
            "middle": self.middle_m0,
            "right": self.right_m0,
        }
        self.m0s = [self.left_m0, self.middle_m0, self.right_m0]

        self.reward_led = LED(
            pi=self.pi,
            rgb_pins=self.config["reward_LED_pins"],
            brightness=self.config["reward_led_brightness"],
            color=self.config["reward_led_color"],
        )
        self.punishment_led = LED(
            pi=self.pi,
            rgb_pins=self.config["punishment_LED_pins"],
            brightness=self.config["punishment_led_brightness"],
            color=self.config["punishment_led_color"],
        )
        self.house_led = LED(
            pi=self.pi,
            pin=self.config["house_LED_pin"],
            brightness=self.config["house_led_brightness"],
        )
        self.beambreak = BeamBreak(
            pi=self.pi,
            pin=self.config["beambreak_pin"],
            beam_break_memory=self.config["beambreak_memory"],
        )
        self.buzzer = Buzzer(
            pi=self.pi,
            pin=self.config["buzzer_pin"],
            volume=self.config["buzzer_volume"],
            frequency=self.config["buzzer_frequency"],
        )
        self.reward = Reward(pi=self.pi, pin=self.config["reward_pump_pin"])
        self.camera = Camera(device=self.config["camera_device"])

    # ---- Display-zone API ----

    def _normalize_zone(self, zone):
        if zone is None:
            return "all"
        zone_name = str(zone).strip().lower()
        if zone_name in {"left", "middle", "right", "all"}:
            return zone_name
        raise ValueError(f"Unknown display zone '{zone}'")

    def get_display_device(self, zone):
        zone_name = self._normalize_zone(zone)
        if zone_name == "all":
            return None
        return self.display_devices[zone_name]

    def display_command(self, zone, command):
        zone_name = self._normalize_zone(zone)
        if zone_name == "all":
            for device in self.display_devices.values():
                device.send_command(command)
            return
        self.display_devices[zone_name].send_command(command)

    def display_load_image(self, zone, image_name):
        self.display_command(zone, f"IMG:{image_name}")

    def display_show(self, zone):
        self.display_command(zone, "SHOW")

    def display_clear(self, zone="all"):
        zone_name = self._normalize_zone(zone)
        if zone_name == "all":
            self.display.clear(DisplayZone.ALL)
            return
        self.display.clear(zone_name)

    def display_was_touched(self, zone):
        zone_name = self._normalize_zone(zone)
        if zone_name == "all":
            return any(device.was_touched() for device in self.display_devices.values())
        return self.display_devices[zone_name].was_touched()

    def configure_display_zones(self, zone_widths=None, zone_gaps=None, center_layout=None):
        """Allow trainers/tasks to reconfigure active display geometry."""
        if center_layout is None:
            center_layout = self.config["display_center_layout"]

        if zone_widths is not None:
            self.config["display_zone_widths"] = zone_widths
        if zone_gaps is not None:
            self.config["display_zone_gaps"] = zone_gaps
        self.config["display_center_layout"] = center_layout

        self.display.configure_zones(
            zone_widths=self.config["display_zone_widths"],
            zone_gaps=self.config["display_zone_gaps"],
            center_layout=self.config["display_center_layout"],
        )

    # ---- Retained methods used by current UI/tests ----

    def get_left_m0(self):
        return self.left_m0

    def get_middle_m0(self):
        return self.middle_m0

    def get_right_m0(self):
        return self.right_m0

    # Legacy M0 control methods are no-ops in single-display mode.
    def compile_sketch(self, sketch_path=None):
        logger.info("Skipping sketch compile in single-display mode.")

    def arduino_cli_discover(self):
        logger.info("Skipping board discovery in single-display mode.")

    def m0_discover(self):
        logger.info("Skipping M0 discovery in single-display mode.")
        return {
            "DISPLAY_LEFT": self.left_m0.port,
            "DISPLAY_MIDDLE": self.middle_m0.port,
            "DISPLAY_RIGHT": self.right_m0.port,
        }

    def m0_reset(self):
        logger.info("Skipping M0 reset in single-display mode.")

    def m0_initialize(self):
        logger.info("Skipping M0 initialize in single-display mode.")

    def m0_reopen_serial(self):
        logger.info("Skipping serial reopen in single-display mode.")

    def m0_close_serial(self):
        logger.info("Skipping serial close in single-display mode.")

    def m0_open_serial(self):
        logger.info("Skipping serial open in single-display mode.")

    def m0_sync_images(self):
        logger.info("Skipping image sync in single-display mode.")

    def m0_upload_sketches(self):
        logger.info("Skipping sketch upload in single-display mode.")

    def m0_send_command(self, command):
        self.display_command("all", command)

    def m0_clear(self):
        self.display_clear("all")

    def m0_show_image(self):
        self.display_show("all")

    def default_state(self):
        """Set the default state for the chamber."""
        self.display_clear("all")
        self.reward_led.deactivate()
        self.punishment_led.deactivate()
        self.buzzer.deactivate()
        self.reward.stop()

    def __del__(self):
        logger.info("Cleaning up chamber...")
        if self.pi is not None:
            self.pi.stop()


if __name__ == "__main__":
    logger.info("Chamber initialized.")
