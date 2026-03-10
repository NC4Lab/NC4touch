# Chamber class for the Touchscreen chamber
#
# Manu Madhav
# 2025

try:
    import pigpio
except ImportError:
    pigpio = None
try:
    import serial
    import serial.tools.list_ports
except ImportError:
    serial = None
import time
import subprocess
import json
import os

from LED import LED
from Reward import Reward
from BeamBreak import BeamBreak
from Buzzer import Buzzer
from M0Device import M0Device, M0Mode
from Display import DisplayManager, DisplayZone, DisplayZoneDevice
from Camera import Camera
from Config import Config

import logging
logger = logging.getLogger(f"session_logger.{__name__}")

class Chamber:
  """Chamber class for NC4Touch"""
  def __init__(self, chamber_config = {}, chamber_config_file = '~/chamber_config.yaml'):
    logger.info("Initializing Chamber...")
    self.config = Config(config = chamber_config, config_file = chamber_config_file)
    self.config.ensure_param("chamber_name", "Chamber0")
    self.config.ensure_param("reward_LED_pins", [13, 21, 26]) # RGB LED pins for reward
    self.config.ensure_param("reward_pump_pin", 27)
    self.config.ensure_param("beambreak_pin", 4)
    self.config.ensure_param("punishment_LED_pins", [18, 19, 17]) # RGB LED pins for punishment
    self.config.ensure_param("house_LED_pin", 20)
    self.config.ensure_param("buzzer_pin", 16)
    self.config.ensure_param("reset_pins", [25, 5, 6])
    self.config.ensure_param("camera_device", "/dev/video0")
    self.config.ensure_param("reward_led_brightness", 140)
    self.config.ensure_param("punishment_led_brightness", 255)
    self.config.ensure_param("house_led_brightness", 100)
    self.config.ensure_param("buzzer_volume", 60)
    self.config.ensure_param("buzzer_frequency", 6000)
    self.config.ensure_param("beambreak_memory", 0.2)
    self.config.ensure_param("display_backend", "single_display")
    self.config.ensure_param("display_width", 1920)
    self.config.ensure_param("display_height", 480)
    self.config.ensure_param("display_image_folder", "../data/images")
    self.config.ensure_param("display_zone_widths", [320, 320, 320])
    self.config.ensure_param("display_zone_gaps", None)
    self.config.ensure_param("display_center_layout", True)
    # LED colors
    self.config.ensure_param("reward_led_color", [0, 255, 0])
    self.config.ensure_param("punishment_led_color", [255, 0, 0])

    self.code_dir = os.path.dirname(os.path.abspath(__file__))

    self.pi = pigpio.pi() if pigpio is not None else None

    backend = str(self.config["display_backend"]).lower().strip()
    self.single_display_mode = backend in {"single_display", "single-display", "pi_display", "pi-single-display"}

    if self.single_display_mode:
      logger.info("Using single Raspberry Pi display backend.")
      self.display = DisplayManager(
        width=self.config["display_width"],
        height=self.config["display_height"],
        image_folder=self.config["display_image_folder"],
        zone_widths=self.config["display_zone_widths"],
        zone_gaps=self.config["display_zone_gaps"],
        center_layout=self.config["display_center_layout"],
      )
      self.left_m0 = DisplayZoneDevice(self.display, DisplayZone.LEFT, "M0_0")
      self.middle_m0 = DisplayZoneDevice(self.display, DisplayZone.MIDDLE, "M0_1")
      self.right_m0 = DisplayZoneDevice(self.display, DisplayZone.RIGHT, "M0_2")
      self.m0s = [self.left_m0, self.middle_m0, self.right_m0]
    else:
      # Initialize physical M0 boards
      self.m0s = [
        M0Device(pi=self.pi, id=f"M0_{i}", reset_pin=self.config["reset_pins"][i])
        for i in range(3)
      ]
      self.arduino_cli_discover()

    self.reward_led = LED(pi=self.pi, rgb_pins=self.config["reward_LED_pins"], brightness=self.config["reward_led_brightness"], color=self.config["reward_led_color"])
    self.punishment_led = LED(pi=self.pi, rgb_pins=self.config["punishment_LED_pins"], brightness=self.config["punishment_led_brightness"], color=self.config["punishment_led_color"])
    self.house_led = LED(pi=self.pi, pin=self.config["house_LED_pin"], brightness=self.config["house_led_brightness"])
    self.beambreak = BeamBreak(pi=self.pi, pin=self.config["beambreak_pin"], beam_break_memory=self.config["beambreak_memory"])
    self.buzzer = Buzzer(pi=self.pi, pin=self.config["buzzer_pin"], volume=self.config["buzzer_volume"], frequency=self.config["buzzer_frequency"])
    self.reward = Reward(pi=self.pi, pin=self.config["reward_pump_pin"])
    self.camera = Camera(device=self.config["camera_device"])
  
  def get_left_m0(self):
    """Returns the left M0 device (M0_0)"""
    if hasattr(self, "left_m0"):
        return self.left_m0
    try:
      idx = [m0.id for m0 in self.m0s].index("M0_0")
      return self.m0s[idx]
    except ValueError:
      logger.error("Left M0 (M0_0) not found in m0s list.")
      return None

  def get_middle_m0(self):
    """Returns the middle M0 device (M0_1)"""
    if hasattr(self, "middle_m0"):
      return self.middle_m0
    try:
      idx = [m0.id for m0 in self.m0s].index("M0_1")
      return self.m0s[idx]
    except ValueError:
      logger.error("Middle M0 (M0_1) not found in m0s list.")
      return None

  def get_right_m0(self):
    """Returns the right M0 device (M0_2)"""
    if hasattr(self, "right_m0"):
      return self.right_m0
    try:
      idx = [m0.id for m0 in self.m0s].index("M0_2")
      return self.m0s[idx]
    except ValueError:
      logger.error("Right M0 (M0_2) not found in m0s list.")
      return None

  def __del__(self):
    """Clean up the chamber by stopping pigpio and M0s."""
    logger.info("Cleaning up chamber...")
    if self.pi is not None:
      self.pi.stop()
    for m0 in getattr(self, "m0s", []):
      if hasattr(m0, "stop"):
        m0.stop()
      else:
        if hasattr(m0, "stop_serial_comm"):
          m0.stop_serial_comm()
        if hasattr(m0, "close_port"):
          m0.close_port()

  def compile_sketch(self, sketch_path=None):
      """
      Compiles the M0Touch sketch using arduino-cli. 
      If sketch_path is None, it defaults to ../M0Touch/M0Touch.ino relative to this file.
      """
      if self.single_display_mode:
          logger.info("Skipping M0 sketch compile in single-display mode.")
          return

      if sketch_path is None:
          sketch_path = os.path.join(self.code_dir, "../M0Touch/M0Touch.ino")

      logger.info(f"Compiling sketch.")

      try:
          # Run arduino-cli compile
          compile = subprocess.check_output(f"~/bin/arduino-cli compile -b DFRobot:samd:mzero_bl {sketch_path}", shell=True).decode("utf-8")
          logger.info(f"Compile output: {compile}")
          
          if "error" in compile.lower():
              logger.error(f"Error compiling sketch: {compile}")
          else:
              logger.info(f"Sketch compiled successfully.")

      except Exception as e:
          logger.error(f"Error compiling sketch: {e}")

  def configure_display_zones(self, zone_widths=None, zone_gaps=None, center_layout=None):
    """Allow trainers to reconfigure active display geometry for tasks.

    Default behavior uses equal auto-gaps for any leftover width.
    Pass explicit zone_gaps=[edge_l, l_m, m_r, edge_r] to override.
    """
    if not self.single_display_mode:
      logger.warning("configure_display_zones is only available in single-display mode.")
      return

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
  
  def arduino_cli_discover(self):
    """
    Uses arduino-cli to discover connected boards.
    Looks for boards with VID: 0x3343 and PID: 0x8244 (DFRobot M0)
    """
    if self.single_display_mode:
      logger.info("Skipping M0 discovery in single-display mode.")
      return

    # Reset all the M0 boards in order before discovery
    self.m0_reset()

    # Poll until all expected boards appear or timeout (boards re-enumerate after reset)
    logger.info("Waiting for M0 boards to re-enumerate after reset...")
    deadline = time.time() + 10
    self.discovered_boards = []
    while time.time() < deadline:
        time.sleep(1)
        self.discovered_boards = []
        try:
            result = subprocess.run([f"~/bin/arduino-cli board list --format json"], capture_output=True, shell=True)
            boards = json.loads(result.stdout)
            for board in boards['detected_ports']:
                props = board['port']['properties']
                if 'pid' in props and 'vid' in props and props['pid'] == '0x8244' and props['vid'] == '0x3343':
                    self.discovered_boards.append(board['port']['address'])
        except Exception as e:
            logger.error(f"Error during board poll: {e}")

        if len(self.discovered_boards) >= len(self.m0s):
            break
        logger.debug(f"Found {len(self.discovered_boards)}/{len(self.m0s)} boards, waiting...")

    logger.info(f"Discovered {len(self.discovered_boards)} M0 board(s): {self.discovered_boards}")

    if not self.discovered_boards:
        logger.error("No M0 boards discovered. Please check the connections.")
        return

    # Open each port and read boot lines until "ID:" appears.
    # Opening the port resets the SAMD21 via DTR, which triggers SD init.
    # We loop through lines until we see the ID broadcast or timeout.
    boot_timeout = 15  # seconds — enough for SD init retries
    for port in self.discovered_boards:
        board_id = None
        try:
            with serial.Serial(port, 115200, timeout=1) as ser:
                logger.debug(f"Opened {port}, waiting for boot ID (up to {boot_timeout}s)...")
                deadline = time.time() + boot_timeout
                while time.time() < deadline:
                    raw = ser.readline()
                    if not raw:
                        continue
                    line = raw.decode("utf-8", errors="ignore").strip()
                    if line:
                        logger.debug(f"  [{port}] {line}")
                    if line.startswith("ID:"):
                        board_id = line.split("ID:")[1].split()[0]  # e.g. "M0_0"
                        break
        except Exception as e:
            logger.error(f"Error reading from {port}: {e}")
            continue

        if board_id is None:
            logger.warning(f"No ID received from {port} within {boot_timeout}s, skipping.")
            continue

        matched = False
        for m0 in self.m0s:
            if m0.id == board_id:
                m0.port = port
                logger.info(f"Matched {board_id} → {port}")
                matched = True
                break
        if not matched:
            logger.warning(f"No M0 object for self-reported ID '{board_id}' on {port}")


  
  def m0_discover(self):
    """
    Searches /dev/ttyACM*, /dev/ttyUSB* for boards that respond with "ID:M0_x"
    when we send "WHOAREYOU?".
    Returns a dict like {"M0_0": "/dev/ttyACM0", "M0_1": "/dev/ttyACM1"}.
    """
    logger.info("Discovering M0 boards...")

    board_map = {}
    ports = serial.tools.list_ports.comports()

    for p in ports:
        # Check if it's an ACM or USB device
        if "ACM" in p.device or "USB" in p.device:
            try:
                with serial.Serial(p.device, 115200, timeout=1) as ser:
                    time.sleep(0.3)
                    ser.write(b"WHOAREYOU?\n")
                    line = ser.readline().decode("utf-8", errors="ignore").strip()
                    if line.startswith("ID:"):
                        board_id = line.split(":", 1)[1]
                        board_map[board_id] = p.device
                        logger.debug(f"Discovered {board_id} on {p.device}")
            except Exception as e:
                logger.error(f"Could not open {p.device}: {e}")
      
    # if len(board_map) == 0:
    #     logger.error("No M0 boards found. Please check the connections.")
    # else:
    #     logger.info(f"Discovered M0 boards: {board_map}")
    #     for m0 in self.m0s:
    #         if m0.id in board_map:
    #             m0.port = board_map[m0.id]
    #             logger.info(f"Set {m0.id} serial port to {board_map[m0.id]}")
    #         else:
    #             logger.error(f"{m0.id} not found in discovered boards. Please check the connections.")

  def m0_send_command(self, command: str):
    """Sends a command to all M0 boards"""
    [m0.send_command(command) for m0 in self.m0s]

  def m0_reset(self):
    """Reset all M0 boards by toggling their reset pins."""
    logger.info("Resetting M0 boards...")
    [m0.reset() for m0 in self.m0s]
  
  def m0_initialize(self):
    """Initialize all M0 boards"""
    for m0 in self.m0s:
      if hasattr(m0, "initialize"):
        m0.initialize()
      elif hasattr(m0, "open_port") and hasattr(m0, "start_serial_comm"):
        m0.open_port()
        m0.start_serial_comm()
  
  def m0_reopen_serial(self):
    """Close and re-open serial connections to all M0 boards"""
    self.m0_close_serial()
    time.sleep(1)  # Wait a moment to ensure ports are released
    self.m0_open_serial()
  
  def m0_close_serial(self):
    """Close serial connections to all M0 boards"""
    for m0 in self.m0s:
      if hasattr(m0, "stop_serial_comm"):
        m0.stop_serial_comm()
      if hasattr(m0, "close_port"):
        m0.close_port()
  
  def m0_open_serial(self):
    """Open serial connections to all M0 boards"""
    for m0 in self.m0s:
      if hasattr(m0, "open_port"):
        m0.open_port()
      if hasattr(m0, "start_serial_comm"):
        m0.start_serial_comm()
  
  def m0_sync_images(self):
    """Sync the image folders for all M0s"""
    for m0 in self.m0s:
      if hasattr(m0, "sync_image_folder"):
        m0.sync_image_folder()

  def m0_upload_sketches(self):
    """Upload sketches to all M0s"""
    if self.single_display_mode:
      logger.info("Skipping M0 sketch upload in single-display mode.")
      return
    self.compile_sketch()
    for m0 in self.m0s:
      if hasattr(m0, "upload_sketch"):
        m0.upload_sketch()
  
  def m0_clear(self):
    """Send the blank command to all M0s"""
    [m0.send_command("OFF") for m0 in self.m0s]
  
  def m0_show_image(self):
    """Send the show image command to all M0s"""
    [m0.send_command("SHOW") for m0 in self.m0s]

  def default_state(self):
    """Set the default state for the chamber"""
    self.m0_send_command("OFF")
    self.reward_led.deactivate()
    self.punishment_led.deactivate()
    self.buzzer.deactivate()
    self.reward.stop()

if __name__ == "__main__":
  # chamber = Chamber()
  # [m0.initialize() for m0 in chamber.m0s]

  # [m0.sync_image_folder() for m0 in chamber.m0s]

  logger.info("Chamber initialized.")