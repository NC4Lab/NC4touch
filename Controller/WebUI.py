# Create a WebUI using NiceUI that replicates the functionality of TUI
from nicegui import ui
from datetime import datetime
import logging
import asyncio

from Trainer import get_trainers
from helpers import get_ip_address, get_best_ip_address
from Session import Session
from file_picker import file_picker
from M0Device import M0Mode, M0Device
import time

import logging
session_logger = logging.getLogger('session_logger')
logger = logging.getLogger(f"session_logger.{__name__}")

#TODO: Work on the UI to make it more user friendly and visually appealing

class LogElementHandler(logging.Handler):
    """A logging handler that emits messages to a log element.
        https://nicegui.io/documentation/log    
    """

    def __init__(self, element: ui.log, level: int = logging.NOTSET) -> None:
        self.element = element
        super().__init__(level)

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            self.element.push(msg)
        except Exception:
            self.handleError(record)

class WebUI:
    def __init__(self, video_port=8080, ui_port=8081):
        # Initialize session and chamber
        self.ip = get_best_ip_address()
        self.ui_port = ui_port
        self.chamber_name = self.derive_chamber_name(self.ip)
        ui.run(host=self.ip if self.ip else '0.0.0.0', port=self.ui_port, title=f"{self.chamber_name} Control Panel", show=False)
        logger.info("Initializing WebUI...")
        self.video_port = video_port
        session_config = {"chamber_name": self.chamber_name} if self.chamber_name else {}
        self.session = Session(session_config=session_config)

        # Initialize UI elements
        # self.init_ui()

    def derive_chamber_name(self, ip_address):
        if not ip_address:
            return None

        try:
            last_octet = int(ip_address.split(".")[-1])
        except (ValueError, IndexError):
            logger.warning(f"Could not parse IP address: {ip_address}")
            return None

        chamber_number = last_octet - 10
        if chamber_number <= 0:
            logger.warning(f"Derived invalid chamber number from IP: {ip_address}")
            return None

        return f"Chamber{chamber_number}"
    
    def update_state(self):
        """Periodically update the state of the UI elements based on the session state."""
        # Update M0 status labels
        self.left_m0_port_label.set_text(f"Port: {self.session.chamber.get_left_m0().port}")
        self.left_m0_mode_label.set_text(f"Mode: {self.session.chamber.get_left_m0().mode.name}")
        self.left_m0_version_label.set_text(f"Firmware: {self.session.chamber.get_left_m0().firmware_version}")

        self.middle_m0_port_label.set_text(f"Port: {self.session.chamber.get_middle_m0().port}")
        self.middle_m0_mode_label.set_text(f"Mode: {self.session.chamber.get_middle_m0().mode.name}")
        self.middle_m0_version_label.set_text(f"Firmware: {self.session.chamber.get_middle_m0().firmware_version}")

        self.right_m0_port_label.set_text(f"Port: {self.session.chamber.get_right_m0().port}")
        self.right_m0_mode_label.set_text(f"Mode: {self.session.chamber.get_right_m0().mode.name}")
        self.right_m0_version_label.set_text(f"Firmware: {self.session.chamber.get_right_m0().firmware_version}")

        self.house_led_brightness_slider.set_value(100.0 * self.session.chamber.house_led.brightness / 255.0)
        self.pump_test_button.set_value(self.session.chamber.reward.state)
        self.reward_led_test_button.set_value(self.session.chamber.reward_led.active)
        self.reward_color_input.set_value(self.rgb_to_hex(self.session.chamber.reward_led.color))
        self.punishment_led_test_button.set_value(self.session.chamber.punishment_led.active)
        self.punishment_color_input.set_value(self.rgb_to_hex(self.session.chamber.punishment_led.color))

    async def m0_discover(self):
        self.discover_button.props('color=red')
        self.discover_button_spinner.visible = True
        await asyncio.sleep(0.1)  # Briefly change button color to indicate action
        self.session.chamber.arduino_cli_discover()
        self.discover_button.props('color=blue')
        self.discover_button_spinner.visible = False
    
    async def m0_reopen_serial(self):
        self.open_serial_button.props('color=red')
        self.open_serial_button_spinner.visible = True
        await asyncio.sleep(0.1)  # Briefly change button color to indicate action
        self.session.chamber.m0_reopen_serial()
        await asyncio.sleep(2.0)  # Wait a moment for the serial port to reopen before updating M0 status
        self.open_serial_button.props('color=blue')
        self.open_serial_button_spinner.visible = False
    
    async def m0_close_serial(self):
        self.close_serial_button.props('color=red')
        self.close_serial_button_spinner.visible = True
        await asyncio.sleep(0.1)  # Briefly change button color to indicate action
        self.session.chamber.m0_close_serial()
        self.close_serial_button.props('color=blue')
        self.close_serial_button_spinner.visible = False
    
    async def m0_sync_images(self):
        self.sync_images_button.props('color=red')
        self.sync_images_button_spinner.visible = True
        await asyncio.sleep(0.1)  # Briefly change button color to indicate action
        self.session.chamber.m0_sync_images()
        self.sync_images_button.props('color=blue')
        self.sync_images_button_spinner.visible = False
    
    async def m0_upload_sketches(self):
        self.upload_code_button.props('color=red')
        self.upload_code_button_spinner.visible = True
        await asyncio.sleep(0.1)  # Briefly change button color to indicate action
        self.session.chamber.m0_upload_sketches()
        self.upload_code_button.props('color=blue')
        self.upload_code_button_spinner.visible = False

    def init_ui(self):
        ui.timer(1, self.update_state)  # Start a timer to update M0 status labels every second
        ui.label(f"{self.chamber_name} Control Panel").style('font-size: 24px; font-weight: bold; text-align: center; margin-top: 20px;')
        with ui.row():
            with ui.column():
                with ui.card():
                    ui.label('Session Configuration').style('font-size: 18px; font-weight: bold; text-align: center; margin-top: 20px;')

                    ui.label('Chamber Name:').style('width: 200px;')
                    self.chamber_name_input = ui.input(self.session.config["chamber_name"],
                                                    on_change = lambda e:self.session.set_chamber_name(e.value)).style('width: 200px;')

                    ui.label('Rodent Name:').style('width: 200px;')
                    self.rodent_name_input = ui.input(self.session.config["rodent_name"],
                                                    on_change = lambda e: self.session.set_rodent_name(e.value)).style('width: 200px;')
                    
                    ui.label('ITI Duration (s):').style('width: 200px;')
                    self.iti_duration_input = ui.input(str(self.session.config["iti_duration"]),
                                                    on_change = lambda e: self.session.set_iti_duration(int(e.value))).style('width: 200px;')

                    ui.label('Trainer Sequence Directory:').style('width: 200px;')
                    self.trainer_seq_dir_input = ui.input(self.session.config["trainer_seq_dir"],
                                                        on_change=lambda e: self.session.set_trainer_seq_dir(e.value)).style('width: 200px;')

                    ui.label('Trainer Sequence File:').style('width: 200px;')
                    self.trainer_seq_file_button = ui.button("Select File").on_click(self.pick_trainer_seq_file).style('width: 200px;')
                    
                    self.trainer_seq_file_input = ui.input(self.session.config["trainer_seq_file"],
                                                        on_change=lambda e: self.session.set_trainer_seq_file(e.value)).style('width: 200px;')

                    ui.label('Data Directory:').style('width: 200px;')
                    self.data_dir_input = ui.input(self.session.config["data_dir"],
                                                on_change=lambda e: self.session.set_data_dir(e.value)).style('width: 200px;')
                    
                    ui.label('Video Directory:').style('width: 200px;')
                    self.video_dir_input = ui.input(self.session.config["video_dir"],
                                                    on_change=lambda e: self.session.set_video_dir(e.value)).style('width: 200px;')
                    
                    ui.label('Trainer:').style('width: 200px;')
                    self.trainer_select = ui.select(get_trainers(), value=self.session.config["trainer_name"], 
                                                    on_change=lambda e: self.session.set_trainer_name(e.value)).style('width: 200px;')


            with ui.column():
                with ui.card():
                    ui.label('Log').style('font-size: 18px; font-weight: bold; text-align: center; margin-top: 20px;')

                    log = ui.log(max_lines=10).classes('w-full').style('width: 800px; height: 200px;')
                    self.log_handler = LogElementHandler(log)
                    formatter = logging.Formatter('[%(asctime)s:%(name)s] %(message)s')
                    self.log_handler.setFormatter(formatter)
                    session_logger.addHandler(self.log_handler)
                    ui.context.client.on_disconnect(lambda: logger.removeHandler(self.log_handler))

                    ui.label('Log Level:').style('width: 200px;')
                    self.log_level_input = ui.select(['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'], value='DEBUG').style('width: 200px;')
                    self.log_level_input.on('change', lambda e: self.log_handler.setLevel(getattr(logging, e.value)))

                with ui.card():
                    ui.label('Camera Control').style('font-size: 18px; font-weight: bold; text-align: center; margin-top: 20px;')
                    # Show video stream from the camera
                    ui.label('Camera Stream:').style('width: 800px;')
                    ui.image(source=f"http://{self.ip}:{self.video_port}/stream").style('width: 640px; height: 480px;')
                
                    with ui.row():
                        # Reinitialize the camera
                        self.reinitialize_camera_button = ui.button("Reinitialize").on_click(self.session.chamber.camera.reinitialize)
                        self.reinitialize_camera_button.style('width: 200px; margin-top: 20px;')
                        self.video_recording_toggle = ui.toggle({0: "Video Rec Off", 1: "Video Rec On"}, value=False, on_change=lambda e: self.session.start_video_recording() if e.value else self.session.stop_video_recording())
                    
                    with ui.row():
                        # Slider to control house LED brightness
                        ui.label('House LED Brightness:').style('width: 200px;')
                        self.house_led_brightness_slider = ui.slider(min=0, max=100, value=0,
                                                                    on_change=lambda e: self.adjust_house_led_brightness(e.value)).style('width: 400px;')
            
            with ui.column():
                with ui.card():
                    ui.label('M0 Board Control').style('font-size: 18px; font-weight: bold; text-align: center; margin-top: 20px;')
                    # Buttons to control M0 boards
                    # self.discover_button = ui.button("Discover").on_click(self.m0_discover)
                    self.discover_button = ui.button(text="Discover", color="blue").on_click(self.m0_discover)
                    with self.discover_button:
                        # ui.label("Discover").style('color: white;')
                        self.discover_button_spinner = ui.spinner(color='white').style('margin-left: 10px;')
                        self.discover_button_spinner.visible = False

                    self.open_serial_button = ui.button(text="Open Serial Comm", color="blue").on_click(self.m0_reopen_serial)
                    with self.open_serial_button:
                        # ui.label("Open Serial Comm").style('color: white;')
                        self.open_serial_button_spinner = ui.spinner(color='white').style('margin-left: 10px;')
                        self.open_serial_button_spinner.visible = False

                    self.close_serial_button = ui.button(text="Close Serial Comm", color="blue").on_click(self.m0_close_serial)
                    with self.close_serial_button:
                        # ui.label("Close Serial Comm").style('color: white;')
                        self.close_serial_button_spinner = ui.spinner(color='white').style('margin-left: 10px;')
                        self.close_serial_button_spinner.visible = False

                    self.sync_images_button = ui.button(text="Sync Images", color="blue").on_click(self.m0_sync_images)
                    with self.sync_images_button:
                        # ui.label("Sync Images").style('color: white;')
                        self.sync_images_button_spinner = ui.spinner(color='white').style('margin-left: 10px;')
                        self.sync_images_button_spinner.visible = False

                    self.upload_code_button = ui.button(text="Upload Code", color="blue").on_click(self.m0_upload_sketches)
                    with self.upload_code_button:
                        # ui.label("Upload Code").style('color: white;')
                        self.upload_code_button_spinner = ui.spinner(color='white').style('margin-left: 10px;')
                        self.upload_code_button_spinner.visible = False
                    
                with ui.card():
                        ui.label('Left M0').style('font-size: 18px; font-weight: bold; text-align: center; margin-top: 20px;')
                        # Show M0 port
                        self.left_m0_port_label = ui.label(f"Port: {self.session.chamber.get_left_m0().port}")
                        self.left_m0_mode_label = ui.label(f"Mode: {self.session.chamber.get_left_m0().mode.name}")
                        self.left_m0_version_label = ui.label(f"Firmware Version: {self.session.chamber.get_left_m0().firmware_version}")

                        ui.label('Middle M0').style('font-size: 18px; font-weight: bold; text-align: center; margin-top: 20px;')
                        # Show M0 port
                        self.middle_m0_port_label = ui.label(f"Port: {self.session.chamber.get_middle_m0().port}")
                        self.middle_m0_mode_label = ui.label(f"Mode: {self.session.chamber.get_middle_m0().mode.name}")
                        self.middle_m0_version_label = ui.label(f"Firmware Version: {self.session.chamber.get_middle_m0().firmware_version}")

                        ui.label('Right M0').style('font-size: 18px; font-weight: bold; text-align: center; margin-top: 20px;')
                        # Show M0 port
                        self.right_m0_port_label = ui.label(f"Port: {self.session.chamber.get_right_m0().port}")
                        self.right_m0_mode_label = ui.label(f"Mode: {self.session.chamber.get_right_m0().mode.name}")
                        self.right_m0_version_label = ui.label(f"Firmware Version: {self.session.chamber.get_right_m0().firmware_version}")

                with ui.card():
                    ui.label('Training Control').style('font-size: 18px; font-weight: bold; text-align: center; margin-top: 20px;')
                    # Buttons to control training session
                    self.start_training_button = ui.button("Start Training").on_click(self.session.start_training)
                    self.stop_training_button = ui.button("Stop Training").on_click(self.session.stop_training)
                    self.start_priming_button = ui.button("Start Priming").on_click(self.session.start_priming)
                    self.stop_priming_button = ui.button("Stop Priming").on_click(self.session.stop_priming)
            
            with ui.column():
                with ui.card():
                    ui.label('Chamber Control').style('font-size: 18px; font-weight: bold; text-align: center; margin-top: 20px;')
                    # Button to test pumps
                    self.pump_test_button = ui.toggle({0: "Pump off", 1: "Pump on"}, value = self.session.chamber.reward.state, 
                                                      on_change=lambda e: self.session.chamber.reward.dispense() if e.value else self.session.chamber.reward.stop())
                    self.reward_color_label = ui.label("Reward LED Color:")
                    self.reward_color_input = ui.color_input(value=self.rgb_to_hex(self.session.chamber.reward_led.color),
                                                            on_change=lambda e: self.session.chamber.reward_led.set_color(self.hex_to_rgb(e.value)))
                    self.reward_led_test_button = ui.toggle({0: "Reward LED off", 1: "Reward LED on"}, 
                                                                value = self.session.chamber.reward_led.active,
                                                                on_change=lambda e: self.session.chamber.reward_led.activate() if e.value else self.session.chamber.reward_led.deactivate())
                    
                    self.punishment_color_label = ui.label("Punishment LED Color:")
                    self.punishment_color_input = ui.color_input(value=self.rgb_to_hex(self.session.chamber.punishment_led.color),
                                                                on_change=lambda e: self.session.chamber.punishment_led.set_color(self.hex_to_rgb(e.value)))
                    self.punishment_led_test_button = ui.toggle({0: "Punishment LED off", 1: "Punishment LED on"}, 
                                                                value = self.session.chamber.punishment_led.active,
                                                                on_change=lambda e: self.session.chamber.punishment_led.activate() if e.value else self.session.chamber.punishment_led.deactivate())
                    
                    self.left_m0_cmd_label = ui.label("Left M0 Command:")
                    self.left_m0_cmd_input = ui.input(value = "")
                    self.left_m0_cmd_button = ui.button("Send").on_click(lambda: self.session.chamber.get_left_m0().send_command(self.left_m0_cmd_input.value))

                    self.middle_m0_cmd_label = ui.label("Middle M0 Command:")
                    self.middle_m0_cmd_input = ui.input(value = "")
                    self.middle_m0_cmd_button = ui.button("Send").on_click(lambda: self.session.chamber.get_middle_m0().send_command(self.middle_m0_cmd_input.value))

                    self.right_m0_cmd_label = ui.label("Right M0 Command:")
                    self.right_m0_cmd_input = ui.input(value = "")
                    self.right_m0_cmd_button = ui.button("Send").on_click(lambda: self.session.chamber.get_right_m0().send_command(self.right_m0_cmd_input.value))

    
    def rgb_to_hex(self, rgb):
        return '#%02x%02x%02x' % rgb

    def hex_to_rgb(self, hex_color):
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    async def pick_trainer_seq_file(self) -> None:
        result = await file_picker(directory = self.session.config["trainer_seq_dir"], multiple = False)
        if result is None:
            logger.info("No file selected")
            return
        
        logger.info(f"File selected: {result[0]}")
        self.session.set_trainer_seq_file(result[0])
        self.trainer_seq_file_input.set_value(result[0])
    
    def adjust_house_led_brightness(self, value):
        """Adjust house LED brightness based on slider value."""
        brightness_value = int(value * 255 / 100)
        if brightness_value != self.session.chamber.house_led.brightness:
            if brightness_value == 0:
                self.session.chamber.house_led.deactivate()
            else:
                # Convert 1-100 to 0-255 brightness value
                self.session.chamber.house_led.set_brightness(brightness_value)
                self.session.chamber.house_led.activate()

web_ui = WebUI()

@ui.page('/')
def main_page():
    web_ui.init_ui()