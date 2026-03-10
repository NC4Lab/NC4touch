# Display.py
"""Single physical display backend with legacy-compatible zone adapters."""

import os
from enum import Enum

import pygame

import logging

logger = logging.getLogger(f"session_logger.{__name__}")


class DisplayZone:
    LEFT = "left"
    MIDDLE = "middle"
    RIGHT = "right"
    ALL = "all"


class DisplayMode(Enum):
    """Mode values kept stable so existing UI code can read `mode.name`."""

    UNINITIALIZED = 0
    PORT_OPEN = 1
    SERIAL_COMM = 2
    PORT_CLOSED = 3
    UD = 4


class DisplayManager:
    """Manages one wide display split into left/middle/right operant zones."""

    def __init__(
        self,
        width=1920,
        height=480,
        image_folder="../data/images",
        zone_widths=None,
        zone_gaps=None,
        center_layout=True,
    ):
        logger.info("Initializing Display Manager...")
        self.width = width
        self.height = height

        self.code_dir = os.path.dirname(os.path.abspath(__file__))
        self.image_folder = os.path.abspath(os.path.join(self.code_dir, image_folder))

        pygame.init()
        pygame.mouse.set_visible(False)

        self.screen = pygame.display.set_mode(
            (self.width, self.height), pygame.FULLSCREEN | pygame.NOFRAME
        )
        self.screen.fill((0, 0, 0))
        pygame.display.flip()

        self.zones = {}
        self.configure_zones(
            zone_widths=zone_widths,
            zone_gaps=zone_gaps,
            center_layout=center_layout,
        )

        self.touch_states = {
            DisplayZone.LEFT: False,
            DisplayZone.MIDDLE: False,
            DisplayZone.RIGHT: False,
        }
        self.image_cache = {}

    def __del__(self):
        logger.info("Cleaning up Display Manager...")
        pygame.quit()

    def _candidate_image_paths(self, image_name):
        image_name = image_name.strip()

        if os.path.isabs(image_name):
            yield image_name
        else:
            yield os.path.join(self.image_folder, image_name)

        base, ext = os.path.splitext(image_name)
        if not ext:
            if os.path.isabs(image_name):
                yield f"{image_name}.bmp"
                yield f"{image_name}.png"
            else:
                yield os.path.join(self.image_folder, f"{image_name}.bmp")
                yield os.path.join(self.image_folder, f"{image_name}.png")

    def configure_zones(self, zone_widths=None, zone_gaps=None, center_layout=True):
        """Configure responsive zones and non-responsive black gaps.

        `zone_widths` supports dict/list/tuple, and defaults to [320, 320, 320].
        `zone_gaps` may be:
        - None / "auto": split leftover pixels evenly across 4 gaps,
        - [left_edge, left-middle, middle-right, right_edge] for explicit control.
        """

        if zone_widths is None:
            width_map = {
                DisplayZone.LEFT: 320,
                DisplayZone.MIDDLE: 320,
                DisplayZone.RIGHT: 320,
            }
        elif isinstance(zone_widths, dict):
            width_map = {
                DisplayZone.LEFT: int(zone_widths.get(DisplayZone.LEFT, zone_widths.get("left", 0))),
                DisplayZone.MIDDLE: int(zone_widths.get(DisplayZone.MIDDLE, zone_widths.get("middle", 0))),
                DisplayZone.RIGHT: int(zone_widths.get(DisplayZone.RIGHT, zone_widths.get("right", 0))),
            }
        else:
            zone_widths = list(zone_widths)
            if len(zone_widths) != 3:
                raise ValueError("zone_widths must contain 3 values: [left, middle, right]")
            width_map = {
                DisplayZone.LEFT: int(zone_widths[0]),
                DisplayZone.MIDDLE: int(zone_widths[1]),
                DisplayZone.RIGHT: int(zone_widths[2]),
            }

        zone_total_width = (
            width_map[DisplayZone.LEFT]
            + width_map[DisplayZone.MIDDLE]
            + width_map[DisplayZone.RIGHT]
        )

        if zone_total_width > self.width:
            raise ValueError(
                f"Total zone width {zone_total_width} exceeds screen width {self.width}"
            )

        if zone_gaps is None or zone_gaps == "auto":
            leftover = self.width - zone_total_width
            gap_base = leftover // 4
            gap_remainder = leftover % 4
            gaps = [
                gap_base + (1 if idx < gap_remainder else 0)
                for idx in range(4)
            ]
        else:
            gaps = [int(v) for v in zone_gaps]
            if len(gaps) != 4:
                raise ValueError("zone_gaps must contain 4 values: [edge_l, l_m, m_r, edge_r]")

        total_layout_width = (
            gaps[0]
            + width_map[DisplayZone.LEFT]
            + gaps[1]
            + width_map[DisplayZone.MIDDLE]
            + gaps[2]
            + width_map[DisplayZone.RIGHT]
            + gaps[3]
        )

        if total_layout_width > self.width:
            raise ValueError(
                f"Display layout width {total_layout_width} exceeds screen width {self.width}"
            )

        offset = (self.width - total_layout_width) // 2 if center_layout else 0
        x = offset + gaps[0]

        self.zones = {
            DisplayZone.LEFT: pygame.Rect(x, 0, width_map[DisplayZone.LEFT], self.height),
            DisplayZone.MIDDLE: pygame.Rect(
                x + width_map[DisplayZone.LEFT] + gaps[1],
                0,
                width_map[DisplayZone.MIDDLE],
                self.height,
            ),
            DisplayZone.RIGHT: pygame.Rect(
                x
                + width_map[DisplayZone.LEFT]
                + gaps[1]
                + width_map[DisplayZone.MIDDLE]
                + gaps[2],
                0,
                width_map[DisplayZone.RIGHT],
                self.height,
            ),
        }

        self.zone_gaps = gaps
        self.zone_widths = width_map
        self.center_layout = center_layout

        self.clear(DisplayZone.ALL)
        logger.info(
            "Configured display zones: left=%s middle=%s right=%s gaps=%s offset=%s",
            self.zones[DisplayZone.LEFT],
            self.zones[DisplayZone.MIDDLE],
            self.zones[DisplayZone.RIGHT],
            gaps,
            offset,
        )

    def _load_image(self, image_name, target_size):
        """Load and scale an image for one display zone, with in-memory caching."""
        image_key = (image_name.strip(), int(target_size[0]), int(target_size[1]))
        if image_key in self.image_cache:
            return self.image_cache[image_key]

        image_path = None
        for candidate in self._candidate_image_paths(image_name.strip()):
            if os.path.exists(candidate):
                image_path = candidate
                break

        if image_path is None:
            logger.error(f"Image not found: {image_key} (searched in {self.image_folder})")
            return None

        try:
            img = pygame.image.load(image_path).convert()
            img = pygame.transform.scale(img, (int(target_size[0]), int(target_size[1])))
            self.image_cache[image_key] = img
            return img
        except Exception as exc:
            logger.error(f"Error loading image {image_key}: {exc}")
            return None

    def show_image(self, zone, image_name):
        zone_rect = self.zones[zone]
        img = self._load_image(image_name, target_size=(zone_rect.width, zone_rect.height))
        if img is not None:
            self.screen.blit(img, zone_rect.topleft)
            pygame.display.update(zone_rect)
            logger.debug(f"Displayed {image_name} in {zone} zone")

    def clear(self, zone=DisplayZone.ALL):
        if zone == DisplayZone.ALL:
            self.screen.fill((0, 0, 0))
            pygame.display.flip()
            return

        if zone in self.zones:
            pygame.draw.rect(self.screen, (0, 0, 0), self.zones[zone])
            pygame.display.update(self.zones[zone])

    def process_events(self):
        for event in pygame.event.get():
            pos = None
            if event.type == pygame.MOUSEBUTTONDOWN:
                pos = event.pos
            elif event.type == pygame.FINGERDOWN:
                pos = (int(event.x * self.width), int(event.y * self.height))

            if pos is None:
                continue

            for zone, rect in self.zones.items():
                if rect.collidepoint(pos):
                    self.touch_states[zone] = True
                    logger.debug(f"Touch in {zone} zone at {pos}")

    def was_touched(self, zone):
        touched = self.touch_states.get(zone, False)
        if touched:
            self.touch_states[zone] = False
        return touched


