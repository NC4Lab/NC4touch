from Chamber import Chamber
from datetime import datetime
import csv

# Session class
class Session:
    def __init__(self):
        # Initialize chamber
        self.chamber = Chamber()
        self.chamber.initialize()

        # Initialize variables
        self.rodent_name = None
        # Find current date in YYYYMMDD format
        self.session_name = None
        self.session_start_time = None
        self.session_end_time = None
        self.num_trials = 0
        self.current_trial = 0
        self.current_trial_start_time = None
        self.trial_config = {}          # Dictionary to hold trial configurations

        self.iti_duration = 10

        self.data_directory = None
        self.data_writer = None
        self.data_filename = None
        self.data_file = None

    def open_data_file(self):
        """
        Opens a data file for the current session.
        The filename is based on the current date and the rodent's name.
        """
        if self.rodent_name is None:
            raise ValueError("Rodent name must be set before opening data file.")
        
        if self.data_directory is None:
            raise ValueError("Data directory must be set before opening data file.")
        
        date_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.data_filename = f"{self.data_directory}/{self.current_date}_{self.rodent_name}_{date_str}.csv"
        
        print(f"Opening data file: {self.data_filename}")
        
        # Open the data file for writing
        self.data_file = open(self.data_filename, "w", newline="")
        self.data_writer = csv.DictWriter(self.data_file, fieldnames=["timestamp", "event", "data"])
        self.data_writer.writeheader()
        self.data_file.flush()

        self.session_start_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        print(f"Session started at: {self.session_start_time}")
        self.write_data_row("session_start", [])

    def write_data_row(self, event, data):
        """
        Writes a single row to the data file and flushes immediately.
        """
        if self.data_writer:
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            row_data = {
                "timestamp": timestamp,
                "event": event,
                "data": data
            }
            self.data_writer.writerow(row_data)
            self.data_file.flush()
        else:
            raise ValueError("Data writer is not initialized.")

    def close_data_file(self):
        """
        Closes the data file for the current session.
        """
        if self.data_file:
            self.data_file.close()
            self.data_file = None
            print(f"Data file closed: {self.data_filename}")
        else:
            raise ValueError("Data file is not open.")
    
    def finalize_session(self):
        """
        Finalizes the session by closing the data file and updating the session end time.
        """
        self.session_end_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        print(f"Session ended at: {self.session_end_time}")
        self.write_data_row("session_end", [])
        self.close_data_file()
    

class Habituation(Session):
    def __init__(self, params=dict()):
        super().__init__()
        self.params = params
        self.session_name = "Habituation"
        self.num_trials = params.get("num_trials", 0)
        self.rodent_name = params.get("rodent_name", "Rodent")
        self.data_directory = params.get("data_directory", ".")
        self.iti_duration = params.get("iti_duration", 10)
        self.trial_config = params.get("trial_config", {})
        
        self.current_trial = 0
        self.current_trial_start_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        
        for 