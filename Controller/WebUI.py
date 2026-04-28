# Create a WebUI using NiceGUI that replicates the functionality of TUI
import os
from nicegui import ui
import logging
from collections import deque

from trainers import get_trainers
from Session import Session
from file_picker import file_picker

session_logger = logging.getLogger('session_logger')
logger = logging.getLogger(f"session_logger.{__name__}")


class LogElementHandler(logging.Handler):
    """Logging handler that buffers records and filters what is shown in the UI."""

    def __init__(self, element: ui.log, level: int = logging.DEBUG) -> None:
        super().__init__(logging.NOTSET)
        self.element = element
        self.visible_level = level
        self.records = deque(maxlen=2000)

    def emit(self, record: logging.LogRecord) -> None:
        try:
            message = self.format(record)
            self.records.append((record.levelno, message))
            if record.levelno >= self.visible_level:
                self.element.push(message)
        except Exception:
            self.handleError(record)

    def set_visible_level(self, level: int) -> None:
        self.visible_level = level
        self.refresh()

    def refresh(self) -> None:
        try:
            self.element.clear()
        except Exception:
            pass

        for record_level, message in self.records:
            if record_level >= self.visible_level:
                self.element.push(message)


class WebUI:
    def __init__(self, video_port=8080, ui_port=8081, virtual_mode=False):
        self.ip = self._best_host()
        self.ui_port = ui_port
        self.video_port = video_port
        self.virtual_mode = bool(virtual_mode)
        self.chamber_name = self.derive_chamber_name(self.ip)

        ui.run(
            host=self.ip if self.ip else '0.0.0.0',
            port=self.ui_port,
            title=f"{self.chamber_name} Control Panel",
            show=False,
        )

        logger.info("Initializing WebUI...")
        session_config = {"chamber_name": self.chamber_name} if self.chamber_name else {}
        session_config["virtual_mode"] = self.virtual_mode
        self.session = Session(session_config=session_config)
        if self.virtual_mode:
            logger.info("WebUI started in virtual mode; using virtual chamber and camera fallback.")

    def _best_host(self):
        try:
            from helpers import get_best_ip_address
            return get_best_ip_address()
        except Exception:
            logger.exception("Unable to determine best IP address; falling back to 0.0.0.0")
            return None

    def derive_chamber_name(self, ip_address):
        if not ip_address:
            return None

        try:
            last_octet = int(ip_address.split(".")[-1])
        except (ValueError, IndexError):
            logger.warning("Could not parse IP address: %s", ip_address)
            return None

        chamber_number = last_octet - 10
        if chamber_number <= 0:
            logger.warning("Derived invalid chamber number from IP: %s", ip_address)
            return None

        return f"Chamber{chamber_number}"

    def update_state(self):
        """Periodically update the state of the UI elements based on the session state."""
        self.house_led_brightness_slider.set_value(100.0 * self.session.chamber.house_led.brightness / 255.0)

    def set_log_level(self, level_name: str):
        level_name = (level_name or "INFO").upper()
        level = getattr(logging, level_name, logging.INFO)
        logger.info("WebUI log filter set to %s", level_name)
        self.log_handler.set_visible_level(level)
        try:
            self.log_level_badge.set_text(f"Visible logs: {level_name}")
        except Exception:
            pass

    def start_training(self):
        logger.info("WebUI: start training requested")
        self.session.start_training()

    def stop_training(self):
        logger.info("WebUI: stop training requested")
        self.session.stop_training()

    def start_priming(self):
        logger.info("WebUI: start priming requested")
        self.session.start_priming()

    def stop_priming(self):
        logger.info("WebUI: stop priming requested")
        self.session.stop_priming()

    def reinitialize_camera(self):
        logger.info("WebUI: reinitialize camera requested")
        if hasattr(self.session.chamber.camera, "reinitialize"):
            self.session.chamber.camera.reinitialize()
        else:
            logger.info("Virtual camera does not require reinitialization.")

    def lock_camera_focus(self):
        logger.info("WebUI: camera focus lock requested")
        if hasattr(self.session.chamber.camera, "lock_focus"):
            self.session.chamber.camera.lock_focus()
        else:
            logger.info("Virtual camera does not support focus locking.")

    def toggle_video_recording(self, enabled: bool):
        logger.info("WebUI: video recording toggled %s", "on" if enabled else "off")
        if enabled:
            self.session.start_video_recording()
        else:
            self.session.stop_video_recording()

    def adjust_house_led_brightness(self, value):
        """Adjust house LED brightness based on slider value."""
        brightness_value = int(value * 255 / 100)
        if brightness_value != self.session.chamber.house_led.brightness:
            logger.debug("Applying house LED brightness: %s/255", brightness_value)
            if brightness_value == 0:
                self.session.chamber.house_led.deactivate()
            else:
                self.session.chamber.house_led.set_brightness(brightness_value)
                self.session.chamber.house_led.activate()

    def apply_theme(self):
        ui.dark_mode().enable()
        ui.add_head_html(
            """
            <style>
                :root {
                    --panel-bg: rgba(15, 23, 42, 0.78);
                    --panel-border: rgba(148, 163, 184, 0.16);
                    --panel-shadow: 0 20px 55px rgba(0, 0, 0, 0.35);
                    --text-main: #e5e7eb;
                    --text-muted: #94a3b8;
                }
                body {
                    background:
                        radial-gradient(circle at top left, rgba(56, 189, 248, 0.18), transparent 28%),
                        radial-gradient(circle at top right, rgba(139, 92, 246, 0.16), transparent 32%),
                        linear-gradient(180deg, #020617 0%, #0f172a 55%, #111827 100%);
                    color: var(--text-main);
                }
                .page-shell {
                    min-height: 100vh;
                    padding: 12px 16px;
                    max-width: 100%;
                }
                .hero-panel {
                    background: linear-gradient(135deg, rgba(15, 23, 42, 0.92), rgba(30, 41, 59, 0.88));
                    border: 1px solid var(--panel-border);
                    box-shadow: var(--panel-shadow);
                    border-radius: 16px;
                    padding: 12px 16px;
                    margin-bottom: 12px;
                    backdrop-filter: blur(18px);
                }
                .hero-title {
                    font-size: 1.5rem;
                    font-weight: 800;
                    color: var(--text-main);
                    letter-spacing: 0.02em;
                }
                .hero-subtitle {
                    color: var(--text-muted);
                    margin-top: 2px;
                    font-size: 0.85rem;
                }
                .glass-card {
                    background: var(--panel-bg);
                    border: 1px solid var(--panel-border);
                    box-shadow: var(--panel-shadow);
                    border-radius: 14px;
                    backdrop-filter: blur(14px);
                    padding: 0 !important;
                }
                .card-title {
                    font-size: 0.95rem;
                    font-weight: 700;
                    color: var(--text-main);
                    margin-bottom: 8px;
                    letter-spacing: 0.02em;
                    padding: 12px 16px 0 16px;
                }
                .field-label {
                    color: var(--text-muted);
                    font-size: 0.8rem;
                    margin-top: 3px;
                    margin-bottom: 3px;
                }
                .status-chip {
                    display: inline-flex;
                    align-items: center;
                    gap: 4px;
                    border-radius: 999px;
                    padding: 4px 8px;
                    background: rgba(59, 130, 246, 0.12);
                    border: 1px solid rgba(59, 130, 246, 0.24);
                    color: var(--text-main);
                    font-size: 0.75rem;
                }
                .w-control {
                    width: 100%;
                }
                .camera-placeholder {
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    min-height: 160px;
                    border-radius: 10px;
                    border: 1px dashed rgba(148, 163, 184, 0.35);
                    background: rgba(15, 23, 42, 0.55);
                    color: var(--text-muted);
                    text-align: center;
                    padding: 12px;
                    font-size: 0.85rem;
                }
                .camera-main {
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    min-height: 420px;
                    border-radius: 10px;
                    border: 1px dashed rgba(148, 163, 184, 0.35);
                    background: rgba(15, 23, 42, 0.55);
                    color: var(--text-muted);
                    text-align: center;
                    padding: 20px;
                    font-size: 0.9rem;
                    width: 100%;
                    aspect-ratio: 16 / 9;
                }
                /* Expansion panels */
                .nicegui-expansion {
                    padding: 0 !important;
                }
                .nicegui-expansion-header {
                    padding: 10px 16px !important;
                    font-weight: 600;
                    color: var(--text-main);
                    border-bottom: 1px solid rgba(148, 163, 184, 0.16);
                    font-size: 0.9rem;
                }
                .nicegui-expansion-content {
                    padding: 10px 16px !important;
                }
                /* Input and select styling */
                .nicegui-input input,
                .nicegui-select select {
                    background: rgba(15, 23, 42, 0.4) !important;
                    border-color: rgba(148, 163, 184, 0.24) !important;
                    color: var(--text-main) !important;
                    font-size: 0.8rem;
                    padding: 4px 6px !important;
                }
                /* Button styling */
                .nicegui-button {
                    padding: 6px 10px !important;
                    font-size: 0.8rem !important;
                }
                /* Log view */
                .nicegui-log {
                    background: rgba(15, 23, 42, 0.5) !important;
                    font-size: 0.75rem !important;
                }
                /* Slider styling */
                .nicegui-slider {
                    margin: 3px 0 !important;
                }
                /* Toggle styling */
                .nicegui-toggle {
                    margin: 3px 0 !important;
                }
                /* 16:9 widescreen optimizations */
                @media (min-width: 1920px) {
                    .page-shell {
                        padding: 16px 24px;
                    }
                    .hero-title {
                        font-size: 1.75rem;
                    }
                    .camera-main {
                        min-height: 500px;
                    }
                }
            </style>
            """
        )

    def init_ui(self):
        self.apply_theme()
        ui.timer(1, self.update_state)
        ui.timer(0.05, lambda: self.session.chamber.display_flush())

        with ui.element('div').classes('page-shell'):
            with ui.card().classes('hero-panel w-full'):
                with ui.row().classes('items-center justify-between w-full'):
                    with ui.column().classes('gap-1'):
                        ui.label(f"{self.chamber_name} Control Panel").classes('hero-title')
                        ui.label('Single-display chamber control optimized for 1080p widescreen.').classes('hero-subtitle')
                    with ui.column().classes('items-end gap-2'):
                        if self.virtual_mode:
                            ui.label('Virtual Mode').classes('status-chip')
                        self.log_level_badge = ui.label('Visible logs: DEBUG').classes('status-chip')

            with ui.row().classes('w-full q-gutter-md items-stretch'):
                # Left column: Configuration (sidebar)
                with ui.column().classes('col-12 col-md-12 col-lg-3'):
                    with ui.card().classes('glass-card w-full').style('padding: 0;'):
                        with ui.expansion('Session Configuration', value=False).classes('w-full').style('font-weight: 600;'):
                            ui.label('Chamber Name').classes('field-label')
                            self.chamber_name_input = ui.input(self.session.config["chamber_name"], on_change=lambda e: self.session.set_chamber_name(e.value)).classes('w-control')

                            ui.label('Rodent Name').classes('field-label')
                            self.rodent_name_input = ui.input(self.session.config["rodent_name"], on_change=lambda e: self.session.set_rodent_name(e.value)).classes('w-control')

                            ui.label('ITI Duration (s)').classes('field-label')
                            self.iti_duration_input = ui.input(str(self.session.config["iti_duration"]), on_change=lambda e: self.session.set_iti_duration(int(e.value))).classes('w-control')

                            ui.label('Trainer').classes('field-label')
                            self.trainer_select = ui.select(get_trainers(), value=self.session.config["trainer_name"], on_change=lambda e: self.session.set_trainer_name(e.value)).classes('w-control')

                        with ui.expansion('Paths & Files', value=False).classes('w-full').style('font-weight: 600;'):
                            ui.label('Trainer Sequence Directory').classes('field-label')
                            self.trainer_seq_dir_input = ui.input(self.session.config["trainer_seq_dir"], on_change=lambda e: self.session.set_trainer_seq_dir(e.value)).classes('w-control').style('font-size: 0.8rem;')

                            ui.label('Trainer Sequence File').classes('field-label')
                            self.trainer_seq_file_button = ui.button('Select File', on_click=self.pick_trainer_seq_file).classes('w-control')
                            self.trainer_seq_file_input = ui.input(self.session.config["trainer_seq_file"], on_change=lambda e: self.session.set_trainer_seq_file(e.value)).classes('w-control').style('font-size: 0.8rem;')

                            ui.label('Data Directory').classes('field-label')
                            self.data_dir_input = ui.input(self.session.config["data_dir"], on_change=lambda e: self.session.set_data_dir(e.value)).classes('w-control').style('font-size: 0.8rem;')

                            ui.label('Video Directory').classes('field-label')
                            self.video_dir_input = ui.input(self.session.config["video_dir"], on_change=lambda e: self.session.set_video_dir(e.value)).classes('w-control').style('font-size: 0.8rem;')

                # Center column: Camera (MAIN FOCUS)
                with ui.column().classes('col-12 col-md-12 col-lg-5'):
                    with ui.card().classes('glass-card w-full').style('display: flex; flex-direction: column; height: 100%;'):
                        ui.label('Live Camera Feed').classes('card-title')
                        if self.virtual_mode:
                            ui.html(
                                '<div class="camera-main">'
                                '<div>'
                                '<div style="font-size: 1.1rem; font-weight: 600; color: #e5e7eb; margin-bottom: 8px;">Virtual Camera Active</div>'
                                '<div style="font-size: 0.9rem; color: #94a3b8;">No physical camera stream required</div>'
                                '</div>'
                                '</div>'
                            )
                        else:
                            ui.image(source=f"http://{self.ip}:{self.video_port}/stream").style('width: 100%; aspect-ratio: 16 / 9; object-fit: cover; border-radius: 12px;')

                        with ui.row().classes('w-full q-gutter-sm q-mt-sm'):
                            self.reinitialize_camera_button = ui.button('Reinit', on_click=self.reinitialize_camera).classes('col-4')
                            self.focus_camera_button = ui.button('Focus', on_click=self.lock_camera_focus).classes('col-4')
                            self.video_recording_toggle = ui.toggle({0: 'Rec Off', 1: 'Rec On'}, value=False, on_change=lambda e: self.toggle_video_recording(bool(e.value))).classes('col-4')

                        ui.label('House LED (0-100%)').classes('field-label')
                        self.house_led_brightness_slider = ui.slider(min=0, max=100, value=0, on_change=lambda e: self.adjust_house_led_brightness(e.value)).classes('w-control').style('margin-top: 8px;')

                # Right column: Logs & Training Controls
                with ui.column().classes('col-12 col-md-12 col-lg-4'):
                    # Training controls (expanded by default)
                    with ui.card().classes('glass-card w-full'):
                        with ui.expansion('Training Control', value=True).classes('w-full').style('font-weight: 600;'):
                            with ui.row().classes('w-full q-gutter-sm'):
                                self.start_training_button = ui.button('Start', on_click=self.start_training).classes('col')
                                self.stop_training_button = ui.button('Stop', on_click=self.stop_training).classes('col')
                            with ui.row().classes('w-full q-gutter-sm q-mt-sm'):
                                self.start_priming_button = ui.button('Prime', on_click=self.start_priming).classes('col')
                                self.stop_priming_button = ui.button('Stop Prime', on_click=self.stop_priming).classes('col')

                    # Logs section
                    with ui.card().classes('glass-card w-full q-mt-md'):
                        ui.label('Session Log').classes('card-title')
                        self.log_view = ui.log(max_lines=250).classes('w-full').style('height: 340px;')
                        self.log_handler = LogElementHandler(self.log_view)
                        formatter = logging.Formatter('[%(levelname)s] %(message)s')
                        self.log_handler.setFormatter(formatter)
                        session_logger.addHandler(self.log_handler)
                        ui.context.client.on_disconnect(lambda: session_logger.removeHandler(self.log_handler))

                        with ui.row().classes('w-full q-gutter-sm items-center q-mt-sm'):
                            ui.label('Level:').classes('text-sm')
                            self.log_level_input = ui.select(
                                ['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                                value='DEBUG',
                                on_change=lambda e: self.set_log_level(e.value),
                            ).classes('col').style('max-width: 150px;')

    async def pick_trainer_seq_file(self) -> None:
        result = await file_picker(directory=self.session.config["trainer_seq_dir"], multiple=False)
        if result is None:
            logger.info("No file selected")
            return

        logger.info("File selected: %s", result[0])
        self.session.set_trainer_seq_file(result[0])
        self.trainer_seq_file_input.set_value(result[0])


def setup_webui():
    """Set up the WebUI instance and NiceGUI page. Called by launcher scripts."""
    web_ui = WebUI(virtual_mode=os.environ.get("NC4TOUCH_VIRTUAL_MODE", "0").strip().lower() in {"1", "true", "yes", "on"})

    @ui.page('/')
    def main_page():
        web_ui.init_ui()
    
    return web_ui

