import os
import time
import pigpio
import yaml
import csv
import netifaces

# Local modules
from Chamber import Chamber
from Trainer import Trainer

class Session:
    """
    This class manages the session configuration, hardware initialization, and training phases.
    It uses the Chamber class to manage the hardware components and the Trainer class to manage the training phases.
    """
    def __init__(self, session_config_file=None, chamber_config_file=None, trainer_config_file=None):
        code_dir = os.path.dirname(os.path.realpath(__file__))

        # Find and load the config files
        if not session_config_file:
            self.session_config_file = os.path.join(code_dir, 'session_config.yaml')
        else:
            self.session_config_file = session_config_file
        
        if not chamber_config_file:
            chamber_config_file = os.path.join(code_dir, 'chamber_config.yaml')
        else:
            self.chamber_config_file = chamber_config_file
        
        if not trainer_config_file:
            trainer_config_file = os.path.join(code_dir, 'trainer_config.yaml')
        else:
            self.trainer_config_file = trainer_config_file

        # Initialize config files
        self.init_session_config_file()

        self.phase_name = self.session_config.get("phase_name", "Habituation")
        self.rodent_name = self.session_config.get("rodent_name", "test_rodent")
        self.iti_duration = self.session_config.get("iti_duration", 10)
        self.seq_csv_dir = self.session_config.get("seq_csv_dir", os.path.join(code_dir, "sequences"))
        self.seq_csv_file = self.session_config.get("seq_csv_file", "sequences.csv")
        self.data_csv_dir = self.session_config.get("data_csv_dir", os.path.join(code_dir, "data"))
        self.video_dir = self.session_config.get("video_dir", os.path.join(code_dir, "videos"))

        self.chamber = Chamber(self.chamber_config_file)
        self.trainer = Trainer(self.trainer_config_file)

        # Video Recording
        self.is_recording = False

        # Session Timer
        self.session_start_time = None

        # Initialize the trainer
        self.init_trainer()

    def init_trainer(self):
        self.trainer = Main.MultiPhaseTraining(self.pi, self.peripherals, self.m0_boards)
        print("Trainer updated with discovered boards.")
        self.trainer.open_realtime_csv("FullSession_ReDiscovered")

    def start_training(self):
        if not self.trainer:
            print("Trainer not initialized.")
            return
        if not self.rodent_name:
            print("Rodent ID not set.")
            return
        
        csv_file = os.path.join(self.seq_csv_dir, self.seq_csv_file)

        print(f"Starting phase: {self.phase_name}, rodent={self.rodent_name}")
        if self.phase_name == "Habituation":
            self.trainer.Habituation()
        elif self.phase_name == "Initial Touch":
            self.trainer.initial_touch_phase(csv_file)
        elif self.phase_name == "Must Touch":
            self.trainer.must_touch_phase(csv_file)
        elif self.phase_name == "Must Initiate":
            self.trainer.must_initiate_phase(csv_file)
        elif self.phase_name == "Punish Incorrect":
            self.trainer.punish_incorrect_phase(csv_file)
        elif self.phase_name == "Simple Discrimination":
            self.trainer.simple_discrimination_phase(csv_file)
        elif self.phase_name == "Complex Discrimination":
            self.trainer.complex_discrimination_phase(csv_file)
        print("Phase run finished.")

    def stop_recording(self):
        if self.is_recording:
            self.chamber.camera.stop_recording()
            self.is_recording = False
            print("Recording stopped.")
        else:
            print("No recording in progress to stop.")
    
    def start_recording(self):
        if not self.is_recording:
            datetime_str = time.strftime("%Y%m%d_%H%M%S")
            video_file = os.path.join(self.video_dir, f"{datetime_str}_{self.rodent_name}.mp4")

            self.chamber.camera.start_recording(video_file)
            self.is_recording = True
            print("Recording started to:", video_file)
        else:
            print("Recording is already in progress.")

    def init_session_config_file(self):
        if os.path.isfile(self.session_config_file):
            with open(self.session_config_file, 'r') as file:
                self.session_config = yaml.safe_load(file)
        else:
            self.session_config = {}
    
    def save_to_session_config(self, key, value):
        self.session_config[key] = value
        with open(self.session_config_file, 'w') as f:
            yaml.dump(self.session_config, f)

    def set_iti_duration(self, iti_duration):
        if isinstance(iti_duration, int) and iti_duration > 0:
            self.iti_duration = iti_duration
            print(f"ITI Duration set to: {self.iti_duration} seconds")
            self.save_to_session_config("iti_duration", self.iti_duration)
        else:
            print("Invalid ITI Duration")

    def set_seq_csv_dir(self, seq_csv_dir):
        if os.path.isdir(seq_csv_dir):
            self.seq_csv_dir = seq_csv_dir
            print(f"Seq CSV directory set to: {self.seq_csv_dir}")
            self.save_to_session_config("seq_csv_dir", self.seq_csv_dir)
        else:
            print("Invalid Sequence directory")

    def set_seq_csv_file(self, seq_csv_file):
        if os.path.isfile(os.path.join(self.seq_csv_dir, seq_csv_file)):
            self.seq_csv_file = seq_csv_file
            print(f"Seq CSV file set to: {self.seq_csv_file}")
            self.save_to_session_config("seq_csv_file", self.seq_csv_file)
        else:
            print("Invalid Sequence CSV file entered.")

    def set_video_dir(self, video_dir):
        if os.path.isdir(video_dir):
            self.video_dir = video_dir
            print(f"Video directory set to: {self.video_dir}")
            self.save_to_session_config("video_dir", self.video_dir)
        else:
            print("Invalid Video directory entered.")

    def set_data_csv_dir(self, data_csv_dir):
        if os.path.isdir(data_csv_dir):
            self.data_csv_dir = data_csv_dir
            print(f"Data CSV directory set to: {self.data_csv_dir}")
            self.session.save_to_config("data_csv_dir", self.data_csv_dir)
        else:
            print("Invalid Data directory")
    
    
    def set_phase_name(self, phase_name):
        if phase_name:
            self.phase_name = phase_name
            print(f"Phase name set to: {self.phase_name}")
            self.save_to_session_config("phase_name", phase_name)
        else:
            print("No Phase name entered.")

    def set_rodent_name(self, rodent_name):
        if rodent_name:
            self.rodent_name = rodent_name
            print(f"Rodent name set to: {self.rodent_name}")
            self.save_to_session_config("rodent_name", rodent_name)
        else:
            print("No Rodent name entered.")
    

    def export_data(self):
        if not self.trainer:
            print("No trainer to export data from.")
            return
        if not self.trainer.trial_data:
            print("No trial data to export.")
            return
        
        datetime_str = time.strftime("%Y%m%d_%H%M%S")
        csv_file = os.path.join(self.data_csv_dir, f"{datetime_str}_{self.rodent_name}_data.csv")
        self.trainer.export_results_csv(csv_file)
        print(f"Data exported to {csv_file}.")
    

    def stop_priming(self):
        if not self.trainer or 'reward' not in self.trainer.peripherals:
            print("No trainer or reward object to stop priming.")
            return
        print("Stopping priming.")
        self.trainer.peripherals['reward'].stop_priming()

    def start_priming(self):
        if not self.trainer or 'reward' not in self.trainer.peripherals:
            print("No trainer or reward object to prime.")
            return
        print("Starting to prime feeding tube.")
        self.trainer.peripherals['reward'].prime_feeding_tube()

    def stop_training(self):
        if self.trainer:
            self.trainer.stop_session()
            print("Training stopped.")
        else:
            print("No training session to stop.")

    def discover_m0s(self):
        self.m0_boards = m0_devices.discover_m0_boards()
        if self.m0_boards:
            print("Discovered boards:")
            for bid, dev in self.m0_boards.items():
                print(f" - {bid} => {dev}")
            self.init_trainer()
        else:
            print("No M0 boards found.")