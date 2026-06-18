# Create a WebUI using NiceGUI that replicates the functionality of TUI
import os
import re
from nicegui import ui
import logging
from collections import deque

from trainers import get_trainers
from Session import Session
from file_picker import file_picker

session_logger = logging.getLogger('session_logger')
logger = logging.getLogger(f"session_logger.{__name__}")

SESSION_LOG_LINE_RE = re.compile(r'^\[(?P<meta>.*):(?P<level>[A-Z]+)\]\s(?P<message>.*)$')


class LogElementHandler:
    """Follow the active session log file and mirror it into the UI log widget."""

    def __init__(self, element: ui.log, log_file: str, level: int = logging.DEBUG) -> None:
        self.element = element
        self.log_file = log_file
        self.visible_level = level
        self.records = deque(maxlen=2000)
        self._file_offset = 0
        self._file_signature = None

    def _parse_line(self, line: str) -> tuple[int, str]:
        match = SESSION_LOG_LINE_RE.match(line)
        if match:
            level_name = match.group('level')
            message = match.group('message')
            level = getattr(logging, level_name, logging.INFO)
            return level, f"[{level_name}] {message}"

        return logging.INFO, line

    def _append_line(self, level: int, message: str) -> None:
        self.records.append((level, message))
        if level >= self.visible_level:
            self.element.push(message)

    def refresh(self) -> None:
        try:
            stat_result = os.stat(self.log_file)
        except FileNotFoundError:
            return

        file_signature = (stat_result.st_dev, stat_result.st_ino)
        if file_signature != self._file_signature or stat_result.st_size < self._file_offset:
            self._file_signature = file_signature
            self._file_offset = 0

        try:
            with open(self.log_file, 'r', encoding='utf-8', errors='replace') as log_stream:
                log_stream.seek(self._file_offset)
                while True:
                    line = log_stream.readline()
                    if not line:
                        break
                    level, message = self._parse_line(line.rstrip('\n'))
                    self._append_line(level, message)
                self._file_offset = log_stream.tell()
        except Exception:
            logger.exception("Unable to refresh session log view from %s", self.log_file)

    def set_visible_level(self, level: int) -> None:
        self.visible_level = level
        self.rebuild()

    def rebuild(self) -> None:
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
        self.syncing_video_recording_toggle = False

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
        if hasattr(self, "video_recording_toggle"):
            desired_value = 1 if self.session.is_video_recording else 0
            if self.video_recording_toggle.value != desired_value:
                self.syncing_video_recording_toggle = True
                try:
                    self.video_recording_toggle.set_value(desired_value)
                finally:
                    self.syncing_video_recording_toggle = False

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
        if self.syncing_video_recording_toggle:
            return
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
                    --page-bg: #121417;
                    --panel-bg: #1d232b;
                    --panel-border: rgba(214, 220, 229, 0.16);
                    --panel-shadow: 0 16px 40px rgba(0, 0, 0, 0.32);
                    --text-main: #f2f5f8;
                    --text-muted: #b9c3cf;
                    --accent: #35c2a3;
                }
                body {
                    background: var(--page-bg);
                    color: var(--text-main);
                    -webkit-touch-callout: none;
                    font-size: 17px;
                }
                body, .page-shell, .page-shell * {
                    -webkit-user-drag: none;
                }
                .page-shell {
                    min-height: 100vh;
                    padding: 10px 14px 18px;
                    max-width: 100%;
                }
                .hero-panel {
                    background: #1a2028;
                    border: 1px solid var(--panel-border);
                    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.24);
                    border-radius: 8px;
                    padding: 8px 12px;
                    margin-bottom: 10px;
                }
                .hero-title {
                    font-size: 1.2rem;
                    font-weight: 800;
                    color: var(--text-main);
                    letter-spacing: 0;
                }
                .hero-subtitle {
                    color: var(--text-muted);
                    margin-top: 1px;
                    font-size: 0.82rem;
                }
                .glass-card {
                    background: var(--panel-bg);
                    border: 1px solid var(--panel-border);
                    box-shadow: var(--panel-shadow);
                    border-radius: 8px;
                    padding: 0 !important;
                }
                .top-grid {
                    display: grid;
                    grid-template-columns: minmax(0, 1.45fr) minmax(430px, 1fr);
                    gap: 14px;
                    align-items: stretch;
                }
                .top-stack {
                    display: grid;
                    grid-template-rows: auto minmax(0, 1fr);
                    gap: 14px;
                    min-height: 0;
                }
                .camera-card,
                .log-card {
                    display: flex;
                    flex-direction: column;
                    min-height: 0;
                }
                .config-grid {
                    display: grid;
                    grid-template-columns: repeat(2, minmax(0, 1fr));
                    gap: 14px;
                    margin-top: 14px;
                }
                .card-title {
                    font-size: 1rem;
                    font-weight: 700;
                    color: var(--text-main);
                    margin-bottom: 6px;
                    letter-spacing: 0;
                    padding: 10px 14px 0 14px;
                }
                .field-label {
                    color: var(--text-muted);
                    font-size: 0.9rem;
                    margin-top: 5px;
                    margin-bottom: 4px;
                }
                .status-chip {
                    display: inline-flex;
                    align-items: center;
                    gap: 4px;
                    border-radius: 999px;
                    padding: 5px 9px;
                    background: rgba(53, 194, 163, 0.14);
                    border: 1px solid rgba(53, 194, 163, 0.34);
                    color: var(--text-main);
                    font-size: 0.82rem;
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
                    min-height: clamp(360px, 50vh, 560px);
                    border-radius: 8px;
                    border: 1px dashed rgba(148, 163, 184, 0.35);
                    background: rgba(9, 12, 16, 0.55);
                    color: var(--text-muted);
                    text-align: center;
                    padding: 18px;
                    font-size: 1rem;
                    width: 100%;
                    aspect-ratio: 16 / 9;
                }
                .camera-feed {
                    width: 100%;
                    min-height: clamp(360px, 50vh, 560px);
                    aspect-ratio: 16 / 9;
                    object-fit: cover;
                    border-radius: 8px;
                }
                .camera-controls {
                    padding: 10px 14px 14px;
                }
                /* Expansion panels */
                .nicegui-expansion {
                    padding: 0 !important;
                }
                .nicegui-expansion-header {
                    padding: 12px 14px !important;
                    font-weight: 600;
                    color: var(--text-main);
                    border-bottom: 1px solid rgba(148, 163, 184, 0.16);
                    font-size: 1rem;
                }
                .nicegui-expansion-content {
                    padding: 10px 14px 14px !important;
                }
                /* Input and select styling */
                .nicegui-input input,
                .nicegui-select select {
                    background: rgba(9, 12, 16, 0.34) !important;
                    border-color: rgba(148, 163, 184, 0.24) !important;
                    color: var(--text-main) !important;
                    font-size: 0.95rem;
                    padding: 6px 8px !important;
                }
                /* Button styling */
                .nicegui-button {
                    padding: 8px 12px !important;
                    font-size: 0.95rem !important;
                    min-height: 42px;
                }
                /* Log view */
                .nicegui-log {
                    background: rgba(9, 12, 16, 0.58) !important;
                    font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace !important;
                    font-size: 0.86rem !important;
                    line-height: 1.4 !important;
                    padding: 8px !important;
                }
                .log-view {
                    height: clamp(420px, 58vh, 640px);
                    min-height: 0;
                }
                .training-card .nicegui-expansion-content {
                    padding-top: 12px !important;
                }
                /* Slider styling */
                .nicegui-slider {
                    margin: 5px 0 !important;
                }
                /* Toggle styling */
                .nicegui-toggle {
                    margin: 4px 0 !important;
                }
                @media (max-width: 1240px) {
                    .top-grid,
                    .config-grid {
                        grid-template-columns: 1fr;
                    }
                    .log-view {
                        height: 360px;
                    }
                }
                @media (min-width: 1900px) {
                    .page-shell {
                        padding: 12px 18px 22px;
                    }
                    .camera-main,
                    .camera-feed {
                        min-height: clamp(420px, 52vh, 650px);
                    }
                    .log-view {
                        height: clamp(480px, 60vh, 720px);
                    }
                }
            </style>
            <script>
                const blockSecondaryPointerActions = event => {
                    if (event.button === 2 || event.ctrlKey) {
                        event.preventDefault();
                        event.stopPropagation();
                    }
                };

                const blockBrowserMenu = event => {
                    event.preventDefault();
                    event.stopPropagation();
                };

                document.addEventListener('contextmenu', blockBrowserMenu, true);
                document.addEventListener('auxclick', blockSecondaryPointerActions, true);
                document.addEventListener('mousedown', blockSecondaryPointerActions, true);
                document.addEventListener('pointerdown', blockSecondaryPointerActions, true);
                document.addEventListener('selectstart', blockBrowserMenu, true);
                document.addEventListener('dragstart', blockBrowserMenu, true);
            </script>
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
                        ui.label('Live monitoring first; session setup below.').classes('hero-subtitle')
                    with ui.column().classes('items-end gap-2'):
                        if self.virtual_mode:
                            ui.label('Virtual Mode').classes('status-chip')
                        self.log_level_badge = ui.label('Visible logs: DEBUG').classes('status-chip')

            with ui.element('div').classes('top-grid w-full'):
                with ui.card().classes('glass-card camera-card w-full'):
                    ui.label('Live Camera Feed').classes('card-title')
                    if self.virtual_mode:
                        ui.html(
                            '<div class="camera-main">'
                            '<div>'
                            '<div style="font-size: 1.2rem; font-weight: 700; color: #f2f5f8; margin-bottom: 8px;">Virtual Camera Active</div>'
                            '<div style="font-size: 1rem; color: #b9c3cf;">No physical camera stream required</div>'
                            '</div>'
                            '</div>'
                        )
                    else:
                        ui.image(source=f"http://{self.ip}:{self.video_port}/stream").classes('camera-feed')

                    with ui.element('div').classes('camera-controls'):
                        with ui.row().classes('w-full q-gutter-sm'):
                            self.reinitialize_camera_button = ui.button('Reinit', on_click=self.reinitialize_camera).classes('col')
                            self.focus_camera_button = ui.button('Focus', on_click=self.lock_camera_focus).classes('col')
                            self.video_recording_toggle = ui.toggle({0: 'Rec Off', 1: 'Rec On'}, value=0, on_change=lambda e: self.toggle_video_recording(bool(e.value))).classes('col')

                        ui.label('House LED (0-100%)').classes('field-label')
                        self.house_led_brightness_slider = ui.slider(min=0, max=100, value=0, on_change=lambda e: self.adjust_house_led_brightness(e.value)).classes('w-control')

                with ui.element('div').classes('top-stack w-full'):
                    with ui.card().classes('glass-card training-card w-full'):
                        with ui.expansion('Training Control', value=True).classes('w-full').style('font-weight: 600;'):
                            with ui.row().classes('w-full q-gutter-sm'):
                                self.start_training_button = ui.button('Start', on_click=self.start_training).classes('col')
                                self.stop_training_button = ui.button('Stop', on_click=self.stop_training).classes('col')
                            with ui.row().classes('w-full q-gutter-sm q-mt-sm'):
                                self.start_priming_button = ui.button('Prime', on_click=self.start_priming).classes('col')
                                self.stop_priming_button = ui.button('Stop Prime', on_click=self.stop_priming).classes('col')

                    with ui.card().classes('glass-card log-card w-full'):
                        ui.label('Session Log').classes('card-title')
                        self.log_view = ui.log(max_lines=250).classes('w-full log-view')
                        self.log_handler = LogElementHandler(self.log_view, self.session.session_log_file)
                        self.log_handler.refresh()
                        ui.timer(0.5, self.log_handler.refresh)

                        with ui.row().classes('w-full q-gutter-sm items-center q-mt-sm'):
                            ui.label('Level:').classes('text-sm')
                            self.log_level_input = ui.select(
                                ['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                                value='DEBUG',
                                on_change=lambda e: self.set_log_level(e.value),
                            ).classes('col').style('max-width: 150px;')

            with ui.element('div').classes('config-grid w-full'):
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

                with ui.card().classes('glass-card w-full').style('padding: 0;'):
                    with ui.expansion('Paths & Files', value=False).classes('w-full').style('font-weight: 600;'):
                        ui.label('Trainer Sequence Directory').classes('field-label')
                        self.trainer_seq_dir_input = ui.input(self.session.config["trainer_seq_dir"], on_change=lambda e: self.session.set_trainer_seq_dir(e.value)).classes('w-control')

                        ui.label('Trainer Sequence File').classes('field-label')
                        self.trainer_seq_file_button = ui.button('Select File', on_click=self.pick_trainer_seq_file).classes('w-control')
                        self.trainer_seq_file_input = ui.input(self.session.config["trainer_seq_file"], on_change=lambda e: self.session.set_trainer_seq_file(e.value)).classes('w-control')

                        ui.label('Data Directory').classes('field-label')
                        self.data_dir_input = ui.input(self.session.config["data_dir"], on_change=lambda e: self.session.set_data_dir(e.value)).classes('w-control')

                        ui.label('Video Directory').classes('field-label')
                        self.video_dir_input = ui.input(self.session.config["video_dir"], on_change=lambda e: self.session.set_video_dir(e.value)).classes('w-control')

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


if __name__ in {"__main__", "__mp_main__"}:
    setup_webui()
