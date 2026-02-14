#!/usr/bin/env python3

import time
import csv
import queue
from datetime import datetime

from PyQt5.QtWidgets import QApplication
from m0_devices import M0Device, discover_m0_boards


class MultiPhaseTraining:
    """
    Orchestrates phases for rodent training using M0 boards for visual stimuli,
    and pigpio-based hardware for reward, LED, beam break, etc.
    """

    def __init__(self, pi, peripherals, m0_ports):
        """
        pi          : pigpio instance
        peripherals : dict of hardware objects (reward, reward_led, beam_break, etc.)
        m0_ports    : dict, e.g. {"M0_0": "/dev/ttyACM0", "M0_1": "/dev/ttyACM1"}
        """
        self.pi = pi
        self.peripherals = peripherals
        self.m0_ports = m0_ports
        self.iti_duration = 10  # Default ITI; can be updated from the GUI

        self.is_session_active = False
        self.session_start_time = None
        self.session_end_time = None

        self.current_phase = "N/A"

        # M0 devices
        self.m0_devices = {}
        for m0_id, port in self.m0_ports.items():
            dev = M0Device(m0_id, port)
            self.m0_devices[m0_id] = dev

        # In-memory trial data + persistent CSV tracking
        self.trial_data = []
        self.csv_file = None
        self.csv_writer = None
        self.csv_filename = None

        self.rodent_id = None

    def _init_csv_fields(self):
        return [
            "Training Stage", "ID", "TrialNumber",
            "M0_0", "M0_1", "M0_2",
            "touched_m0", "Choice",
            "InitiationTime", "StartTraining", "EndTraining", "Reward"
        ]

    ## [PERSISTENT CSV SESSION]
    def open_realtime_csv(self, phase_name="FullSession"):
        """
        Opens a persistent CSV file for the entire session.
        Call this once (right after the Trainer is created) so that all trial rows
        are appended to the same file.
        """
        if self.csv_file is None:
            date_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            self.csv_filename = f"{date_str}_{phase_name}.csv"
            print(f"Opening persistent CSV file: {self.csv_filename}")

            self.csv_file = open(self.csv_filename, "w", newline="")
            fieldnames = self._init_csv_fields()
            self.csv_writer = csv.DictWriter(self.csv_file, fieldnames=fieldnames)
            self.csv_writer.writeheader()
            self.csv_file.flush()

            self.session_start_time = datetime.now().strftime("%H:%M:%S")
        else:
            print(f"Persistent CSV already open: {self.csv_filename}")

    def _write_realtime_csv_row(self, row_data):
        """
        Writes a single row to the persistent CSV file and flushes immediately.
        """
        row_data["Training Stage"] = self.current_phase if self.current_phase else "N/A"
        if self.csv_writer:
            self.csv_writer.writerow(row_data)
            self.csv_file.flush()

    def close_realtime_csv(self):
        """
        Closes the persistent CSV file.
        This should be called on GUI close or when ending the session.
        """
        if self.csv_file:
            self.session_end_time = datetime.now().strftime("%H:%M:%S")
            print(f"Closing persistent CSV file: {self.csv_filename}")
            self.csv_file.close()
            self.csv_file = None
            self.csv_writer = None
            self.csv_filename = None

    def finalize_training_timestamp(self):
    # Record the training finish timestamp
        self.session_end_time = datetime.now().strftime("%H:%M:%S")
        if self.trial_data:
            last_row = self.trial_data[-1]
            last_row["EndTraining"] = self.session_end_time
            self._write_realtime_csv_row(last_row)
        print(f"Training finished at {self.session_end_time}.")


    def export_results_csv(self, filename):
        """
        Exports the in-memory trial data to a new CSV file if needed.
        (This is separate from the persistent CSV.)
        """
        if not self.trial_data:
            print("No trial data to export.")
            return
        fieldnames = self._init_csv_fields()
        with open(filename, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in self.trial_data:
                # Ensure that each exported row has the training stage (if not already set)
                if "Training Stage" not in row:
                    row["Training Stage"] = self.current_phase if self.current_phase else "N/A"
                writer.writerow(row)
        print(f"Trial data exported to {filename}.")

    def flush_message_queues(self):
        """Flush out any remaining messages in each M0 device's message queue."""
        for dev in self.m0_devices.values():
            while not dev.message_queue.empty():
                try:
                    dev.message_queue.get_nowait()
                except queue.Empty:
                    break

    def stop_session(self):
        """
        Stop the current training session WITHOUT closing the persistent CSV file.
        When called manually, this also updates the EndTraining timestamp in the CSV.
        """
        if self.is_session_active:
            print("Forcing session to stop.")
            self.is_session_active = False
            # Record the manual stop time in the EndTraining column.
            self.finalize_training_timestamp()

        # Flush message queues so that old events do not interfere with the next phase.
        self.flush_message_queues()
        
        # Optionally, clear trial data if you want a fresh start for the next phase.
        # self.trial_data.clear()
        
        # Turn screens black (but keep ports open)
        for m0_id in self.m0_ports:
            self.send_m0_command(m0_id, "BLACK")
        
        # Deactivate peripherals
        self.peripherals['reward_led'].deactivate()
        self.peripherals['reward'].stop_reward_dispense()
        self.peripherals['beam_break'].deactivate_beam_break()
        
        print("Session stopped and EndTraining timestamp logged.")


    def stop_all_m0(self):
        """
        If you REALLY want to kill the M0 read threads & close ports, call this.
        Typically used only at final shutdown (GUI close).
        """
        for dev in self.m0_devices.values():
            dev.stop()

    def send_m0_command(self, m0_id, command):
        if m0_id not in self.m0_devices:
            print(f"Error: no M0Device for {m0_id}.")
            return
        self.m0_devices[m0_id].send_command(command)

    def get_counts(self):
        correct = 0
        incorrect = 0
        no_touch = 0
        for row in self.trial_data:
            r = row.get("Choice", "")
            if r == "correct":
                correct += 1
            elif r == "no_touch":
                no_touch += 1
            else:
                incorrect += 1
        total = len(self.trial_data)
        return correct, incorrect, no_touch, total
    

    



    # --------------------- Example Phases ---------------------

    def Habituation(self):
        print("Starting Habituation.")
        self.is_session_active = True

        AUTO_ACTIVATION_LIMIT = 30
        self.automatic_activation_count = 0

        from PyQt5.QtWidgets import QApplication

        try:
            while self.automatic_activation_count < AUTO_ACTIVATION_LIMIT:
                QApplication.processEvents()
                if not self.is_session_active:
                    break

                trial_num = self.automatic_activation_count + 1
                trial_start_time = datetime.now().strftime("%H:%M:%S")
                print(f"\n=== Trial {trial_num}: M0_0 -> N/A, M0_1 -> N/A ===")

                # Large reward style with an ITI defined by self.iti_duration
                reward_time = self._large_reward_habituation(pump_secs=3.5, iti_duration=self.iti_duration)

                row_data = {
                    "ID": self.rodent_id or "UNKNOWN",
                    "TrialNumber": trial_num,
                    "M0_0": "N/A",
                    "M0_1": "N/A",
                    "M0_2": "N/A",
                    "touched_m0": "N/A",
                    "Choice": "N/A",
                    "InitiationTime": "N/A",
                    "StartTraining": self.session_start_time or "",
                    "EndTraining": "",
                    "Reward": reward_time if reward_time else ""
                }
                self._write_realtime_csv_row(row_data)
                self.trial_data.append(row_data)

                self.automatic_activation_count += 1

            print("Habituation training finished.")

        except KeyboardInterrupt:
            print("Habituation interrupted by user.")
        finally:
            if self.trial_data:
                self.finalize_training_timestamp()
            self.is_session_active = False
            for m0_id in self.m0_ports:
                self.send_m0_command(m0_id, "BLACK")
            self.peripherals['reward_led'].deactivate()
            self.peripherals['reward'].stop_reward_dispense()
            self.peripherals['beam_break'].deactivate_beam_break()
            print(f"Habituation phase finished at {self.session_end_time}.")

    def _large_reward_habituation(self, pump_secs=3.5, iti_duration=10):
        if not self.is_session_active:
            return None

        from PyQt5.QtWidgets import QApplication

        reward_time = datetime.now().strftime("%H:%M:%S")
        print(f"Large_reward_habituation: pumping for {pump_secs} second(s).")

        beam_broken = False
        self.peripherals['beam_break'].deactivate_beam_break()
        self.peripherals['reward_led'].activate()
        self.peripherals['reward'].dispense_reward()
        start_t = time.time()

        while (time.time() - start_t) < pump_secs:
            QApplication.processEvents()
            if not self.is_session_active:
                break
            self.peripherals['beam_break'].activate_beam_break()
            if self.peripherals['beam_break'].sensor_state == 0 and not beam_broken:
                beam_broken = True
                print("Beam broken during reward dispense.")
                self.peripherals['reward_led'].deactivate()
            time.sleep(0.01)

        self.peripherals['reward'].stop_reward_dispense()

        if not beam_broken and self.is_session_active:
            print("Waiting for beam to be broken.")
            while self.peripherals['beam_break'].sensor_state != 0:
                QApplication.processEvents()
                if not self.is_session_active:
                    break
                self.peripherals['beam_break'].activate_beam_break()
                time.sleep(0.01)
            if self.peripherals['beam_break'].sensor_state == 0:
                print("Beam broken.")
            while self.peripherals['beam_break'].sensor_state == 0 and self.is_session_active:
                QApplication.processEvents()
                self.peripherals['beam_break'].activate_beam_break()
                time.sleep(0.01)

        self.peripherals['reward_led'].deactivate()
        self.peripherals['beam_break'].deactivate_beam_break()
        print("Beam break deactivated. Reward finished.")

        if self.is_session_active:
            print(f"[Habituation] Starting ITI for {iti_duration}s.")
            # Ensure reward LED is off before starting ITI
            self.peripherals['reward_led'].deactivate()
            # Wait a brief moment to ensure LED has turned off
            time.sleep(0.5)
            iti_start_time = time.time()
            while (time.time() - iti_start_time) < iti_duration and self.is_session_active:
                QApplication.processEvents()
                self.peripherals['beam_break'].activate_beam_break()
                time.sleep(0.01)
            while self.peripherals['beam_break'].sensor_state == 0 and self.is_session_active:
                QApplication.processEvents()
                print("Beam still broken at end of ITI. Adding 1s delay.")
                time.sleep(1)
                self.peripherals['beam_break'].activate_beam_break()
            print("ITI completed.")

        return reward_time

    def initial_touch_phase(self, csv_file_path):
        print("Starting Initial Touch.")



        self.is_session_active = True

        trials = self.read_csv(csv_file_path)
        print("Dispensing free reward.")
        _ = self.large_reward(3.0)
        if trials:
            img0_first, img1_first = trials[0]
            self.send_m0_command("M0_0", f"IMG:{img0_first}")
            self.send_m0_command("M0_1", f"IMG:{img1_first}")

        for i, (img0, img1) in enumerate(trials, start=1):
            if not self.is_session_active:
                break

            trial_start_time = datetime.now().strftime("%H:%M:%S")
            print(f"\n=== Trial {i}: M0_0 -> {img0}, M0_1 -> {img1} ===")
            self.send_m0_command("M0_0", "SHOW")
            self.send_m0_command("M0_1", "SHOW")

            touched_m0, touched_image = self.wait_for_touch(img0, img1, timeout=120)

            if not touched_m0:
                print("No touch => skipping reward")
                self.send_m0_command("M0_0", "BLACK")
                self.send_m0_command("M0_1", "BLACK")
                row_data = {
                    "ID": self.rodent_id or "UNKNOWN",
                    "TrialNumber": i,
                    "M0_0": img0,
                    "M0_1": img1,
                    "M0_2": "",
                    "touched_m0": None,
                    "Choice": "no_touch",
                    "InitiationTime": trial_start_time,
                    "StartTraining": self.session_start_time or "",
                    "EndTraining": "",
                    "Reward": ""
                }
                self._write_realtime_csv_row(row_data)
                self.trial_data.append(row_data)
                self._fixed_iti()  # Use the GUI-defined ITI duration
                continue

            print(f"{touched_m0} touched => {touched_image}. BLACKing screens.")
            self.send_m0_command("M0_0", "BLACK")
            self.send_m0_command("M0_1", "BLACK")

            if touched_image == "A01":
                choice_result = "correct"
                print("Correct choice")
                reward_time = self.large_reward(3.0)
            else:
                choice_result = "incorrect"
                print("Incorrect choice")
                reward_time = self.large_reward(1.5)

            row_data = {
                "ID": self.rodent_id or "UNKNOWN",
                "TrialNumber": i,
                "M0_0": img0,
                "M0_1": img1,
                "M0_2": "N/A",
                "touched_m0": touched_m0,
                "Choice": choice_result,
                "InitiationTime": trial_start_time,
                "StartTraining": self.session_start_time or "",
                "EndTraining": "",
                "Reward": reward_time if reward_time else ""
            }
            self._write_realtime_csv_row(row_data)
            self.trial_data.append(row_data)
            self._fixed_iti()  # Use the GUI-defined ITI duration

            if i < len(trials):
                next_img0, next_img1 = trials[i]
                print(f"Preloading images for next trial {i+1} => {next_img0}, {next_img1}")
                self.send_m0_command("M0_0", f"IMG:{next_img0}")
                self.send_m0_command("M0_1", f"IMG:{next_img1}")

        self.is_session_active = False
        for m0_id in self.m0_ports:
            self.send_m0_command(m0_id, "BLACK")
        print("Initial Touch finished.")

        for dev in self.m0_devices.values():
            dev._attempt_reopen()
            time.sleep(0.5)

    def _fixed_iti(self, iti_duration=None):
        if not self.is_session_active:
            return
        if iti_duration is None:
            iti_duration = self.iti_duration
        # Ensure the reward LED is off before starting ITI.
        self.peripherals['reward_led'].deactivate()
        # Wait a short delay after LED turns off.
        time.sleep(0.5)
        print(f"Starting ITI for {iti_duration}s.")
        start_time = time.time()
        while (time.time() - start_time) < iti_duration and self.is_session_active:
            self.peripherals['beam_break'].activate_beam_break()
            time.sleep(0.01)
        print("ITI completed.")



    def must_touch_phase(self, csv_file_path):
        """
        Must Touch Phase:
        - Rodent must press the 'A01' image to get a reward.
        - Other touches are ignored (no punishment, no corrections).
        - After 300s without A01, the trial is considered 'no_touch'.
        - An ITI is added at the end of each trial EXCEPT for the first trial (no ITI for Trial 1).
        - Stopping the session exits immediately.
        """
        print("Starting Must Touch.")




        self.is_session_active = True
        trials = self.read_csv(csv_file_path)
        if not trials:
            print("No trials found in CSV.")
            return

        from PyQt5.QtWidgets import QApplication

        try:
            # -------------------- Trial 1 --------------------
            # Preload images for Trial 1 immediately after phase starts
            img0_first, img1_first = trials[0]
            print("Preloading images for Trial 1 (pre-free reward phase)...")
            self.send_m0_command("M0_0", f"IMG:{img0_first}")
            self.send_m0_command("M0_1", f"IMG:{img1_first}")

            # Dispense free reward
            print("Dispensing free reward.")
            _ = self.large_reward(3.0)

            # NO ITI for Trial 1 => immediately show images
            print("Showing images for Trial 1 (no ITI).")
            self.send_m0_command("M0_0", "SHOW")
            self.send_m0_command("M0_1", "SHOW")

            # Wait up to 300s for a correct (A01) touch
            trial_start_time = datetime.now().strftime("%H:%M:%S")
            print(f"\nTrial 1: M0_0 -> {img0_first}, M0_1 -> {img1_first}")
            start_t = time.time()
            touched_m0 = None
            touched_image = None
            correct_choice = False

            while (time.time() - start_t) < 300 and self.is_session_active and not correct_choice:
                QApplication.processEvents()
                sub_timeout = 1.0
                sub_start = time.time()
                found_touch = False
                while (time.time() - sub_start) < sub_timeout and not found_touch and self.is_session_active:
                    QApplication.processEvents()
                    for m0_id, device in self.m0_devices.items():
                        try:
                            m_id, line = device.message_queue.get(timeout=0.02)
                            if line.startswith("TOUCH:"):
                                found_touch = True
                                if m_id == "M0_0":
                                    touched_m0 = "M0_0"
                                    touched_image = img0_first
                                else:
                                    touched_m0 = "M0_1"
                                    touched_image = img1_first
                                break
                        except queue.Empty:
                            pass
                    time.sleep(0.01)
                if not self.is_session_active:
                    break
                if found_touch:
                    if touched_image == "A01":
                        correct_choice = True
                    else:
                        # Other touches are simply ignored.
                        print(f"{touched_m0} touched => {touched_image}. Ignoring, must press A01.")
                        touched_m0 = None
                        touched_image = None

            if not self.is_session_active:
                return

            if correct_choice:
                # Correct => reward
                print(f"{touched_m0} touched => {touched_image} (correct).")
                print("Correct choice")
                print("Black out both screens and dispense reward.")
                self.send_m0_command("M0_0", "BLACK")
                self.send_m0_command("M0_1", "BLACK")
                reward_time = self.large_reward(3.0)
                row_data = {
                    "ID": self.rodent_id or "UNKNOWN",
                    "TrialNumber": 1,
                    "M0_0": img0_first,
                    "M0_1": img1_first,
                    "M0_2": "N/A",
                    "touched_m0": touched_m0,
                    "Choice": "correct",
                    "InitiationTime": "N/A",
                    "StartTraining": self.session_start_time or "",
                    "EndTraining": "",
                    "Reward": reward_time if reward_time else ""
                }
                self._write_realtime_csv_row(row_data)
                self.trial_data.append(row_data)
            else:
                # No correct touch => no reward
                print("No touch => skipping reward.")
                self.send_m0_command("M0_0", "BLACK")
                self.send_m0_command("M0_1", "BLACK")
                row_data = {
                    "ID": self.rodent_id or "UNKNOWN",
                    "TrialNumber": 1,
                    "M0_0": img0_first,
                    "M0_1": img1_first,
                    "M0_2": "",
                    "touched_m0": None,
                    "Choice": "no_touch",
                    "InitiationTime": "N/A",
                    "StartTraining": self.session_start_time or "",
                    "EndTraining": "",
                    "Reward": ""
                }
                self._write_realtime_csv_row(row_data)
                self.trial_data.append(row_data)

            # -------------------- Subsequent Trials --------------------
            for i in range(1, len(trials)):
                if not self.is_session_active:
                    break

                img0, img1 = trials[i]

                # Preload images BEFORE ITI
                print(f"\nPreloading images for Trial {i+1} (pre-ITI)...")
                self.send_m0_command("M0_0", f"IMG:{img0}")
                self.send_m0_command("M0_1", f"IMG:{img1}")

                # Run ITI
                print(f"--- ITI before Trial {i+1} ---")
                self._fixed_iti()
                if not self.is_session_active:
                    break

                # Show images immediately after ITI
                self.send_m0_command("M0_0", "SHOW")
                self.send_m0_command("M0_1", "SHOW")

                trial_start_time = datetime.now().strftime("%H:%M:%S")
                print(f"=== Trial {i+1}: M0_0 -> {img0}, M0_1 -> {img1} ===")

                start_t = time.time()
                touched_m0 = None
                touched_image = None
                correct_choice = False

                # Wait up to 300s for correct (A01) touch
                while (time.time() - start_t) < 300 and self.is_session_active and not correct_choice:
                    QApplication.processEvents()
                    sub_timeout = 1.0
                    sub_start = time.time()
                    found_touch = False
                    while (time.time() - sub_start) < sub_timeout and not found_touch and self.is_session_active:
                        QApplication.processEvents()
                        for m0_id, device in self.m0_devices.items():
                            try:
                                m_id, line = device.message_queue.get(timeout=0.02)
                                if line.startswith("TOUCH:"):
                                    found_touch = True
                                    if m_id == "M0_0":
                                        touched_m0 = "M0_0"
                                        touched_image = img0
                                    else:
                                        touched_m0 = "M0_1"
                                        touched_image = img1
                                    break
                            except queue.Empty:
                                pass
                        time.sleep(0.01)
                    if not self.is_session_active:
                        break
                    if found_touch:
                        if touched_image == "A01":
                            correct_choice = True
                        else:
                            print("Incorrect choice")
                            print(f"{touched_m0} touched => {touched_image}. Ignoring, must press A01.")
                            touched_m0 = None
                            touched_image = None

                if not self.is_session_active:
                    break

                if correct_choice:
                    print(f"{touched_m0} touched => {touched_image} (correct).")
                    print("Correct choice")
                    print("Black out both screens and dispense reward.")
                    self.send_m0_command("M0_0", "BLACK")
                    self.send_m0_command("M0_1", "BLACK")
                    reward_time = self.large_reward(3.0)
                    row_data = {
                        "ID": self.rodent_id or "UNKNOWN",
                        "TrialNumber": i+1,
                        "M0_0": img0,
                        "M0_1": img1,
                        "M0_2": "N/A",
                        "touched_m0": touched_m0,
                        "Choice": "correct",
                        "InitiationTime": "N/A",
                        "StartTraining": self.session_start_time or "",
                        "EndTraining": "",
                        "Reward": reward_time if reward_time else ""
                    }
                    self._write_realtime_csv_row(row_data)
                    self.trial_data.append(row_data)
                else:
                    print("No touch => skipping reward.")
                    self.send_m0_command("M0_0", "BLACK")
                    self.send_m0_command("M0_1", "BLACK")
                    row_data = {
                        "ID": self.rodent_id or "UNKNOWN",
                        "TrialNumber": i+1,
                        "M0_0": img0,
                        "M0_1": img1,
                        "M0_2": "",
                        "touched_m0": None,
                        "Choice": "no_touch",
                        "InitiationTime": "N/A",
                        "StartTraining": self.session_start_time or "",
                        "EndTraining": "",
                        "Reward": ""
                    }
                    self._write_realtime_csv_row(row_data)
                    self.trial_data.append(row_data)

                # Preload images for next trial if available
                if i < len(trials) - 1 and self.is_session_active:
                    next_img0, next_img1 = trials[i+1]
                    print(f"Preloading images for next trial {i+2} (pre-ITI)...")
                    self.send_m0_command("M0_0", f"IMG:{next_img0}")
                    self.send_m0_command("M0_1", f"IMG:{next_img1}")

        finally:
            self.finalize_training_timestamp()
            self.is_session_active = False
            for m0_id in self.m0_ports:
                self.send_m0_command(m0_id, "BLACK")
            print("Must Touch training stage finished.")

        for dev in self.m0_devices.values():
            dev._attempt_reopen()
            time.sleep(0.5)




    def must_initiate_phase(self, csv_file_path):

        print("Starting Must Initiate.")
        self.is_session_active = True
        trials = self.read_csv(csv_file_path)
        if not trials:
            print("No trials found in CSV.")
            return

        from PyQt5.QtWidgets import QApplication

        # ----- Trial 1 (Free Reward Phase) -----
        img0_first, img1_first = trials[0]
        print("Preloading images for Trial 1 (pre-free reward)...")
        self.send_m0_command("M0_0", f"IMG:{img0_first}")
        self.send_m0_command("M0_1", f"IMG:{img1_first}")
        print("Dispensing free reward.")
        _ = self.large_reward(3.0)
        print("Showing images for Trial 1 (no initiation required).")
        self.send_m0_command("M0_0", "SHOW")
        self.send_m0_command("M0_1", "SHOW")
        trial_start_time = datetime.now().strftime("%H:%M:%S")
        print(f"\nTrial 1: M0_0 -> {img0_first}, M0_1 -> {img1_first}")
        start_t = time.time()
        touched_m0 = None
        touched_image = None
        choice_result = None

        while (time.time() - start_t) < 300 and self.is_session_active and not choice_result:
            QApplication.processEvents()
            sub_timeout = 1.0
            sub_start = time.time()
            found_touch = False
            while (time.time() - sub_start) < sub_timeout and not found_touch and self.is_session_active:
                QApplication.processEvents()
                for m0_id, device in self.m0_devices.items():
                    try:
                        m_id, line = device.message_queue.get(timeout=0.02)
                        if line.startswith("TOUCH:"):
                            found_touch = True
                            if m_id == "M0_0":
                                touched_m0 = "M0_0"
                                touched_image = img0_first
                            else:
                                touched_m0 = "M0_1"
                                touched_image = img1_first
                            break
                    except queue.Empty:
                        pass
                time.sleep(0.01)
            if not self.is_session_active:
                break
            if found_touch:
                if touched_image == "A01":
                    choice_result = "correct"
                    print("Correct choice")
                    break
                elif touched_image == "B01":
                    print(f"{touched_m0} touched => {touched_image}. Ignoring (must press A01).")
                    print("Incorrect choice")
                    touched_m0 = None
                    touched_image = None

        if not self.is_session_active:
            return
        if not choice_result:
            choice_result = "no_touch"
            print("No touch => skipping reward for Trial 1.")
            self.send_m0_command("M0_0", "BLACK")
            self.send_m0_command("M0_1", "BLACK")
            row_data = {
                "ID": self.rodent_id or "UNKNOWN",
                "TrialNumber": 1,
                "M0_0": img0_first,
                "M0_1": img1_first,
                "M0_2": "",
                "touched_m0": None,
                "Choice": "no_touch",
                "InitiationTime": trial_start_time,
                "StartTraining": self.session_start_time or "",
                "EndTraining": "",
                "Reward": ""
            }
            self._write_realtime_csv_row(row_data)
            self.trial_data.append(row_data)
        else:
            print(f"{touched_m0} touched => {touched_image} (correct).")
            self.send_m0_command("M0_0", "BLACK")
            self.send_m0_command("M0_1", "BLACK")
            reward_time = self.large_reward(3.0)
            row_data = {
                "ID": self.rodent_id or "UNKNOWN",
                "TrialNumber": 1,
                "M0_0": img0_first,
                "M0_1": img1_first,
                "M0_2": "N/A",
                "touched_m0": touched_m0,
                "Choice": "correct",
                "InitiationTime": trial_start_time,
                "StartTraining": self.session_start_time or "",
                "EndTraining": "",
                "Reward": reward_time if reward_time else ""
            }
            self._write_realtime_csv_row(row_data)
            self.trial_data.append(row_data)

        # ----- Subsequent Trials -----
        for i in range(1, len(trials)):
            if not self.is_session_active:
                break

            img0, img1 = trials[i]
            print(f"\nPreloading images for Trial {i+1} (pre-ITI)...")
            self.send_m0_command("M0_0", f"IMG:{img0}")
            self.send_m0_command("M0_1", f"IMG:{img1}")
            print(f"--- ITI before Trial {i+1} ---")
            self._fixed_iti()
            if not self.is_session_active:
                break
            print(f"--- Waiting for rodent to initiate Trial {i+1} ---")
            if not self.wait_for_trial_initiation():
                print(f"Session stopped during initiation for trial {i+1}.")
                break

            self.send_m0_command("M0_0", "SHOW")
            self.send_m0_command("M0_1", "SHOW")
            trial_start_time = datetime.now().strftime("%H:%M:%S")
            print(f"=== Trial {i+1}: M0_0 -> {img0}, M0_1 -> {img1} ===")
            start_t = time.time()
            touched_m0 = None
            touched_image = None
            correct_choice = False

            while (time.time() - start_t) < 300 and self.is_session_active and not correct_choice:
                QApplication.processEvents()
                sub_timeout = 1.0
                sub_start = time.time()
                found_touch = False
                while (time.time() - sub_start) < sub_timeout and not found_touch and self.is_session_active:
                    QApplication.processEvents()
                    for m0_id, device in self.m0_devices.items():
                        try:
                            m_id, line = device.message_queue.get(timeout=0.02)
                            if line.startswith("TOUCH:"):
                                found_touch = True
                                if m_id == "M0_0":
                                    touched_m0 = "M0_0"
                                    touched_image = img0
                                else:
                                    touched_m0 = "M0_1"
                                    touched_image = img1
                                break
                        except queue.Empty:
                            pass
                    time.sleep(0.01)
                if not self.is_session_active:
                    break
                if found_touch:
                    if touched_image == "A01":
                        correct_choice = True
                        print("Correct choice")
            
                    elif touched_image == "B01":
                        print(f"{touched_m0} touched => {touched_image}. Ignoring (must press A01).")
                        print("Incorrect choice")
                        touched_m0 = None
                        touched_image = None
            if not self.is_session_active:
                break
            if not correct_choice:
                print("No correct touch (A01) within 300s => skipping reward.")
                self.send_m0_command("M0_0", "BLACK")
                self.send_m0_command("M0_1", "BLACK")
                row_data = {
                    "ID": self.rodent_id or "UNKNOWN",
                    "TrialNumber": i+1,
                    "M0_0": img0,
                    "M0_1": img1,
                    "M0_2": "",
                    "touched_m0": None,
                    "Choice": "no_touch",
                    "InitiationTime": trial_start_time,
                    "StartTraining": self.session_start_time or "",
                    "EndTraining": "",
                    "Reward": ""
                }
                self._write_realtime_csv_row(row_data)
                self.trial_data.append(row_data)
            else:
                print(f"{touched_m0} touched => {touched_image} (correct).")
                self.send_m0_command("M0_0", "BLACK")
                self.send_m0_command("M0_1", "BLACK")
                reward_time = self.large_reward(3.0)
                row_data = {
                    "ID": self.rodent_id or "UNKNOWN",
                    "TrialNumber": i+1,
                    "M0_0": img0,
                    "M0_1": img1,
                    "M0_2": "N/A",
                    "touched_m0": touched_m0,
                    "Choice": "correct",
                    "InitiationTime": trial_start_time,
                    "StartTraining": self.session_start_time or "",
                    "EndTraining": "",
                    "Reward": reward_time if reward_time else ""
                }
                self._write_realtime_csv_row(row_data)
                self.trial_data.append(row_data)
            # ITI after processing each trial
            self._fixed_iti()
            if i < len(trials):
                next_img0, next_img1 = trials[i]
                print(f"Preloading images for next trial {i+1} => {next_img0}, {next_img1}")
                self.send_m0_command("M0_0", f"IMG:{next_img0}")
                self.send_m0_command("M0_1", f"IMG:{next_img1}")
        self.is_session_active = False
        for m0_id in self.m0_ports:
            self.send_m0_command(m0_id, "BLACK")
        print("Must Initiate training stage finished.")
        for dev in self.m0_devices.values():
            dev._attempt_reopen()
            time.sleep(0.5)





    def punish_incorrect_phase(self, csv_file_path): 
        print("Starting Punish Incorrect.")

        for dev in self.m0_devices.values():
            while not dev.message_queue.empty():
                try:
                    dev.message_queue.get_nowait()
                except queue.Empty:
                    break

        self.is_session_active = True
        trials = self.read_csv(csv_file_path)
        if not trials:
            print("No trials found in CSV.")
            return

        from PyQt5.QtWidgets import QApplication

        try:
            # ---------------------- TRIAL #1 (Free Reward) ----------------------
            # Preload images for trial 1 immediately after starting the phase.
            img0_first, img1_first = trials[0]
            print("Preloading images for Trial 1 (pre-free reward)...")
            self.send_m0_command("M0_0", f"IMG:{img0_first}")
            self.send_m0_command("M0_1", f"IMG:{img1_first}")

            # Now dispense free reward.
            print("Dispensing free reward.")
            _ = self.large_reward(4.0)

            # >>> FLUSH leftover messages BEFORE starting Trial 1 <<<
            for dev in self.m0_devices.values():
                while not dev.message_queue.empty():
                    try:
                        dev.message_queue.get_nowait()
                    except queue.Empty:
                        break

            # Immediately display images (no initiation required for trial 1).
            self.send_m0_command("M0_0", "SHOW")
            self.send_m0_command("M0_1", "SHOW")

            trial_start_time = datetime.now().strftime("%H:%M:%S")
            print(f"\nTrial 1: M0_0 -> {img0_first}, M0_1 -> {img1_first}")

            start_t = time.time()
            touched_m0 = None
            touched_image = None
            choice_result = None

            while (time.time() - start_t) < 300 and self.is_session_active and not choice_result:
                QApplication.processEvents()
                sub_timeout = 1.0
                sub_start = time.time()
                found_touch = False

                while ((time.time() - sub_start) < sub_timeout and not found_touch and self.is_session_active):
                    QApplication.processEvents()
                    for m0_id, device in self.m0_devices.items():
                        try:
                            m_id, line = device.message_queue.get(timeout=0.02)
                            if line.startswith("TOUCH:"):
                                found_touch = True
                                if m_id == "M0_0":
                                    touched_m0 = "M0_0"
                                    touched_image = img0_first
                                else:
                                    touched_m0 = "M0_1"
                                    touched_image = img1_first
                                break
                        except queue.Empty:
                            pass
                    time.sleep(0.01)

                if found_touch:
                    if touched_image == "A01":
                        choice_result = "correct"
                        print("Correct choice")
                        break
                    elif touched_image == "B01":
                        choice_result = "incorrect"
                        print("Incorrect choice")
                        break

            if not choice_result:
                choice_result = "no_touch"
                print("No touch => skipping reward")

            if choice_result == "correct":
                self.send_m0_command("M0_0", "BLACK")
                self.send_m0_command("M0_1", "BLACK")
                reward_time = self.large_reward(3.0)
            elif choice_result == "incorrect":
                self.send_m0_command("M0_0", "BLACK")
                self.send_m0_command("M0_1", "BLACK")
                self.peripherals['punishment_led'].activate()
                self.peripherals['buzzer'].activate()
                start_punish = time.time()
                buzzer_off = False
                while (time.time() - start_punish) < 5 and self.is_session_active:
                    QApplication.processEvents()
                    elapsed = time.time() - start_punish
                    if (not buzzer_off) and (elapsed >= 0.5):
                        self.peripherals['buzzer'].deactivate()
                        buzzer_off = True
                    time.sleep(0.01)
                self.peripherals['punishment_led'].deactivate()
                reward_time = ""
            else:
                self.send_m0_command("M0_0", "BLACK")
                self.send_m0_command("M0_1", "BLACK")
                reward_time = ""

            row_data = {
                "ID": self.rodent_id or "UNKNOWN",
                "TrialNumber": "1",
                "M0_0": img0_first,
                "M0_1": img1_first,
                "M0_2": "",
                "touched_m0": touched_m0,
                "Choice": choice_result,
                "InitiationTime": trial_start_time,
                "StartTraining": self.session_start_time or "",
                "EndTraining": "",
                "Reward": reward_time if reward_time else ""
            }
            self._write_realtime_csv_row(row_data)
            self.trial_data.append(row_data)


            # ---------------------- SUBSEQUENT TRIALS ----------------------
            for i in range(1, len(trials)):
                if not self.is_session_active:
                    break
                img0, img1 = trials[i]

                print(f"\nPreloading images for Trial {i+1} (pre-ITI)...")
                self.send_m0_command("M0_0", f"IMG:{img0}")
                self.send_m0_command("M0_1", f"IMG:{img1}")

                print(f"--- ITI before Trial {i+1} ---")
                self._fixed_iti()
                if not self.is_session_active:
                    break

                # >>> FLUSH leftover messages BEFORE starting each new trial <<<
                for dev in self.m0_devices.values():
                    while not dev.message_queue.empty():
                        try:
                            dev.message_queue.get_nowait()
                        except queue.Empty:
                            break

                print(f"--- Waiting for rodent to initiate Trial {i+1} ---")
                if not self.wait_for_trial_initiation():
                    print(f"Session stopped during initiation for trial {i+1}.")
                    break

                self.send_m0_command("M0_0", "SHOW")
                self.send_m0_command("M0_1", "SHOW")
                trial_start_time = datetime.now().strftime("%H:%M:%S")
                print(f"=== Trial {i+1}: M0_0 -> {img0}, M0_1 -> {img1} ===")

                start_t = time.time()
                touched_m0 = None
                touched_image = None
                choice_result = None

                while (time.time() - start_t) < 300 and self.is_session_active and not choice_result:
                    QApplication.processEvents()
                    sub_timeout = 1.0
                    sub_start = time.time()
                    found_touch = False

                    while ((time.time() - sub_start) < sub_timeout and not found_touch and self.is_session_active):
                        QApplication.processEvents()
                        for m0_id, device in self.m0_devices.items():
                            try:
                                m_id, line = device.message_queue.get(timeout=0.02)
                                if line.startswith("TOUCH:"):
                                    found_touch = True
                                    if m_id == "M0_0":
                                        touched_m0 = "M0_0"
                                        touched_image = img0
                                    else:
                                        touched_m0 = "M0_1"
                                        touched_image = img1
                                    break
                            except queue.Empty:
                                pass
                        time.sleep(0.01)

                    if found_touch:
                        if touched_image == "A01":
                            choice_result = "correct"
                            print("Correct choice")
                            break
                        elif touched_image == "B01":
                            choice_result = "incorrect"
                            print("Incorrect choice")
                            break

                if not self.is_session_active:
                    break

                if not choice_result:
                    choice_result = "no_touch"
                    print("No touch => skipping reward")

                if choice_result == "correct":
                    self.send_m0_command("M0_0", "BLACK")
                    self.send_m0_command("M0_1", "BLACK")
                    reward_time = self.large_reward(3.0)
                elif choice_result == "incorrect":
                    self.send_m0_command("M0_0", "BLACK")
                    self.send_m0_command("M0_1", "BLACK")
                    self.peripherals['punishment_led'].activate()
                    self.peripherals['buzzer'].activate()
                    start_punish = time.time()
                    buzzer_off = False
                    while (time.time() - start_punish) < 5 and self.is_session_active:
                        QApplication.processEvents()
                        elapsed = time.time() - start_punish
                        if (not buzzer_off) and (elapsed >= 0.5):
                            self.peripherals['buzzer'].deactivate()
                            buzzer_off = True
                        time.sleep(0.01)
                    self.peripherals['punishment_led'].deactivate()
                    reward_time = ""
                else:
                    self.send_m0_command("M0_0", "BLACK")
                    self.send_m0_command("M0_1", "BLACK")
                    reward_time = ""

                row_data = {
                    "ID": self.rodent_id or "UNKNOWN",
                    "TrialNumber": f"{i+1}",
                    "M0_0": img0,
                    "M0_1": img1,
                    "M0_2": "",
                    "touched_m0": touched_m0,
                    "Choice": choice_result,
                    "InitiationTime": trial_start_time,
                    "StartTraining": self.session_start_time or "",
                    "EndTraining": "",
                    "Reward": reward_time
                }
                self._write_realtime_csv_row(row_data)
                self.trial_data.append(row_data)

                # Preload images for next trial if available.
                if i < len(trials) - 1 and self.is_session_active:
                    next_img0, next_img1 = trials[i+1]
                    print(f"Preloading images for next trial {i+2} (pre-ITI)...")
                    self.send_m0_command("M0_0", f"IMG:{next_img0}")
                    self.send_m0_command("M0_1", f"IMG:{next_img1}")

        finally:
            self.finalize_training_timestamp()
            self.is_session_active = False
            for m0_id in self.m0_ports:
                self.send_m0_command(m0_id, "BLACK")
            print(f"Punish Incorrect Phase finished at {self.session_end_time}.")

        for dev in self.m0_devices.values():
            dev._attempt_reopen()
            time.sleep(0.5)


    def simple_discrimination_phase(self, csv_file_path):
        print("Starting Simple Discrimination.")

        for dev in self.m0_devices.values():
            while not dev.message_queue.empty():
                try:
                    dev.message_queue.get_nowait()
                except queue.Empty:
                    break

        self.is_session_active = True
        trials = self.read_csv(csv_file_path)
        if not trials:
            print("No trials found in CSV.")
            return

        from PyQt5.QtWidgets import QApplication

        try:
            trial_index = 0
            # Process each trial (including trial 1) with correction attempts for incorrect responses.
            while trial_index < len(trials) and self.is_session_active:
                # Get current trial stimuli.
                img0, img1 = trials[trial_index]
                correction_count = 0
                trial_completed = False

                while not trial_completed and self.is_session_active:
                    # For Trial 1 first attempt: no initiation required.
                    if trial_index == 0 and correction_count == 0:
                        print("Preloading images for Trial 1 (pre-free reward phase)...")
                        self.send_m0_command("M0_0", f"IMG:{img0}")
                        self.send_m0_command("M0_1", f"IMG:{img1}")
                        print("Dispensing free reward.")
                        _ = self.large_reward(4.0)
                        # Immediately display images.
                        self.send_m0_command("M0_0", "SHOW")
                        self.send_m0_command("M0_1", "SHOW")
                    else:
                        # For any new trial (trial_index > 0) or for correction attempts:
                        print(f"Preloading images for Trial {trial_index+1}{' (correction)' if correction_count > 0 else ''} (pre-ITI)...")
                        self.send_m0_command("M0_0", f"IMG:{img0}")
                        self.send_m0_command("M0_1", f"IMG:{img1}")
                        print(f"--- ITI before Trial {trial_index+1}{' (correction)' if correction_count > 0 else ''} ---")
                        self._fixed_iti()
                        if not self.is_session_active:
                            break
                        print(f"--- Waiting for rodent to initiate Trial {trial_index+1}{' (correction)' if correction_count > 0 else ''} ---")
                        if not self.wait_for_trial_initiation():
                            print(f"Session stopped during initiation for trial {trial_index+1}.")
                            break
                        # Immediately show images after initiation.
                        self.send_m0_command("M0_0", "SHOW")
                        self.send_m0_command("M0_1", "SHOW")

                    # Record initiation time.
                    trial_start_time = datetime.now().strftime("%H:%M:%S")
                    print(f"=== Trial {trial_index+1}{'*' if correction_count > 0 else ''}: M0_0 -> {img0}, M0_1 -> {img1} ===")

                    # Wait for touch response (up to 300 seconds).
                    start_t = time.time()
                    touched_m0 = None
                    touched_image = None
                    choice_result = None

                    while (time.time() - start_t) < 300 and self.is_session_active and not choice_result:
                        QApplication.processEvents()
                        sub_timeout = 1.0
                        sub_start = time.time()
                        found_touch = False

                        while ((time.time() - sub_start) < sub_timeout and not found_touch and self.is_session_active):
                            QApplication.processEvents()
                            for m0_id, device in self.m0_devices.items():
                                try:
                                    m_id, line = device.message_queue.get(timeout=0.02)
                                    if line.startswith("TOUCH:"):
                                        found_touch = True
                                        if m_id == "M0_0":
                                            touched_m0 = "M0_0"
                                            touched_image = img0
                                        else:
                                            touched_m0 = "M0_1"
                                            touched_image = img1
                                        break
                                except queue.Empty:
                                    pass
                            time.sleep(0.01)

                        if found_touch:
                            if touched_image == "A01":
                                choice_result = "correct"
                                print("Correct choice")
                                break
                            elif touched_image == "C01":
                                choice_result = "incorrect"
                                print("Incorrect choice")
                                break

                    if not self.is_session_active:
                        break

                    # If we never got a touch or it didn't match 'E01'/'D01', call it "no_touch".
                    if not choice_result:
                        choice_result = "no_touch"
                        print("No touch => skipping reward")

                    # -------------------- Outcome Handling --------------------
                    if choice_result == "correct":
                        self.send_m0_command("M0_0", "BLACK")
                        self.send_m0_command("M0_1", "BLACK")
                        reward_time = self.large_reward(3.0)

                        row_data = {
                            "ID": self.rodent_id or "UNKNOWN",
                            "TrialNumber": f"{trial_index+1}" if correction_count == 0 else f"{trial_index+1}*",
                            "M0_0": img0,
                            "M0_1": img1,
                            "M0_2": "",
                            "touched_m0": touched_m0,
                            "Choice": choice_result,
                            "InitiationTime": trial_start_time,
                            "StartTraining": self.session_start_time or "",
                            "EndTraining": "",
                            "Reward": reward_time if reward_time else ""
                        }
                        self._write_realtime_csv_row(row_data)
                        self.trial_data.append(row_data)

                        # Flush any leftover messages before next trial
                        for dev in self.m0_devices.values():
                            while not dev.message_queue.empty():
                                try:
                                    dev.message_queue.get_nowait()
                                except queue.Empty:
                                    break

                        trial_completed = True
                        correction_count = 0  # Reset corrections for next trial.

                    elif choice_result == "incorrect":
                        self.send_m0_command("M0_0", "BLACK")
                        self.send_m0_command("M0_1", "BLACK")
                        self.peripherals['punishment_led'].activate()
                        self.peripherals['buzzer'].activate()
                        start_punish = time.time()
                        buzzer_off = False

                        while (time.time() - start_punish) < 5 and self.is_session_active:
                            QApplication.processEvents()
                            elapsed = time.time() - start_punish
                            if (not buzzer_off) and (elapsed >= 0.5):
                                self.peripherals['buzzer'].deactivate()
                                buzzer_off = True
                            time.sleep(0.01)

                        self.peripherals['punishment_led'].deactivate()

                        row_data = {
                            "ID": self.rodent_id or "UNKNOWN",
                            "TrialNumber": f"{trial_index+1}" if correction_count == 0 else f"{trial_index+1}*",
                            "M0_0": img0,
                            "M0_1": img1,
                            "M0_2": "",
                            "touched_m0": touched_m0,
                            "Choice": choice_result,
                            "InitiationTime": trial_start_time,
                            "StartTraining": self.session_start_time or "",
                            "EndTraining": "",
                            "Reward": ""
                        }
                        self._write_realtime_csv_row(row_data)
                        self.trial_data.append(row_data)

                        # Flush leftover messages before next correction attempt
                        for dev in self.m0_devices.values():
                            while not dev.message_queue.empty():
                                try:
                                    dev.message_queue.get_nowait()
                                except queue.Empty:
                                    break

                        correction_count += 1
                        if correction_count >= 3:
                            print("Maximum correction trials reached. Moving on to next trial.")
                            trial_completed = True
                        else:
                            print(f"Repeating trial {trial_index+1} as correction (attempt {correction_count}).")
                            continue  # Retry the same trial.

                    else:  # "no_touch" outcome
                        self.send_m0_command("M0_0", "BLACK")
                        self.send_m0_command("M0_1", "BLACK")

                        row_data = {
                            "ID": self.rodent_id or "UNKNOWN",
                            "TrialNumber": f"{trial_index+1}" if correction_count == 0 else f"{trial_index+1}*",
                            "M0_0": img0,
                            "M0_1": img1,
                            "M0_2": "",
                            "touched_m0": None,
                            "Choice": "no_touch",
                            "InitiationTime": trial_start_time,
                            "StartTraining": self.session_start_time or "",
                            "EndTraining": "",
                            "Reward": ""
                        }
                        self._write_realtime_csv_row(row_data)
                        self.trial_data.append(row_data)

                        # Flush leftover messages before next trial
                        for dev in self.m0_devices.values():
                            while not dev.message_queue.empty():
                                try:
                                    dev.message_queue.get_nowait()
                                except queue.Empty:
                                    break

                        trial_completed = True
                        correction_count = 0

                # End of inner loop; move to next trial.
                trial_index += 1
                if trial_index < len(trials) and self.is_session_active:
                    next_img0, next_img1 = trials[trial_index]
                    print(f"Preloading images for next trial {trial_index+1} (pre-ITI)...")
                    self.send_m0_command("M0_0", f"IMG:{next_img0}")
                    self.send_m0_command("M0_1", f"IMG:{next_img1}")

        finally:
            self.finalize_training_timestamp()
            self.is_session_active = False
            for m0_id in self.m0_ports:
                self.send_m0_command(m0_id, "BLACK")
            print(f"Simple Discrimination Phase finished at {self.session_end_time}.")

        for dev in self.m0_devices.values():
            dev._attempt_reopen()
            time.sleep(0.5)



    def complex_discrimination_phase(self, csv_file_path):
        print("Starting Complex Discrimination.")

            # 1) Flush queues immediately when the phase starts
        for dev in self.m0_devices.values():
            while not dev.message_queue.empty():
                try:
                    dev.message_queue.get_nowait()
                except queue.Empty:
                    break

        self.is_session_active = True
        trials = self.read_csv(csv_file_path)
        if not trials:
            print("No trials found in CSV.")
            return

        from PyQt5.QtWidgets import QApplication

        try:
            trial_index = 0
            # Process each trial (including trial 1) with correction attempts for incorrect responses.
            while trial_index < len(trials) and self.is_session_active:
                # Get current trial stimuli.
                img0, img1 = trials[trial_index]
                correction_count = 0
                trial_completed = False

                while not trial_completed and self.is_session_active:
                    # For Trial 1 first attempt: no initiation required.
                    if trial_index == 0 and correction_count == 0:
                        print("Preloading images for Trial 1 (pre-free reward phase)...")
                        self.send_m0_command("M0_0", f"IMG:{img0}")
                        self.send_m0_command("M0_1", f"IMG:{img1}")
                        print("Dispensing free reward.")
                        _ = self.large_reward(4.0)
                        # Immediately display images.
                        self.send_m0_command("M0_0", "SHOW")
                        self.send_m0_command("M0_1", "SHOW")
                    else:
                        # For any new trial (trial_index > 0) or for correction attempts:
                        print(f"Preloading images for Trial {trial_index+1}{' (correction)' if correction_count > 0 else ''} (pre-ITI)...")
                        self.send_m0_command("M0_0", f"IMG:{img0}")
                        self.send_m0_command("M0_1", f"IMG:{img1}")
                        print(f"--- ITI before Trial {trial_index+1}{' (correction)' if correction_count > 0 else ''} ---")
                        self._fixed_iti()
                        if not self.is_session_active:
                            break
                        print(f"--- Waiting for rodent to initiate Trial {trial_index+1}{' (correction)' if correction_count > 0 else ''} ---")
                        if not self.wait_for_trial_initiation():
                            print(f"Session stopped during initiation for trial {trial_index+1}.")
                            break
                        # Immediately show images after initiation.
                        self.send_m0_command("M0_0", "SHOW")
                        self.send_m0_command("M0_1", "SHOW")

                    # Record initiation time.
                    trial_start_time = datetime.now().strftime("%H:%M:%S")
                    print(f"=== Trial {trial_index+1}{'*' if correction_count > 0 else ''}: M0_0 -> {img0}, M0_1 -> {img1} ===")

                    # Wait for touch response (up to 300 seconds).
                    start_t = time.time()
                    touched_m0 = None
                    touched_image = None
                    choice_result = None

                    while (time.time() - start_t) < 300 and self.is_session_active and not choice_result:
                        QApplication.processEvents()
                        sub_timeout = 1.0
                        sub_start = time.time()
                        found_touch = False

                        while ((time.time() - sub_start) < sub_timeout and not found_touch and self.is_session_active):
                            QApplication.processEvents()
                            for m0_id, device in self.m0_devices.items():
                                try:
                                    m_id, line = device.message_queue.get(timeout=0.02)
                                    if line.startswith("TOUCH:"):
                                        found_touch = True
                                        if m_id == "M0_0":
                                            touched_m0 = "M0_0"
                                            touched_image = img0
                                        else:
                                            touched_m0 = "M0_1"
                                            touched_image = img1
                                        break
                                except queue.Empty:
                                    pass
                            time.sleep(0.01)

                        if found_touch:
                            if touched_image == "E01":
                                choice_result = "correct"
                                print("Correct choice")
                                break
                            elif touched_image == "D01":
                                choice_result = "incorrect"
                                print("Incorrect choice")
                                break

                    if not self.is_session_active:
                        break

                    # If we never got a touch or it didn't match 'E01'/'D01', call it "no_touch".
                    if not choice_result:
                        choice_result = "no_touch"
                        print("No touch => skipping reward")

                    # -------------------- Outcome Handling --------------------
                    if choice_result == "correct":
                        self.send_m0_command("M0_0", "BLACK")
                        self.send_m0_command("M0_1", "BLACK")
                        reward_time = self.large_reward(3.0)

                        row_data = {
                            "ID": self.rodent_id or "UNKNOWN",
                            "TrialNumber": f"{trial_index+1}" if correction_count == 0 else f"{trial_index+1}*",
                            "M0_0": img0,
                            "M0_1": img1,
                            "M0_2": "",
                            "touched_m0": touched_m0,
                            "Choice": choice_result,
                            "InitiationTime": trial_start_time,
                            "StartTraining": self.session_start_time or "",
                            "EndTraining": "",
                            "Reward": reward_time if reward_time else ""
                        }
                        self._write_realtime_csv_row(row_data)
                        self.trial_data.append(row_data)

                        # Flush any leftover messages before next trial
                        for dev in self.m0_devices.values():
                            while not dev.message_queue.empty():
                                try:
                                    dev.message_queue.get_nowait()
                                except queue.Empty:
                                    break

                        trial_completed = True
                        correction_count = 0  # Reset corrections for next trial.

                    elif choice_result == "incorrect":
                        self.send_m0_command("M0_0", "BLACK")
                        self.send_m0_command("M0_1", "BLACK")
                        self.peripherals['punishment_led'].activate()
                        self.peripherals['buzzer'].activate()
                        start_punish = time.time()
                        buzzer_off = False

                        while (time.time() - start_punish) < 5 and self.is_session_active:
                            QApplication.processEvents()
                            elapsed = time.time() - start_punish
                            if (not buzzer_off) and (elapsed >= 0.5):
                                self.peripherals['buzzer'].deactivate()
                                buzzer_off = True
                            time.sleep(0.01)

                        self.peripherals['punishment_led'].deactivate()

                        row_data = {
                            "ID": self.rodent_id or "UNKNOWN",
                            "TrialNumber": f"{trial_index+1}" if correction_count == 0 else f"{trial_index+1}*",
                            "M0_0": img0,
                            "M0_1": img1,
                            "M0_2": "",
                            "touched_m0": touched_m0,
                            "Choice": choice_result,
                            "InitiationTime": trial_start_time,
                            "StartTraining": self.session_start_time or "",
                            "EndTraining": "",
                            "Reward": ""
                        }
                        self._write_realtime_csv_row(row_data)
                        self.trial_data.append(row_data)

                        # Flush leftover messages before next correction attempt
                        for dev in self.m0_devices.values():
                            while not dev.message_queue.empty():
                                try:
                                    dev.message_queue.get_nowait()
                                except queue.Empty:
                                    break

                        correction_count += 1
                        if correction_count >= 3:
                            print("Maximum correction trials reached. Moving on to next trial.")
                            trial_completed = True
                        else:
                            print(f"Repeating trial {trial_index+1} as correction (attempt {correction_count}).")
                            continue  # Retry the same trial.

                    else:  # "no_touch" outcome
                        self.send_m0_command("M0_0", "BLACK")
                        self.send_m0_command("M0_1", "BLACK")

                        row_data = {
                            "ID": self.rodent_id or "UNKNOWN",
                            "TrialNumber": f"{trial_index+1}" if correction_count == 0 else f"{trial_index+1}*",
                            "M0_0": img0,
                            "M0_1": img1,
                            "M0_2": "",
                            "touched_m0": None,
                            "Choice": "no_touch",
                            "InitiationTime": trial_start_time,
                            "StartTraining": self.session_start_time or "",
                            "EndTraining": "",
                            "Reward": ""
                        }
                        self._write_realtime_csv_row(row_data)
                        self.trial_data.append(row_data)

                        # Flush leftover messages before next trial
                        for dev in self.m0_devices.values():
                            while not dev.message_queue.empty():
                                try:
                                    dev.message_queue.get_nowait()
                                except queue.Empty:
                                    break

                        trial_completed = True
                        correction_count = 0

                # End of inner loop; move to next trial.
                trial_index += 1
                if trial_index < len(trials) and self.is_session_active:
                    next_img0, next_img1 = trials[trial_index]
                    print(f"Preloading images for next trial {trial_index+1} (pre-ITI)...")
                    self.send_m0_command("M0_0", f"IMG:{next_img0}")
                    self.send_m0_command("M0_1", f"IMG:{next_img1}")

        finally:
            self.finalize_training_timestamp()
            self.is_session_active = False
            for m0_id in self.m0_ports:
                self.send_m0_command(m0_id, "BLACK")
            print(f"Complex Discrimination Phase finished at {self.session_end_time}.")

        for dev in self.m0_devices.values():
            dev._attempt_reopen()
            time.sleep(0.5)







    def read_csv(self, csv_file_path):
        trials = []
        try:
            with open(csv_file_path, 'r') as f:
                for row in csv.reader(f):
                    if len(row) >= 2:
                        trials.append(row)
        except Exception as e:
            print(f"Error reading CSV '{csv_file_path}': {e}")
        return trials

    def wait_for_touch(self, img0, img1, timeout=180):
        start_time = time.time()
        touched_m0 = None
        touched_image = None
        while time.time() - start_time < timeout:
            if not self.is_session_active:
                break
            QApplication.processEvents()
            for m0_id, device in self.m0_devices.items():
                try:
                    m_id, line = device.message_queue.get(timeout=0.02)
                    if line.startswith("TOUCH:"):
                        if m_id == "M0_0":
                            touched_m0 = "M0_0"
                            touched_image = img0
                        else:
                            touched_m0 = "M0_1"
                            touched_image = img1
                        return touched_m0, touched_image
                except queue.Empty:
                    pass
            time.sleep(0.01)
        return touched_m0, touched_image

    def large_reward(self, pump_secs=1.0):
        if not self.is_session_active:
            return None
        from PyQt5.QtWidgets import QApplication
        reward_time = datetime.now().strftime("%H:%M:%S")
        print(f"large_reward: pumping for {pump_secs} seconds.")
        beam_broken = False
        self.peripherals['reward_led'].activate()
        self.peripherals['beam_break'].deactivate_beam_break()
        self.peripherals['reward'].dispense_reward(duration_s=pump_secs)
        start_t = time.time()
        while (time.time() - start_t) < pump_secs:
            QApplication.processEvents()
            if not self.is_session_active:
                break
            self.peripherals['beam_break'].activate_beam_break()
            if self.peripherals['beam_break'].sensor_state == 0 and not beam_broken:
                beam_broken = True
                print("Beam broken during reward dispense.")
                self.peripherals['reward_led'].deactivate()
            time.sleep(0.01)
        self.peripherals['reward'].stop_reward_dispense()
        if not beam_broken and self.is_session_active:
            print("Waiting for beam to be broken.")
            while self.peripherals['beam_break'].sensor_state != 0:
                QApplication.processEvents()
                if not self.is_session_active:
                    break
                self.peripherals['beam_break'].activate_beam_break()
                time.sleep(0.01)
            if self.peripherals['beam_break'].sensor_state == 0:
                print("Beam broken.")
            while self.peripherals['beam_break'].sensor_state == 0 and self.is_session_active:
                QApplication.processEvents()
                self.peripherals['beam_break'].activate_beam_break()
                time.sleep(0.01)
        self.peripherals['reward_led'].deactivate()
        self.peripherals['beam_break'].deactivate_beam_break()
        print("Beam break deactivated. Reward finished.")
        return reward_time

    def wait_for_trial_initiation(self):
        from PyQt5.QtWidgets import QApplication
        self.peripherals['beam_break'].deactivate_beam_break()
        self.peripherals['reward_led'].activate()
        print("Waiting for beam break to initiate trial...")
        while self.peripherals['beam_break'].sensor_state != 0:
            QApplication.processEvents()
            if not self.is_session_active:
                return False
            self.peripherals['beam_break'].activate_beam_break()
            time.sleep(0.01)
        self.peripherals['reward_led'].deactivate()
        print("Beam broken. Now waiting for beam to be unbroken...")
        while self.peripherals['beam_break'].sensor_state == 0:
            QApplication.processEvents()
            if not self.is_session_active:
                return False
            self.peripherals['beam_break'].activate_beam_break()
            time.sleep(0.01)
        print("Beam unbroken. Trial initiated!")
        return True
    
    
