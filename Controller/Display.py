# Display.py
"""Single physical display backend with legacy-compatible zone adapters."""

import os
import re
import subprocess
import threading
from collections import deque
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
        display_name=None,
        display_index=None,
        window_mode="fullscreen",
        image_border_color=(255, 255, 255),
        image_border_width=1,
    ):
        logger.info("Initializing Display Manager...")
        self.width = width
        self.height = height
        self.display_name = display_name
        self.window_mode = (window_mode or "fullscreen").strip().lower()
        self.display_index = self._resolve_display_index(display_name, display_index)
        self.display_geometry = self._resolve_display_geometry(self.display_index, display_name)

        self._configure_sdl_display_env()

        self.code_dir = os.path.dirname(os.path.abspath(__file__))
        self.image_folder = os.path.abspath(os.path.join(self.code_dir, image_folder))
        self.image_border_color = tuple(int(v) for v in image_border_color)
        self.image_border_width = max(0, int(image_border_width))

        pygame.init()
        pygame.mouse.set_visible(False)

        flags = pygame.NOFRAME
        if self.window_mode == "fullscreen":
            flags |= pygame.FULLSCREEN
        elif self.window_mode != "borderless_pinned":
            logger.warning(
                "Unknown window_mode '%s'; defaulting to fullscreen",
                self.window_mode,
            )
            self.window_mode = "fullscreen"
            flags |= pygame.FULLSCREEN

        self.screen = pygame.display.set_mode((self.width, self.height), flags, display=self.display_index)
        self.screen.fill((0, 0, 0))
        pygame.display.flip()

        self._owner_thread_id = threading.get_ident()
        self._pending_ops = deque()
        self._ops_lock = threading.Lock()

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
        self._touch_lock = threading.Lock()
        self.image_cache = {}

    def _is_owner_thread(self):
        return threading.get_ident() == self._owner_thread_id

    def _enqueue_op(self, op_name, *args):
        with self._ops_lock:
            self._pending_ops.append((op_name, args))

    def _dequeue_ops(self):
        with self._ops_lock:
            ops = list(self._pending_ops)
            self._pending_ops.clear()
        return ops

    def _configure_sdl_display_env(self):
        if self.display_index is not None:
            os.environ["SDL_VIDEO_FULLSCREEN_DISPLAY"] = str(self.display_index)

        if self.window_mode == "borderless_pinned" and self.display_geometry is not None:
            x = int(self.display_geometry["x"])
            y = int(self.display_geometry["y"])
            os.environ["SDL_VIDEO_WINDOW_POS"] = f"{x},{y}"
            os.environ["SDL_VIDEO_CENTERED"] = "0"
            logger.info(
                "Using borderless pinned window at (%s, %s) on display index %s",
                x,
                y,
                self.display_index,
            )
        elif self.window_mode == "borderless_pinned":
            logger.warning(
                "borderless_pinned mode requested but display geometry was not detected; window may open on wrong output"
            )

    def _resolve_display_index(self, display_name, display_index):
        if display_index is not None:
            try:
                selected_index = int(display_index)
                logger.info("Using configured display index: %s", selected_index)
                return selected_index
            except (TypeError, ValueError):
                logger.warning("Invalid display_index '%s'; falling back to auto-detect", display_index)

        if display_name:
            detected = self._detect_display_index_by_name(display_name)
            if detected is not None:
                # Verify the detected display has the correct resolution
                if self._verify_display_resolution(detected):
                    logger.info("Detected display '%s' at index %s with correct resolution", display_name, detected)
                    return detected
                logger.warning(
                    "Detected display '%s' at index %s but it has incorrect resolution; "
                    "searching for correct resolution display",
                    display_name,
                    detected,
                )
            logger.warning("Display '%s' not found or has incorrect resolution", display_name)

        # Try to find a display with the correct 480x1920 or 1920x480 resolution
        correct_index = self._detect_display_by_correct_resolution()
        if correct_index is not None:
            logger.info("Found display with correct resolution at index %s", correct_index)
            return correct_index

        logger.warning(
            "Could not find display with resolution %sx%s or %sx%s; "
            "falling back to default display index 0",
            self.width,
            self.height,
            self.height,
            self.width,
        )
        return 0

    def _detect_display_index_by_name(self, target_name):
        target = str(target_name).strip().lower()
        if not target:
            return None

        index = self._detect_with_xrandr(target)
        if index is not None:
            return index

        index = self._detect_with_wlr_randr(target)
        if index is not None:
            return index

        return None

    def _detect_with_xrandr(self, target):
        try:
            result = subprocess.run(
                ["xrandr", "--listmonitors"],
                check=False,
                capture_output=True,
                text=True,
                timeout=1.5,
            )
        except Exception:
            return None

        if result.returncode != 0:
            return None

        for line in result.stdout.splitlines():
            match = re.match(r"\s*(\d+):.*\s([A-Za-z0-9_.-]+)\s*$", line)
            if not match:
                continue
            idx = int(match.group(1))
            output_name = match.group(2).lower()
            if output_name == target:
                return idx
        return None

    def _detect_with_wlr_randr(self, target):
        try:
            result = subprocess.run(
                ["wlr-randr"],
                check=False,
                capture_output=True,
                text=True,
                timeout=1.5,
            )
        except Exception:
            return None

        if result.returncode != 0:
            return None

        idx = 0
        for line in result.stdout.splitlines():
            if not line.startswith(" ") and line.strip():
                output_name = line.split()[0].strip().lower()
                if output_name == target:
                    return idx
                idx += 1
        return None

    def _verify_display_resolution(self, display_index):
        """Check if a display has the correct resolution.
        
        Handles both physical and transformed (rotated) resolutions:
        - 1920x480 can be a 480x1920 display rotated 270 degrees
        - 480x1920 can be a 1920x480 display rotated 90/270 degrees
        
        Prefers wlr-randr (physical dimensions) over xrandr (may be transformed).
        """
        # Try wlr-randr first (shows physical dimensions before any transform)
        if self.display_name:
            target = str(self.display_name).strip().lower()
            geometry = self._geometry_from_wlr_randr(target)
            if geometry is not None:
                w = geometry["width"]
                h = geometry["height"]
                if (w == self.width and h == self.height) or (w == self.height and h == self.width):
                    logger.info("Display '%s' matches (physical: %sx%s)", target, w, h)
                    return True
                logger.warning(
                    "Display '%s' physical resolution %sx%s doesn't match request %sx%s or %sx%s",
                    target,
                    w,
                    h,
                    self.width,
                    self.height,
                    self.height,
                    self.width,
                )
                return False

        # Fall back to xrandr (may show rotated dimensions)
        geometry = self._geometry_from_xrandr_listmonitors(display_index)
        if geometry is not None:
            w = geometry["width"]
            h = geometry["height"]
            if (w == self.width and h == self.height) or (w == self.height and h == self.width):
                logger.info("Display index %s matches (xrandr: %sx%s)", display_index, w, h)
                return True
            logger.warning(
                "Display index %s resolution %sx%s doesn't match request %sx%s or %sx%s",
                display_index,
                w,
                h,
                self.width,
                self.height,
                self.height,
                self.width,
            )
            return False
        return None  # Could not determine resolution

    def _detect_display_by_correct_resolution(self):
        """Find a display with the correct 480x1920 or 1920x480 resolution."""
        # Try xrandr first (more reliable for resolution checking)
        index = self._find_correct_resolution_with_xrandr()
        if index is not None:
            return index

        # Fall back to wlr-randr
        index = self._find_correct_resolution_with_wlr_randr()
        if index is not None:
            return index

        return None

    def _find_correct_resolution_with_xrandr(self):
        """Use xrandr to find a display with the correct resolution."""
        try:
            result = subprocess.run(
                ["xrandr", "--listmonitors"],
                check=False,
                capture_output=True,
                text=True,
                timeout=1.5,
            )
        except Exception:
            return None

        if result.returncode != 0:
            return None

        pattern = re.compile(
            r"\s*(\d+):.*?(\d+)/\d+x(\d+)/\d+\+(-?\d+)\+(-?\d+)\s+([A-Za-z0-9_.-]+)\s*$"
        )
        for line in result.stdout.splitlines():
            match = pattern.match(line)
            if not match:
                continue
            idx = int(match.group(1))
            width = int(match.group(2))
            height = int(match.group(3))
            if (width == self.width and height == self.height) or (
                width == self.height and height == self.width
            ):
                logger.info("Found display index %s with correct resolution: %sx%s", idx, width, height)
                return idx
        return None

    def _find_correct_resolution_with_wlr_randr(self):
        """Use wlr-randr to find a display with the correct physical resolution.
        
        wlr-randr shows physical (not rotated) dimensions, making it more reliable
        for finding displays with specific physical resolutions.
        """
        try:
            result = subprocess.run(
                ["wlr-randr"],
                check=False,
                capture_output=True,
                text=True,
                timeout=1.5,
            )
        except Exception:
            return None

        if result.returncode != 0:
            return None

        idx = 0
        current_name = None
        found_correct = False

        for raw_line in result.stdout.splitlines():
            line = raw_line.rstrip("\n")

            if line and not line.startswith(" "):
                if found_correct and current_name is not None:
                    logger.info("Found display at index %s with correct physical resolution", idx - 1)
                    return idx - 1
                current_name = line.split()[0].strip().lower()
                found_correct = False
                continue

            stripped = line.strip()
            
            # Look for the current mode (in Modes section)
            if "(current" in stripped and "x" in stripped:
                mode_token = stripped.split()[0]
                if "x" in mode_token:
                    try:
                        w_str, h_str = mode_token.split("x", 1)
                        w = int(w_str)
                        h = int(h_str)
                        if (w == self.width and h == self.height) or (
                            w == self.height and h == self.width
                        ):
                            logger.info(
                                "Display at index %s has matching physical resolution: %sx%s",
                                idx,
                                w,
                                h,
                            )
                            found_correct = True
                    except ValueError:
                        pass

        # Check the last display
        if found_correct:
            logger.info("Found display at index %s with correct physical resolution", idx)
            return idx

        return None

    def _resolve_display_geometry(self, display_index, display_name):
        geometry = self._geometry_from_xrandr_listmonitors(display_index)
        if geometry is not None:
            logger.info(
                "Resolved display geometry from xrandr list: %sx%s+%s+%s",
                geometry["width"],
                geometry["height"],
                geometry["x"],
                geometry["y"],
            )
            return geometry

        if display_name:
            geometry = self._geometry_from_wlr_randr(display_name)
            if geometry is not None:
                logger.info(
                    "Resolved display geometry for '%s' from wlr-randr: %sx%s+%s+%s",
                    display_name,
                    geometry["width"],
                    geometry["height"],
                    geometry["x"],
                    geometry["y"],
                )
                return geometry

        return None

    def _geometry_from_xrandr_listmonitors(self, display_index):
        if display_index is None:
            return None

        try:
            result = subprocess.run(
                ["xrandr", "--listmonitors"],
                check=False,
                capture_output=True,
                text=True,
                timeout=1.5,
            )
        except Exception:
            return None

        if result.returncode != 0:
            return None

        pattern = re.compile(
            r"\s*(\d+):.*?(\d+)/\d+x(\d+)/\d+\+(-?\d+)\+(-?\d+)\s+([A-Za-z0-9_.-]+)\s*$"
        )
        for line in result.stdout.splitlines():
            match = pattern.match(line)
            if not match:
                continue
            idx = int(match.group(1))
            if idx != int(display_index):
                continue
            width = int(match.group(2))
            height = int(match.group(3))
            x = int(match.group(4))
            y = int(match.group(5))
            return {"x": x, "y": y, "width": width, "height": height}
        return None

    def _geometry_from_wlr_randr(self, display_name):
        target = str(display_name).strip().lower()
        if not target:
            return None

        try:
            result = subprocess.run(
                ["wlr-randr"],
                check=False,
                capture_output=True,
                text=True,
                timeout=1.5,
            )
        except Exception:
            return None

        if result.returncode != 0:
            return None

        current_name = None
        position = None
        mode = None
        transform = "normal"
        in_modes = False

        for raw_line in result.stdout.splitlines():
            line = raw_line.rstrip("\n")
            if line and not line.startswith(" "):
                if current_name == target and position is not None and mode is not None:
                    return self._wlr_geometry(position, mode, transform)

                current_name = line.split()[0].strip().lower()
                position = None
                mode = None
                transform = "normal"
                in_modes = False
                continue

            stripped = line.strip()
            if stripped == "Modes:":
                in_modes = True
                continue

            if stripped.startswith("Position:"):
                in_modes = False
                pos = stripped.split(":", 1)[1].strip()
                if "," in pos:
                    x_str, y_str = pos.split(",", 1)
                    position = (int(x_str), int(y_str))
                continue

            if stripped.startswith("Transform:"):
                transform = stripped.split(":", 1)[1].strip().lower()
                continue

            if in_modes and "(current" in stripped:
                mode_token = stripped.split()[0]
                if "x" in mode_token:
                    w_str, h_str = mode_token.split("x", 1)
                    mode = (int(w_str), int(h_str))

        if current_name == target and position is not None and mode is not None:
            return self._wlr_geometry(position, mode, transform)

        return None

    def _wlr_geometry(self, position, mode, transform):
        x, y = position
        width, height = mode
        if transform in {"90", "270", "flipped-90", "flipped-270"}:
            width, height = height, width
        return {"x": x, "y": y, "width": width, "height": height}

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

    def _show_image_now(self, zone, image_name):
        zone_rect = self.zones[zone]
        img = self._load_image(image_name, target_size=(zone_rect.width, zone_rect.height))
        if img is not None:
            self.screen.blit(img, zone_rect.topleft)
            if self.image_border_width > 0:
                pygame.draw.rect(self.screen, self.image_border_color, zone_rect, self.image_border_width)
            pygame.display.update(zone_rect)
            logger.debug(f"Displayed {image_name} in {zone} zone")

    def show_image(self, zone, image_name):
        if not self._is_owner_thread():
            self._enqueue_op("show", zone, image_name)
            return
        self._show_image_now(zone, image_name)

    def _clear_now(self, zone=DisplayZone.ALL):
        if zone == DisplayZone.ALL:
            self.screen.fill((0, 0, 0))
            pygame.display.flip()
            return

        if zone in self.zones:
            pygame.draw.rect(self.screen, (0, 0, 0), self.zones[zone])
            pygame.display.update(self.zones[zone])

    def clear(self, zone=DisplayZone.ALL):
        if not self._is_owner_thread():
            self._enqueue_op("clear", zone)
            return
        self._clear_now(zone)

    def process_events(self):
        if not self._is_owner_thread():
            return

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
                    with self._touch_lock:
                        self.touch_states[zone] = True
                    logger.debug(f"Touch in {zone} zone at {pos}")

    def was_touched(self, zone):
        with self._touch_lock:
            touched = self.touch_states.get(zone, False)
            if touched:
                self.touch_states[zone] = False
        return touched

    def flush_pending_operations(self):
        """Run queued draw operations on the display owner thread."""
        if not self._is_owner_thread():
            return

        self.process_events()
        for op_name, args in self._dequeue_ops():
            if op_name == "show":
                self._show_image_now(*args)
            elif op_name == "clear":
                self._clear_now(*args)

    def clear_touch_states(self, drain_events=True):
        """Clear latched touch flags, optionally draining pending pygame touch events."""
        if drain_events and self._is_owner_thread():
            # Drain queued touch/mouse down events so prior touches do not trigger a new trial.
            for event in pygame.event.get():
                if event.type in (pygame.MOUSEBUTTONDOWN, pygame.FINGERDOWN):
                    continue
                pygame.event.post(event)

        with self._touch_lock:
            for zone in self.touch_states:
                self.touch_states[zone] = False


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

    def clear_touches(self, drain_events=True):
        self.display.clear_touch_states(drain_events=drain_events)

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