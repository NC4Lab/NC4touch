import os
import time
from enum import Enum, auto

from trainers.Trainer import Trainer

import logging
logger = logging.getLogger(f"session_logger.{__name__}")


class MustInitiateState(Enum):
    """Enum for different states in the MustInitiate trainer."""
    IDLE = auto()
    START_TRAINING = auto()
    INITIATION_READY = auto()
    WAIT_FOR_TRIAL_INITIATION = auto()
    START_TRIAL = auto()
    WAIT_FOR_TOUCH = auto()
    CORRECT = auto()
    ERROR = auto()
    DELIVER_REWARD_START = auto()
    DELIVERING_REWARD = auto()
    POST_REWARD = auto()
    ITI_START = auto()
    ITI = auto()
    END_TRIAL = auto()
    END_TRAINING = auto()


class MustInitiate(Trainer):
    """
    MustTouch trainer variant that requires trial initiation.

    Before each trial starts, the mouse must trigger the beam break.
    House light behavior:
      - During ITI: dimmed
      - Trial initiation window and trial: bright
    """

    def __init__(self, chamber, trainer_config={}, trainer_config_file='~/trainer_MustInitiate_config.yaml'):
        super().__init__(chamber=chamber, trainer_config=trainer_config, trainer_config_file=trainer_config_file)

        self.config.ensure_param("trainer_name", "MustInitiate")
        self.config.ensure_param("num_trials", 30)
        self.config.ensure_param("reward_pump_secs", 1)
        self.config.ensure_param("beam_break_wait_time", 10)
        self.config.ensure_param("iti_duration", 10)
        self.config.ensure_param("max_iti_duration", 30)
        self.config.ensure_param("iti_increment", 1)
        self.config.ensure_param("touch_timeout", 120)
        self.config.ensure_param("trainer_seq_dir", "./scripts")
        self.config.ensure_param("trainer_seq_file", "seq_file.csv")
        self.config.ensure_param("correct_image", "A01")

        self.current_trial = 0
        iti_duration_value = self.config["iti_duration"]
        self.current_trial_iti = float(iti_duration_value) if iti_duration_value is not None else 10.0

        self.left_image = ""
        self.right_image = ""

        self.reward_start_time = 0.0
        self.reward_collected = False
        self.iti_start_time = 0.0
        self.trial_start_time = 0.0

        self.state = MustInitiateState.IDLE
        self.prev_state = MustInitiateState.IDLE

        self.default_setup_led_colors()

    def start_training(self):
        logger.info("Starting MustInitiate training session...")

        self.chamber.default_state()

        trainer_seq_dir = str(self.config["trainer_seq_dir"])
        trainer_seq_file_name = str(self.config["trainer_seq_file"])
        num_trials_value = self.config["num_trials"]
        configured_num_trials = int(num_trials_value) if num_trials_value is not None else 30

        trainer_seq_file = os.path.join(trainer_seq_dir, trainer_seq_file_name)
        self.trials = self.read_trainer_seq_file(trainer_seq_file, 2)
        if not self.trials:
            logger.error(f"Failed to read trainer sequence file: {trainer_seq_file}")
            self.state = MustInitiateState.IDLE
            return

        if len(self.trials) > configured_num_trials:
            logger.warning(
                "Number of trials in sequence file exceeds expected num_trials (%s). Truncating.",
                configured_num_trials,
            )
            self.trials = self.trials[:configured_num_trials]
        elif len(self.trials) < configured_num_trials:
            logger.warning(
                "Sequence file has fewer trials (%s) than configured num_trials (%s). Using file length.",
                len(self.trials),
                configured_num_trials,
            )

        self.config["num_trials"] = len(self.trials)
        self.open_data_file()
        self.current_trial = 0
        self.state = MustInitiateState.START_TRAINING

    def load_images(self, trial_num):
        """Load images for the current trial from sequence file columns [left, right]."""
        self.left_image = self.trials[trial_num][0]
        self.right_image = self.trials[trial_num][1]

        if self.left_image == "BLACK":
            self.chamber.get_left_m0().send_command("BLACK")
        else:
            self.chamber.get_left_m0().send_command(f"IMG:{self.left_image}")

        if self.right_image == "BLACK":
            self.chamber.get_right_m0().send_command("BLACK")
        else:
            self.chamber.get_right_m0().send_command(f"IMG:{self.right_image}")

    def show_images(self):
        """Display loaded images."""
        if self.left_image != "BLACK":
            self.chamber.get_left_m0().send_command("SHOW")
        if self.right_image != "BLACK":
            self.chamber.get_right_m0().send_command("SHOW")

    def clear_images(self):
        """Blank both screens."""
        self.chamber.get_left_m0().send_command("BLACK")
        self.chamber.get_right_m0().send_command("BLACK")

    def run_training(self):
        current_time = time.time()

        num_trials_value = self.config["num_trials"]
        touch_timeout_value = self.config["touch_timeout"]
        reward_pump_secs_value = self.config["reward_pump_secs"]
        beam_break_wait_time_value = self.config["beam_break_wait_time"]
        iti_duration_value = self.config["iti_duration"]

        num_trials = int(num_trials_value) if num_trials_value is not None else 30
        touch_timeout = float(touch_timeout_value) if touch_timeout_value is not None else 120.0
        reward_pump_secs = float(reward_pump_secs_value) if reward_pump_secs_value is not None else 1.0
        beam_break_wait_time = float(beam_break_wait_time_value) if beam_break_wait_time_value is not None else 10.0
        iti_duration = float(iti_duration_value) if iti_duration_value is not None else 10.0

        if self.state != self.prev_state:
            logger.info(f"State changed: {self.prev_state.name} -> {self.state.name}")
            self.prev_state = self.state

        if self.state == MustInitiateState.IDLE:
            return

        if self.state == MustInitiateState.START_TRAINING:
            self.write_event("StartTraining", 1)
            self.state = MustInitiateState.INITIATION_READY

        elif self.state == MustInitiateState.INITIATION_READY:
            if self.current_trial >= num_trials:
                self.state = MustInitiateState.END_TRAINING
                return

            trial_number = self.current_trial + 1
            self.write_event("TrialInitiationReady", trial_number)
            self.default_start_trial()
            self.chamber.beambreak.activate()
            self.state = MustInitiateState.WAIT_FOR_TRIAL_INITIATION

        elif self.state == MustInitiateState.WAIT_FOR_TRIAL_INITIATION:
            if self.chamber.beambreak.state is False:
                trial_number = self.current_trial + 1
                self.write_event("TrialInitiated", trial_number)
                self.state = MustInitiateState.START_TRIAL

        elif self.state == MustInitiateState.START_TRIAL:
            trial_number = self.current_trial + 1
            self.write_event("StartTrial", trial_number)
            self.load_images(self.current_trial)
            self.show_images()
            self.trial_start_time = current_time
            self.state = MustInitiateState.WAIT_FOR_TOUCH

        elif self.state == MustInitiateState.WAIT_FOR_TOUCH:
            if current_time - self.trial_start_time > touch_timeout:
                logger.info("Touch timeout on trial %s", self.current_trial + 1)
                self.write_event("TouchTimeout", self.current_trial + 1)
                self.clear_images()
                self.state = MustInitiateState.ITI_START
                return

            side = self.check_touch()
            if side is None:
                return

            trial_number = self.current_trial + 1
            self.write_event(f"{side}ScreenTouched", trial_number)

            touched_image = self.left_image if side == "LEFT" else self.right_image
            if touched_image == self.config["correct_image"]:
                self.state = MustInitiateState.CORRECT
            else:
                self.state = MustInitiateState.ERROR

        elif self.state == MustInitiateState.CORRECT:
            self.write_event("CorrectTouch", self.current_trial + 1)
            self.clear_images()
            self.state = MustInitiateState.DELIVER_REWARD_START

        elif self.state == MustInitiateState.ERROR:
            self.write_event("IncorrectTouch", self.current_trial + 1)
            self.clear_images()
            self.state = MustInitiateState.ITI_START

        elif self.state == MustInitiateState.DELIVER_REWARD_START:
            self.write_event("RewardStart", self.current_trial + 1)
            self.reward_collected = False
            self.reward_start_time = self.default_deliver_reward(reward_pump_secs)
            self.state = MustInitiateState.DELIVERING_REWARD

        elif self.state == MustInitiateState.DELIVERING_REWARD:
            if current_time - self.reward_start_time < reward_pump_secs:
                if self.chamber.beambreak.state is False and not self.reward_collected:
                    self.reward_collected = True
                    self.write_event("BeamBreakDuringReward", self.current_trial + 1)
                    self.chamber.reward_led.deactivate()
            else:
                self.default_stop_reward()
                self.write_event("RewardDispenseComplete", self.current_trial + 1)
                self.state = MustInitiateState.POST_REWARD

        elif self.state == MustInitiateState.POST_REWARD:
            if current_time - self.reward_start_time < beam_break_wait_time:
                if self.chamber.beambreak.state is False and not self.reward_collected:
                    self.reward_collected = True
                    self.write_event("BeamBreakAfterReward", self.current_trial + 1)
                    self.state = MustInitiateState.ITI_START
            else:
                self.write_event("BeamBreakTimeout", self.current_trial + 1)
                self.state = MustInitiateState.ITI_START

        elif self.state == MustInitiateState.ITI_START:
            self.write_event("ITIStart", self.current_trial + 1)
            self.current_trial_iti = iti_duration
            self.iti_start_time = self.default_iti_start()
            self.state = MustInitiateState.ITI

        elif self.state == MustInitiateState.ITI:
            current_trial_iti = float(self.current_trial_iti)
            if current_time - self.iti_start_time < current_trial_iti:
                old_iti = self.current_trial_iti
                updated_iti = self.default_iti_check_beam_break(self.current_trial_iti)
                self.current_trial_iti = float(updated_iti) if updated_iti is not None else current_trial_iti
                if self.current_trial_iti > old_iti:
                    self.write_event("BeamBreakDuringITI", self.current_trial + 1)
            else:
                self.state = MustInitiateState.END_TRIAL

        elif self.state == MustInitiateState.END_TRIAL:
            self.write_event("EndTrial", self.current_trial + 1)
            self.current_trial += 1
            self.state = MustInitiateState.INITIATION_READY

        elif self.state == MustInitiateState.END_TRAINING:
            self.write_event("EndTraining", 1)
            self.stop_training()

    def stop_training(self):
        logger.info("Stopping MustInitiate training session...")
        self.default_stop_training()
        self.state = MustInitiateState.IDLE
