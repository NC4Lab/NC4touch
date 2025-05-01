import os
import time
import pigpio
import yaml
import csv
import netifaces

# Local modules
import m0_devices       # discover_m0_boards()
import Main             # The MultiPhaseTraining code
from LED import LED
from Reward import Reward
from BeamBreak import BeamBreak
from Buzzer import Buzzer
from Camera import Camera

class Session:
    def __init__(self):
        # pigpio/peripherals/trainer
        self.pi = None
        self.peripherals = None
        self.camera = None
        self.trainer = None

        # Video Recording
        self.is_recording = False
        self.video_file_path = ""

        # Session Timer
        self.session_start_time = None

        self.phase_name = self.load_from_config("phase_name")
        self.rodent_name = self.load_from_config("rodent_name")
        self.iti_duration = self.load_from_config("iti_duration")
        self.seq_csv_dir = self.load_from_config("seq_csv_dir")
        self.seq_csv_file = self.load_from_config("seq_csv_file")
        self.data_csv_dir = self.load_from_config("data_csv_dir")
        self.video_dir = self.load_from_config("video_dir")

        self.ip = netifaces.ifaddresses('eth0')[netifaces.AF_INET][0]['addr']
        print(f"IP Address: {self.ip}")

        # Initialize pigpio and trainer
        self.init_hardware()

        # Initialize config file
        self.init_config_file()

    def start_training(self):
        if not self.trainer:
            print("Trainer not initialized.")
            return
        if not self.rodent_name:
            print("Rodent ID not set.")
            return
        
        self.trainer.current_phase = self.phase_name
        self.trainer.iti_duration = self.iti_duration
        self.trainer.rodent_id = self.rodent_name
        self.trainer.trial_data = []
        self.session_start_time = time.time()
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
            self.camera.stop_recording()
            self.is_recording = False
            print("Recording stopped.")
        else:
            print("No recording in progress to stop.")
    
    def start_recording(self):
        if not self.camera:
            print("Camera not initialized.")
            return
        if not self.is_recording:
            datetime_str = time.strftime("%Y%m%d_%H%M%S")
            video_file = os.path.join(self.video_dir, f"{datetime_str}_{self.rodent_name}.mp4")

            self.camera.start_recording(video_file)
            self.is_recording = True
            print("Recording started.")
        else:
            print("Recording is already in progress.")

    def init_config_file(self):
        code_dir = os.path.dirname(os.path.realpath(__file__))
        self.config_file = os.path.join(code_dir, 'config.yaml')
        if os.path.isfile(self.config_file):
            with open(self.config_file, 'r') as file:
                self.config = yaml.safe_load(file)
        else:
            self.config = {}
    
    def load_from_config(self, key):
        if key in self.config:
            return self.config[key]
        else:
            print(f"Key '{key}' not found in config.")
            return ""
            return None
    
    def save_to_config(self, key, value):
        self.config[key] = value
        self.write_config_file()

    def write_config_file(self):
        with open(self.config_file, 'w') as f:
            yaml.dump(self.config, f)

    # ---------------- Hardware/Trainer Init ----------------
    def init_hardware(self):
        self.pi = pigpio.pi()
        if not self.pi.connected:
            print("Failed to connect to pigpio!")
            return

        Reward_LED_PIN = 21
        Reward_PIN = 27
        BeamBreak_PIN = 4
        Punishment_LED_PIN = 17
        Buzzer_PIN = 16

        self.peripherals = {
            'reward_led': LED(self.pi, Reward_LED_PIN, brightness=140),
            'reward':     Reward(self.pi, Reward_PIN),
            'beam_break': BeamBreak(self.pi, BeamBreak_PIN),
            'punishment_led': LED(self.pi, Punishment_LED_PIN, brightness=255),
            'buzzer': Buzzer(self.pi, Buzzer_PIN)
        }
        # self.trainer = None
        #default_board_map = {"M0_0": "/dev/ttyACM0", "M0_1": "/dev/ttyACM1"}
        #self.trainer = Main.MultiPhaseTraining(self.pi, self.peripherals, default_board_map)
        #self.trainer.open_realtime_csv("FullSession")

        self.camera = Camera(camera_device="/dev/video0")

    def set_iti_duration(self, iti_duration):
        if isinstance(iti_duration, int) and iti_duration > 0:
            self.iti_duration = iti_duration
            print(f"ITI Duration set to: {self.iti_duration} seconds")
            self.save_to_config("iti_duration", self.iti_duration)
        else:
            print("Invalid ITI Duration")

    def set_seq_csv_dir(self, seq_csv_dir):
        if os.path.isdir(seq_csv_dir):
            self.seq_csv_dir = seq_csv_dir
            print(f"Seq CSV directory set to: {self.seq_csv_dir}")
            self.save_to_config("seq_csv_dir", self.seq_csv_dir)
        else:
            print("Invalid Sequence directory")

    def set_seq_csv_file(self, seq_csv_file):
        if os.path.isfile(os.path.join(self.seq_csv_dir, seq_csv_file)):
            self.seq_csv_file = seq_csv_file
            print(f"Seq CSV file set to: {self.seq_csv_file}")
            self.save_to_config("seq_csv_file", self.seq_csv_file)
        else:
            print("Invalid Sequence CSV file entered.")

    def set_video_dir(self, video_dir):
        if os.path.isdir(video_dir):
            self.video_dir = video_dir
            print(f"Video directory set to: {self.video_dir}")
            self.save_to_config("video_dir", self.video_dir)
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
            self.save_to_config("phase_name", phase_name)
        else:
            print("No Phase name entered.")

    def set_rodent_name(self, rodent_name):
        if rodent_name:
            self.rodent_name = rodent_name
            print(f"Rodent name set to: {self.rodent_name}")
            self.save_to_config("rodent_name", rodent_name)
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
        boards = m0_devices.discover_m0_boards()
        if boards:
            print("Discovered boards:")
            for bid, dev in boards.items():
                print(f" - {bid} => {dev}")
            self.trainer = Main.MultiPhaseTraining(self.pi, self.peripherals, boards)
            print("Trainer updated with discovered boards.")
            self.trainer.open_realtime_csv("FullSession_ReDiscovered")
        else:
            print("No M0 boards found.")