class DisplayZoneDevice:
    """Legacy-compatible command API for one logical zone on the single display."""

    def __init__(self, display_manager, zone, device_id):
        self.display = display_manager
        self.zone = zone
        self.id = device_id

        self.port = f"PI_DISPLAY_{zone.upper()}"
        self.baudrate = 0
        self.firmware_version = "pi-display"
        self.mode = DisplayMode.SERIAL_COMM
        self.reset_pin = None

        self._loaded_image = None

    def send_command(self, command):
        if command is None:
            return

        cmd = command.strip()
        if not cmd:
            return

        logger.debug(f"[{self.id}] display command: {cmd}")

        if cmd == "WHOAREYOU?":
            logger.info(f"[{self.id}] ID:{self.id}")
            return

        if cmd == "VERSION?":
            logger.info(f"[{self.id}] VERSION:{self.firmware_version}")
            return

        if cmd.startswith("IMG:"):
            self._loaded_image = cmd.split(":", 1)[1]
            return

        if cmd == "SHOW":
            if self._loaded_image:
                self.display.show_image(self.zone, self._loaded_image)
            return

        if cmd in {"BLACK", "OFF", "CLEAR"}:
            self.display.clear(self.zone)
            return

        if cmd.startswith("DISPLAY:"):
            self.display.show_image(self.zone, cmd.split(":", 1)[1])
            return

        if cmd == "SCREENSHARE":
            logger.info(f"[{self.id}] SCREENSHARE ignored for pi display backend")
            return

        logger.warning(f"[{self.id}] Unknown display command: {cmd}")

    def was_touched(self):
        self.display.process_events()
        return self.display.was_touched(self.zone)

    def is_touched(self):
        self.display.process_events()
        return self.display.touch_states.get(self.zone, False)

    # No-op lifecycle methods to keep Chamber/WebUI compatibility.
    def reset(self):
        self.display.clear(self.zone)

    def open_port(self):
        self.mode = DisplayMode.PORT_OPEN

    def close_port(self):
        self.mode = DisplayMode.PORT_CLOSED

    def start_serial_comm(self):
        self.mode = DisplayMode.SERIAL_COMM

    def stop_serial_comm(self):
        self.mode = DisplayMode.PORT_OPEN

    def sync_image_folder(self):
        logger.info(f"[{self.id}] sync_image_folder not required for pi display backend")

    def upload_sketch(self):
        logger.info(f"[{self.id}] upload_sketch not required for pi display backend")

    def stop(self):
        self.mode = DisplayMode.UNINITIALIZED