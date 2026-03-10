"""
Virtual Chamber GUI - Interactive interface for simulating chamber hardware.

Provides a visual interface to:
- View and interact with a single virtual display split into 3 logical zones
- Simulate beam breaks
- Monitor LED states, buzzer activity, and reward dispensing
- Control all virtual hardware components for testing
"""

import tkinter as tk
from tkinter import ttk
import threading
import time
import os

try:
    from PIL import Image, ImageTk
    HAS_PIL = True
except ImportError:
    Image = None
    ImageTk = None
    HAS_PIL = False

import logging
logger = logging.getLogger(f"session_logger.{__name__}")


class VirtualChamberGUI:
    """Interactive GUI for controlling and monitoring a virtual chamber."""

    def __init__(self, virtual_chamber, update_interval=100):
        self.chamber = virtual_chamber
        self.update_interval = update_interval

        self.root = tk.Tk()
        self.root.title(f"Virtual Chamber - {self.chamber.config['chamber_name']}")
        self.root.geometry("1400x850")

        self._running = False
        self._image_cache = {}
        self._canvas_images = {"left": None, "middle": None, "right": None}
        self._zone_touch_until = {"left": 0.0, "middle": 0.0, "right": 0.0}

        self.layout = self.chamber.get_display_layout() if hasattr(self.chamber, "get_display_layout") else {
            "display_width": 1920,
            "display_height": 480,
            "zones": {
                "left": {"x": 240, "y": 0, "w": 320, "h": 480},
                "middle": {"x": 800, "y": 0, "w": 320, "h": 480},
                "right": {"x": 1360, "y": 0, "w": 320, "h": 480},
            },
        }

        self._create_ui()
        self._start_update_loop()

        logger.info("Virtual Chamber GUI initialized")

    def _create_ui(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky="nsew")

        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.columnconfigure(2, weight=1)

        title_label = ttk.Label(
            main_frame,
            text="Virtual Touchscreen Chamber",
            font=("Arial", 16, "bold"),
        )
        title_label.grid(row=0, column=0, columnspan=3, pady=10)

        self._create_touchscreen_section(main_frame)
        self._create_peripherals_section(main_frame)
        self._create_status_section(main_frame)

    def _create_touchscreen_section(self, parent):
        ts_frame = ttk.LabelFrame(parent, text="Single Display (3 Zones)", padding="10")
        ts_frame.grid(row=1, column=0, columnspan=3, sticky="ew", pady=10)

        display_w = int(self.layout["display_width"])
        display_h = int(self.layout["display_height"])
        max_canvas_w = 1150
        max_canvas_h = 320
        self.canvas_scale = min(max_canvas_w / display_w, max_canvas_h / display_h)
        self.canvas_scale = max(0.2, min(self.canvas_scale, 1.0))
        self.virtual_canvas_w = int(display_w * self.canvas_scale)
        self.virtual_canvas_h = int(display_h * self.canvas_scale)

        gaps = self.layout.get("gaps", [0, 0, 0, 0])
        widths = self.layout.get("zone_widths", [0, 0, 0])
        self.layout_label = ttk.Label(
            ts_frame,
            text=(
                f"Layout px: {gaps[0]}-L({widths[0]})-{gaps[1]}-M({widths[1]})-"
                f"{gaps[2]}-R({widths[2]})-{gaps[3]}"
            ),
            font=("Arial", 9),
        )
        self.layout_label.grid(row=0, column=0, columnspan=3, pady=(0, 4))

        self.virtual_canvas = tk.Canvas(
            ts_frame,
            width=self.virtual_canvas_w,
            height=self.virtual_canvas_h,
            bg="black",
            highlightthickness=2,
            highlightbackground="gray",
        )
        self.virtual_canvas.grid(row=1, column=0, columnspan=3, pady=5)
        self.virtual_canvas.bind("<Button-1>", self._handle_virtual_canvas_click)

        self.zone_status_labels = {}
        for idx, (zone_name, m0_id) in enumerate([
            ("left", self.chamber.left_m0.id),
            ("middle", self.chamber.middle_m0.id),
            ("right", self.chamber.right_m0.id),
        ]):
            zone_frame = ttk.Frame(ts_frame)
            zone_frame.grid(row=2, column=idx, padx=8, sticky="ew")
            ttk.Label(
                zone_frame,
                text=f"{zone_name.capitalize()} Zone ({m0_id})",
                font=("Arial", 9, "bold"),
            ).pack()
            status_label = ttk.Label(zone_frame, text="No image", foreground="gray")
            status_label.pack()
            self.zone_status_labels[zone_name] = status_label

            ttk.Button(
                zone_frame,
                text="Simulate Touch",
                command=lambda z=zone_name: self._simulate_zone_touch(z),
            ).pack(pady=4)

    def _create_peripherals_section(self, parent):
        bb_frame = ttk.LabelFrame(parent, text="Beam Break Sensor", padding="10")
        bb_frame.grid(row=2, column=0, sticky="nsew", pady=5, padx=5)

        self.bb_status_label = ttk.Label(bb_frame, text="Not Broken", foreground="green")
        self.bb_status_label.pack()

        ttk.Button(bb_frame, text="Break Beam", command=self._break_beam).pack(pady=5)
        ttk.Button(bb_frame, text="Restore Beam", command=self._restore_beam).pack()

        led_frame = ttk.LabelFrame(parent, text="LEDs", padding="10")
        led_frame.grid(row=2, column=1, sticky="nsew", pady=5, padx=5)

        ttk.Label(led_frame, text="Reward LED:").pack()
        self.reward_led_label = ttk.Label(led_frame, text="OFF", foreground="gray")
        self.reward_led_label.pack()

        ttk.Label(led_frame, text="Punishment LED:").pack(pady=(10, 0))
        self.punishment_led_label = ttk.Label(led_frame, text="OFF", foreground="gray")
        self.punishment_led_label.pack()

        misc_frame = ttk.LabelFrame(parent, text="Buzzer and Reward", padding="10")
        misc_frame.grid(row=2, column=2, sticky="nsew", pady=5, padx=5)

        ttk.Label(misc_frame, text="Buzzer:").pack()
        self.buzzer_label = ttk.Label(misc_frame, text="Silent", foreground="gray")
        self.buzzer_label.pack()

        ttk.Label(misc_frame, text="Reward Pump:").pack(pady=(10, 0))
        self.reward_label = ttk.Label(misc_frame, text="Stopped", foreground="gray")
        self.reward_label.pack()

        self.reward_count_label = ttk.Label(misc_frame, text="Dispensed: 0")
        self.reward_count_label.pack(pady=5)

    def _create_status_section(self, parent):
        status_frame = ttk.LabelFrame(parent, text="Status Log", padding="10")
        status_frame.grid(row=3, column=0, columnspan=3, sticky="nsew", pady=10)

        self.log_text = tk.Text(status_frame, height=10, width=100, state="disabled")
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(status_frame, command=self.log_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.config(yscrollcommand=scrollbar.set)

        btn_frame = ttk.Frame(parent)
        btn_frame.grid(row=4, column=0, columnspan=3, pady=10)

        ttk.Button(btn_frame, text="Clear Log", command=self._clear_log).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Get Chamber State", command=self._print_state).pack(side=tk.LEFT, padx=5)

    def _zone_from_real_x(self, real_x):
        for zone_name in ("left", "middle", "right"):
            zone = self.layout["zones"][zone_name]
            if zone["x"] <= real_x < zone["x"] + zone["w"]:
                return zone_name
        return None

    def _handle_virtual_canvas_click(self, event):
        real_x = int(event.x / self.canvas_scale)
        real_y = int(event.y / self.canvas_scale)
        zone_name = self._zone_from_real_x(real_x)
        if zone_name is None:
            self._log(f"Touched non-responsive gap at x={real_x}")
            return

        m0 = getattr(self.chamber, f"{zone_name}_m0")
        zone = self.layout["zones"][zone_name]
        local_x = max(0, min(zone["w"] - 1, real_x - zone["x"]))
        local_y = max(0, min(zone["h"] - 1, real_y - zone["y"]))

        m0.simulate_touch(local_x, local_y, duration=0.2)
        self._zone_touch_until[zone_name] = time.time() + 0.25
        self._log(f"{zone_name.capitalize()} zone touched at ({local_x}, {local_y})")

    def _simulate_zone_touch(self, zone_name):
        m0 = getattr(self.chamber, f"{zone_name}_m0")
        zone = self.layout["zones"][zone_name]
        m0.simulate_touch(zone["w"] // 2, zone["h"] // 2, duration=0.2)
        self._zone_touch_until[zone_name] = time.time() + 0.25
        self._log(f"{zone_name.capitalize()} zone touched at center")

    def _break_beam(self):
        self.chamber.beambreak.simulate_break()
        self._log("Beam broken (animal at hopper)")

    def _restore_beam(self):
        self.chamber.beambreak.simulate_restore()
        self._log("Beam restored (animal left hopper)")

    def _print_state(self):
        state = self.chamber.get_state()
        self._log("=" * 50)
        self._log("CHAMBER STATE:")
        self._log(f"  Left M0: {'TOUCHED' if state['left_m0']['is_touched'] else 'not touched'}")
        self._log(f"    Image: {state['left_m0']['current_image'] or 'none'}")
        self._log(f"  Middle M0: {'TOUCHED' if state['middle_m0']['is_touched'] else 'not touched'}")
        self._log(f"    Image: {state['middle_m0']['current_image'] or 'none'}")
        self._log(f"  Right M0: {'TOUCHED' if state['right_m0']['is_touched'] else 'not touched'}")
        self._log(f"    Image: {state['right_m0']['current_image'] or 'none'}")
        self._log(f"  Beam: {'BROKEN' if state['beambreak']['state'] == 0 else 'intact'}")
        self._log(f"  Reward LED: {'ON' if state['reward_led']['is_on'] else 'OFF'}")
        self._log(f"  Punishment LED: {'ON' if state['punishment_led']['is_on'] else 'OFF'}")
        self._log(f"  Buzzer: {'ACTIVE' if state['buzzer']['is_active'] else 'silent'}")
        self._log(f"  Reward: {'DISPENSING' if state['reward']['is_dispensing'] else 'stopped'}")
        self._log(f"  Total rewards: {state['reward']['total_dispensed']}")
        self._log("=" * 50)

    def _display_image_on_canvas(self, canvas, image_path, zone_name, zone_rect):
        if not HAS_PIL or Image is None or ImageTk is None:
            return
        try:
            render_w = max(1, int(zone_rect["w"] * self.canvas_scale))
            render_h = max(1, int(zone_rect["h"] * self.canvas_scale))
            origin_x = int(zone_rect["x"] * self.canvas_scale)
            origin_y = int(zone_rect["y"] * self.canvas_scale)

            cache_key = f"{image_path}:{render_w}x{render_h}"
            if cache_key not in self._image_cache:
                pil_image = Image.open(image_path)
                pil_image = pil_image.resize((render_w, render_h), Image.Resampling.LANCZOS)
                self._image_cache[cache_key] = ImageTk.PhotoImage(pil_image)

            self._canvas_images[zone_name] = canvas.create_image(
                origin_x,
                origin_y,
                image=self._image_cache[cache_key],
                anchor="nw",
            )
        except Exception as exc:
            logger.warning(f"Could not load image {image_path}: {exc}")

    def _draw_virtual_display_base(self):
        self.virtual_canvas.delete("all")
        self.virtual_canvas.create_rectangle(
            0,
            0,
            self.virtual_canvas_w,
            self.virtual_canvas_h,
            fill="#0f0f0f",
            outline="",
        )

        for zone_name in ("left", "middle", "right"):
            zone = self.layout["zones"][zone_name]
            x1 = int(zone["x"] * self.canvas_scale)
            y1 = int(zone["y"] * self.canvas_scale)
            x2 = int((zone["x"] + zone["w"]) * self.canvas_scale)
            y2 = int((zone["y"] + zone["h"]) * self.canvas_scale)
            self.virtual_canvas.create_rectangle(
                x1, y1, x2, y2, fill="black", outline="#555", width=2
            )
            self.virtual_canvas.create_text(
                (x1 + x2) // 2,
                y2 - 12,
                text=zone_name.upper(),
                fill="#888",
                font=("Arial", 8, "bold"),
            )

        # Draw non-responsive gap labels to mirror physical split spacing.
        gaps = self.layout.get("gaps", [0, 0, 0, 0])
        gap_spans = [
            (0, self.layout["zones"]["left"]["x"], gaps[0]),
            (
                self.layout["zones"]["left"]["x"] + self.layout["zones"]["left"]["w"],
                self.layout["zones"]["middle"]["x"],
                gaps[1],
            ),
            (
                self.layout["zones"]["middle"]["x"] + self.layout["zones"]["middle"]["w"],
                self.layout["zones"]["right"]["x"],
                gaps[2],
            ),
            (
                self.layout["zones"]["right"]["x"] + self.layout["zones"]["right"]["w"],
                self.layout["display_width"],
                gaps[3],
            ),
        ]

        for start, end, gap_px in gap_spans:
            if end <= start:
                continue
            x1 = int(start * self.canvas_scale)
            x2 = int(end * self.canvas_scale)
            self.virtual_canvas.create_rectangle(
                x1,
                0,
                x2,
                self.virtual_canvas_h,
                fill="#111111",
                outline="",
                stipple="gray25",
            )
            self.virtual_canvas.create_text(
                (x1 + x2) // 2,
                14,
                text=f"gap {gap_px}",
                fill="#5f5f5f",
                font=("Arial", 7),
            )

    def _update_ui(self):
        state = self.chamber.get_state()
        self._draw_virtual_display_base()

        for zone_name, m0_key in [
            ("left", "left_m0"),
            ("middle", "middle_m0"),
            ("right", "right_m0"),
        ]:
            zone = self.layout["zones"][zone_name]
            m0_state = state[m0_key]
            label = self.zone_status_labels[zone_name]

            if m0_state["is_touched"] or time.time() < self._zone_touch_until[zone_name]:
                x1 = int(zone["x"] * self.canvas_scale)
                y1 = int(zone["y"] * self.canvas_scale)
                x2 = int((zone["x"] + zone["w"]) * self.canvas_scale)
                y2 = int((zone["y"] + zone["h"]) * self.canvas_scale)
                self.virtual_canvas.create_rectangle(x1, y1, x2, y2, outline="red", width=4)

            img_name = m0_state["current_image"]
            img_path = getattr(self.chamber.m0s[["left", "middle", "right"].index(zone_name)], "_current_image_path", None)

            if img_name:
                display_name = img_name if "/" not in img_name else img_name.split("/")[-1]
                label.config(text=f"Image: {display_name}", foreground="white")
                if HAS_PIL and img_path and os.path.exists(img_path):
                    self._display_image_on_canvas(self.virtual_canvas, img_path, zone_name, zone)
                else:
                    x1 = int(zone["x"] * self.canvas_scale)
                    y1 = int(zone["y"] * self.canvas_scale)
                    x2 = int((zone["x"] + zone["w"]) * self.canvas_scale)
                    y2 = int((zone["y"] + zone["h"]) * self.canvas_scale)
                    self.virtual_canvas.create_rectangle(
                        x1 + 4, y1 + 4, x2 - 4, y2 - 4, fill="white", outline="gray"
                    )
                    self.virtual_canvas.create_text(
                        (x1 + x2) // 2,
                        (y1 + y2) // 2,
                        text=display_name,
                        fill="black",
                        width=max(40, x2 - x1 - 10),
                    )
            else:
                label.config(text="No image", foreground="gray")

        if state["beambreak"]["state"] == 0:
            self.bb_status_label.config(text="BROKEN", foreground="red")
        else:
            self.bb_status_label.config(text="Not Broken", foreground="green")

        if state["reward_led"]["is_on"]:
            self.reward_led_label.config(
                text=f"ON (brightness: {state['reward_led']['brightness']})",
                foreground="yellow",
            )
        else:
            self.reward_led_label.config(text="OFF", foreground="gray")

        if state["punishment_led"]["is_on"]:
            self.punishment_led_label.config(
                text=f"ON (brightness: {state['punishment_led']['brightness']})",
                foreground="red",
            )
        else:
            self.punishment_led_label.config(text="OFF", foreground="gray")

        if state["buzzer"]["is_active"]:
            self.buzzer_label.config(
                text=f"ACTIVE ({state['buzzer']['frequency']}Hz)",
                foreground="orange",
            )
        else:
            self.buzzer_label.config(text="Silent", foreground="gray")

        if state["reward"]["is_dispensing"]:
            self.reward_label.config(text="DISPENSING", foreground="blue")
        else:
            self.reward_label.config(text="Stopped", foreground="gray")

        self.reward_count_label.config(text=f"Dispensed: {state['reward']['total_dispensed']}")

    def _start_update_loop(self):
        def update():
            if self._running:
                self._update_ui()
                self.root.after(self.update_interval, update)

        self._running = True
        self.root.after(self.update_interval, update)

    def _log(self, message):
        timestamp = time.strftime("%H:%M:%S")
        self.log_text.config(state="normal")
        self.log_text.insert("end", f"[{timestamp}] {message}\n")
        self.log_text.see("end")
        self.log_text.config(state="disabled")

    def _clear_log(self):
        self.log_text.config(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.config(state="disabled")

    def run(self):
        logger.info("Starting Virtual Chamber GUI...")
        self._log("Virtual Chamber GUI started")
        self._log("Click on display zones to simulate touches")
        self._log("Gap regions are non-responsive")
        self.root.mainloop()
        self._running = False

    def run_async(self):
        gui_thread = threading.Thread(target=self.run, daemon=True)
        gui_thread.start()
        logger.info("Virtual Chamber GUI started in background thread")
        return gui_thread
