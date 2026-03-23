import json
import csv
import os
from Chamber import Chamber
from datetime import datetime
from abc import ABC, abstractmethod
from Config import Config
import time

import logging
logger = logging.getLogger(f"session_logger.{__name__}")

class Trainer(ABC):
    # Base trainer class for running training sessions

    def __init__(self, chamber, trainer_config = {}, trainer_config_file = '~/trainer_config.yaml'):
        # Accept both Chamber and VirtualChamber
        try:
            from Virtual.VirtualChamber import VirtualChamber
            valid_chamber = isinstance(chamber, (Chamber, VirtualChamber))
        except ImportError:
            valid_chamber = isinstance(chamber, Chamber)
        
        if not valid_chamber:
            logger.error("chamber must be an instance of Chamber or VirtualChamber")
            raise ValueError("chamber must be an instance of Chamber or VirtualChamber")

        self.chamber = chamber
        self.config = Config(config = trainer_config, config_file = trainer_config_file)

        self.data_file = None

    def ensure_trainer_param(self, param: str, default_value):
        self.config.ensure_param(param, default_value)

    def ensure_trainer_params(self, params: dict):
        for param, default_value in params.items():
            self.ensure_trainer_param(param, default_value)
    
    def read_trainer_seq_file(self, csv_file_path, min_num_columns = 2):
        # Read trial sequence from CSV file
        trials = []
        try:
            with open(csv_file_path, 'r') as f:
                reader = csv.reader(f)
                # Read rows into a list of trials
                trials = [row for row in reader if len(row) >= min_num_columns and not row[0].startswith("#")]
        except FileNotFoundError:
            logger.error(f"File not found: {csv_file_path}")
        except Exception as e:
            logger.error(f"Error reading file {csv_file_path}: {e}")
        
        return trials

    def open_data_file(self):
        # Create a new JSON file for trial data
        try:
            if self.data_file is None:
                date_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                chamber_name = self.chamber.config["chamber_name"]
                rodent_name = self.config["rodent_name"]
                trainer_name = self.config["trainer_name"]
                data_dir = self.config["data_dir"] or "/mnt/shared/data"
                os.makedirs(data_dir, exist_ok=True)
                self.data_filename = f"{date_str}_{chamber_name}_{trainer_name}_{rodent_name}_data.json"
                self.data_filepath = os.path.join(data_dir, self.data_filename)
                
                logger.info(f"Creating data file: {self.data_filepath}")
                self.data_file = open(self.data_filepath, "w")
                self.data_file.write("# NC4Touch training data\n")

                # Create a header with metadata
                header = {
                    "header": {
                        "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S_%f"),
                        "rodent": self.config["rodent_name"],
                        "chamber": self.chamber.config["chamber_name"],
                        "trainer": self.config["trainer_name"],
                    }
                }
                # Write the header to the json file
                json.dump(header, self.data_file)
                logger.info(f"Data file created successfully: {self.data_filepath}")
            else:
                logger.warning("Data file already open. Skipping creation.")
        except Exception as e:
            logger.error(f"Error creating data file: {e}")
    
    def close_data_file(self):
        # Close the data file when done
        if self.data_file:
            logger.info(f"Closing data file: {self.data_filename}")

            self.data_file.close()
            self.data_file = None
        else:
            logger.debug("Data file already closed; skipping.")
    
    def write_event(self, event, data):
        # Write a single event to the data file
        if self.data_file:
            event_data = {
                "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S_%f"),
                "event": event,
                "data": data,
            }
            json.dump(event_data, self.data_file)
        else:
            logger.warning("Data file is not open. Cannot write event.")

    # ---- Default behavior methods (opt-in, called from subclass state machines) ----

    def default_start_trial(self):
        """Set house LED to active brightness and activate it."""
        active_brightness = self.config["house_led_brightness_active"]
        if active_brightness is None:
            active_brightness = 200
        self.chamber.house_led.set_brightness(active_brightness)
        self.chamber.house_led.activate()

    def default_iti_start(self):
        """Dim house LED, deactivate reward LED, activate beambreak. Returns current time."""
        iti_brightness = self.config["house_led_brightness_iti"]
        if iti_brightness is None:
            iti_brightness = 50
        self.chamber.house_led.set_brightness(iti_brightness)
        self.chamber.reward_led.deactivate()
        self.chamber.beambreak.activate()
        return time.time()

    def default_iti_check_beam_break(self, current_iti_duration):
        """Check for beam break during ITI and extend duration if needed."""
        if self.chamber.beambreak.state == False:
            logger.info("Beam broken during ITI. Adding iti_increment to ITI duration.")
            max_iti_duration = self.config["max_iti_duration"]
            iti_increment = self.config["iti_increment"]
            if max_iti_duration is None:
                max_iti_duration = 20
            if iti_increment is None:
                iti_increment = 1
            if current_iti_duration < max_iti_duration:
                current_iti_duration += iti_increment
        return current_iti_duration

    def default_deliver_reward(self, duration=None):
        """Dispense reward, activate reward LED and beambreak. Returns start time."""
        self.chamber.reward.dispense()
        self.chamber.reward_led.activate()
        self.chamber.beambreak.activate()
        return time.time()

    def default_stop_reward(self):
        """Stop pump, deactivate reward LED and beambreak."""
        self.chamber.reward.stop()
        self.chamber.reward_led.deactivate()
        self.chamber.beambreak.deactivate()

    def default_punishment(self):
        """Activate punishment LED and buzzer. Returns start time."""
        self.chamber.punishment_led.activate()
        self.chamber.buzzer.activate()
        return time.time()

    def default_stop_punishment(self):
        """Deactivate punishment LED and buzzer."""
        self.chamber.punishment_led.deactivate()
        self.chamber.buzzer.deactivate()

    def default_setup_led_colors(self):
        """Set reward/punishment LED colors from config."""
        reward_color = self.config["reward_led_color"]
        punishment_color = self.config["punishment_led_color"]
        if reward_color is None:
            reward_color = (0, 255, 0)
        if punishment_color is None:
            punishment_color = (255, 0, 0)
        self.chamber.reward_led.set_color(reward_color)
        self.chamber.punishment_led.set_color(punishment_color)

    def default_end_trial(self):
        """Clear images on all M0s and write EndTrial event."""
        self.chamber.get_left_m0().send_command("BLACK")
        self.chamber.get_right_m0().send_command("BLACK")

    def default_start_training(self):
        """Reset chamber to default state, set LED colors, and open data file."""
        self.chamber.default_state()
        self.default_setup_led_colors()
        self.open_data_file()

    def default_stop_training(self):
        """Stop all hardware and close data file."""
        self.chamber.reward.stop()
        self.chamber.reward_led.deactivate()
        self.chamber.punishment_led.deactivate()
        self.chamber.house_led.deactivate()
        self.chamber.buzzer.deactivate()
        self.chamber.beambreak.deactivate()
        self.close_data_file()

    # ---- Helper methods ----

    def check_touch(self):
        """Returns 'LEFT', 'RIGHT', or None based on which screen was touched."""
        if self.chamber.get_left_m0().was_touched():
            return "LEFT"
        elif self.chamber.get_right_m0().was_touched():
            return "RIGHT"
        return None

    def prepare_touch_window(self, drain_events=True):
        """Clear stale touch events before a new touch-response window starts."""
        flush_fn = getattr(self.chamber, "display_flush", None)
        if callable(flush_fn):
            flush_fn()

        clear_fn = getattr(self.chamber, "display_clear_touches", None)
        if callable(clear_fn):
            clear_fn(drain_events=drain_events)
            return

        # Fallback for older chamber APIs that only expose edge-latched touches.
        left = getattr(self.chamber, "get_left_m0", lambda: None)()
        right = getattr(self.chamber, "get_right_m0", lambda: None)()
        if left is not None and hasattr(left, "was_touched"):
            left.was_touched()
        if right is not None and hasattr(right, "was_touched"):
            right.was_touched()

    def write_trial_data(self, data):
        """Wrapper around write_event for trial data."""
        self.write_event("TrialData", data)

    def free_reward(self, duration=None):
        """Dispense reward and turn on reward LED. Caller manages timing via state machine."""
        self.chamber.reward.dispense()
        self.chamber.reward_led.activate()

    def wait_for_trial_initiation(self):
        """Check if beambreak was triggered for trial initiation."""
        return self.chamber.beambreak.state == False

    def deliver_reward(self, duration=None):
        """Alias for default_deliver_reward for backwards compatibility."""
        return self.default_deliver_reward(duration)
    
    @abstractmethod
    def start_training(self):
        pass
    
    @abstractmethod
    def run_training(self):
        pass
    
    @abstractmethod
    def stop_training(self):
        pass
    
    