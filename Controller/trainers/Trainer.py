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
    CONTROLLER_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    DEFAULT_SEQUENCE_DIR = os.path.join(CONTROLLER_DIR, "sequences")
    DEFAULT_SEQUENCE_FILE = "sequences.csv"
    SESSION_CONTEXT_KEYS = {"rodent_name", "data_dir", "trainer_seq_dir", "trainer_seq_file"}

    def __init__(self, chamber, trainer_config = None):
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
        # Trainer behavior is defined by hardcoded defaults in each trainer.
        # Only session metadata is accepted from callers.
        self.config = Config(config=self._session_context(trainer_config))

        # Ensure required parameters are set in the config
        self.config.ensure_param("trainer_name", self.__class__.__name__)
        self.config.ensure_param("rodent_name", "TestRodent")

        # House LED
        self.config.ensure_param("house_led_brightness_active", 200)
        self.config.ensure_param("house_led_brightness_iti", 50)

        # Common training
        self.config.ensure_param("num_trials", 30)
        self.config.ensure_param("iti_duration", 10)
        self.config.ensure_param("max_iti_duration", 20)
        self.config.ensure_param("iti_increment", 1)
        self.config.ensure_param("touch_timeout", 120)
        self.config.ensure_param("beam_break_wait_time", 10)
        self.config.ensure_param("reward_pump_secs", 3.0)

        # LED colors
        self.config.ensure_param("back_led_color", (0, 255, 0))
        self.config.ensure_param("front_led_color", (255, 0, 0))

        # Punishment
        self.config.ensure_param("punish_duration", 5.0)
        self.config.ensure_param("buzzer_duration", 0.5)

        self.config.ensure_param("data_dir", "/mnt/shared/data")

        self.data_file = None

    def _session_context(self, context):
        if not isinstance(context, dict):
            return {}
        return {key: value for key, value in context.items() if key in self.SESSION_CONTEXT_KEYS}

    def update_session_context(self, context):
        self.config.update_with_dict(self._session_context(context))
    
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
        self.chamber.house_led.set_brightness(self.config["house_led_brightness_active"])
        self.chamber.house_led.activate()

    def default_iti_start(self):
        """Dim house LED, deactivate back LED, activate beambreak. Returns current time."""
        self.chamber.house_led.set_brightness(self.config["house_led_brightness_iti"])
        self.chamber.back_led.deactivate()
        self.chamber.beambreak.activate()
        return time.time()

    def default_iti_check_beam_break(self, current_iti_duration):
        """Check for beam break during ITI and extend duration if needed."""
        if self.chamber.beambreak.state == False:
            logger.info("Beam broken during ITI. Adding iti_increment to ITI duration.")
            if current_iti_duration < self.config["max_iti_duration"]:
                current_iti_duration += self.config["iti_increment"]
        return current_iti_duration

    def default_deliver_reward(self, duration=None):
        """Dispense reward, activate back LED and beambreak. Returns start time."""
        self.chamber.reward.dispense()
        self.chamber.back_led.activate()
        self.chamber.beambreak.activate()
        return time.time()

    def default_stop_reward(self):
        """Stop pump, deactivate back LED and beambreak."""
        self.chamber.reward.stop()
        self.chamber.back_led.deactivate()
        self.chamber.beambreak.deactivate()

    def default_punishment(self):
        """Activate front LED and buzzer. Returns start time."""
        self.chamber.front_led.activate()
        self.chamber.buzzer.activate()
        return time.time()

    def default_stop_punishment(self):
        """Deactivate front LED and buzzer."""
        self.chamber.front_led.deactivate()
        self.chamber.buzzer.deactivate()

    def default_setup_led_colors(self):
        """Set back/front LED colors from config."""
        self.chamber.back_led.set_color(self.config["back_led_color"])
        self.chamber.front_led.set_color(self.config["front_led_color"])

    def default_end_trial(self):
        """Clear operant display zones at the end of a trial."""
        self.chamber.display_clear("left")
        self.chamber.display_clear("right")

    def default_start_training(self):
        """Reset chamber to default state, set LED colors, and open data file."""
        self.chamber.default_state()
        self.default_setup_led_colors()
        self.open_data_file()

    def default_stop_training(self):
        """Stop all hardware and close data file."""
        self.chamber.reward.stop()
        self.chamber.back_led.deactivate()
        self.chamber.front_led.deactivate()
        self.chamber.house_led.deactivate()
        self.chamber.buzzer.deactivate()
        self.chamber.beambreak.deactivate()
        if hasattr(self.chamber, "display_power_off"):
            self.chamber.display_power_off()
        self.close_data_file()

    # ---- Helper methods ----

    def check_touch(self):
        """Returns 'LEFT', 'RIGHT', or None based on which screen was touched."""
        if self.chamber.display_was_touched("left"):
            return "LEFT"
        elif self.chamber.display_was_touched("right"):
            return "RIGHT"
        return None

    def write_trial_data(self, data):
        """Wrapper around write_event for trial data."""
        self.write_event("TrialData", data)

    def free_reward(self, duration=None):
        """Dispense reward and turn on back LED. Caller manages timing via state machine."""
        self.chamber.reward.dispense()
        self.chamber.back_led.activate()

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
    
    
