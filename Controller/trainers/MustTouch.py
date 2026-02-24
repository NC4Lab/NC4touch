import os
import time
from enum import Enum, auto

from trainers.Trainer import Trainer

import logging
logger = logging.getLogger(f"session_logger.{__name__}")


class MustTouchState(Enum):
    """Enum for different states in the MustTouch trainer."""
    IDLE = auto()
    START_TRAINING = auto()
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


class MustTouch(Trainer):
    """
    MustTouch trainer.

    Two images are shown (correct vs incorrect). Reward is delivered only when
    the rodent touches the screen showing the configured correct image.
    """

    def __init__(self, chamber, trainer_config={}, trainer_config_file='~/trainer_MustTouch_config.yaml'):
        super().__init__(chamber=chamber, trainer_config=trainer_config, trainer_config_file=trainer_config_file)

        self.config.ensure_param("trainer_name", "MustTouch")
        self.config.ensure_param("num_trials", 30)
        self.config.ensure_param("reward_pump_secs", 3.5)
        self.config.ensure_param("beam_break_wait_time", 10)
        self.config.ensure_param("iti_duration", 10)
        self.config.ensure_param("max_iti_duration", 30)
        self.config.ensure_param("iti_increment", 1)
        self.config.ensure_param("touch_timeout", 120)
        self.config.ensure_param("trainer_seq_dir", "./scripts")
        self.config.ensure_param("trainer_seq_file", "seq_file.csv")
        self.config.ensure_param("correct_image", "A01")

        self.current_trial = 0
        self.current_trial_iti = self.config["iti_duration"]

        self.left_image = ""
        self.right_image = ""

        self.reward_start_time = 0.0
        self.reward_collected = False
        self.iti_start_time = 0.0
        self.trial_start_time = 0.0

        self.state = MustTouchState.IDLE
        self.prev_state = MustTouchState.IDLE

        self.default_setup_led_colors()

    def start_training(self):
        logger.info("Starting MustTouch training session...")

        self.chamber.default_state()

        trainer_seq_file = os.path.join(self.config["trainer_seq_dir"], self.config["trainer_seq_file"])
        self.trials = self.read_trainer_seq_file(trainer_seq_file, 2)
        if not self.trials:
            logger.error(f"Failed to read trainer sequence file: {trainer_seq_file}")
            self.state = MustTouchState.IDLE
            return

        if len(self.trials) > self.config["num_trials"]:
            logger.warning(
                "Number of trials in sequence file exceeds expected num_trials (%s). Truncating.",
                self.config["num_trials"],
            )
            self.trials = self.trials[:self.config["num_trials"]]
        elif len(self.trials) < self.config["num_trials"]:
            logger.warning(
                "Sequence file has fewer trials (%s) than configured num_trials (%s). Using file length.",
                len(self.trials),
                self.config["num_trials"],
            )

        self.config["num_trials"] = len(self.trials)
        self.open_data_file()
        self.current_trial = 0
        self.state = MustTouchState.START_TRAINING

    def load_images(self, trial_num):
        """Load images for the current trial from sequence file columns [left, right]."""
        self.left_image = self.trials[trial_num][0]
        self.right_image = self.trials[trial_num][1]

        if self.left_image == "BLACK":
            self.chamber.left_m0.send_command("BLACK")
        else:
            self.chamber.left_m0.send_command(f"IMG:{self.left_image}")

        if self.right_image == "BLACK":
            self.chamber.right_m0.send_command("BLACK")
        else:
            self.chamber.right_m0.send_command(f"IMG:{self.right_image}")

    def show_images(self):
        """Display loaded images."""
        if self.left_image != "BLACK":
            self.chamber.left_m0.send_command("SHOW")
        if self.right_image != "BLACK":
            self.chamber.right_m0.send_command("SHOW")

    def clear_images(self):
        """Blank both screens."""
        self.chamber.left_m0.send_command("BLACK")
        self.chamber.right_m0.send_command("BLACK")

    def run_training(self):
        current_time = time.time()

        if self.state != self.prev_state:
            logger.info(f"State changed: {self.prev_state.name} -> {self.state.name}")
            self.prev_state = self.state

        if self.state == MustTouchState.IDLE:
            return

        if self.state == MustTouchState.START_TRAINING:
            self.write_event("StartTraining", 1)
            self.chamber.house_led.activate()
            self.state = MustTouchState.START_TRIAL

        elif self.state == MustTouchState.START_TRIAL:
            if self.current_trial >= self.config["num_trials"]:
                self.state = MustTouchState.END_TRAINING
                return

            trial_number = self.current_trial + 1
            self.write_event("StartTrial", trial_number)
            self.default_start_trial()
            self.load_images(self.current_trial)
            self.show_images()
            self.trial_start_time = current_time
            self.state = MustTouchState.WAIT_FOR_TOUCH

        elif self.state == MustTouchState.WAIT_FOR_TOUCH:
            if current_time - self.trial_start_time > self.config["touch_timeout"]:
                logger.info("Touch timeout on trial %s", self.current_trial + 1)
                self.write_event("TouchTimeout", self.current_trial + 1)
                self.clear_images()
                self.state = MustTouchState.ITI_START
                return

            side = self.check_touch()
            if side is None:
                return

            trial_number = self.current_trial + 1
            self.write_event(f"{side}ScreenTouched", trial_number)

            touched_image = self.left_image if side == "LEFT" else self.right_image
            if touched_image == self.config["correct_image"]:
                self.state = MustTouchState.CORRECT
            else:
                self.state = MustTouchState.ERROR

        elif self.state == MustTouchState.CORRECT:
            self.write_event("CorrectTouch", self.current_trial + 1)
            self.clear_images()
            self.state = MustTouchState.DELIVER_REWARD_START

        elif self.state == MustTouchState.ERROR:
            self.write_event("IncorrectTouch", self.current_trial + 1)
            self.clear_images()
            self.state = MustTouchState.ITI_START

        elif self.state == MustTouchState.DELIVER_REWARD_START:
            self.write_event("RewardStart", self.current_trial + 1)
            self.reward_collected = False
            self.reward_start_time = self.default_deliver_reward(self.config["reward_pump_secs"])
            self.state = MustTouchState.DELIVERING_REWARD

        elif self.state == MustTouchState.DELIVERING_REWARD:
            if current_time - self.reward_start_time < self.config["reward_pump_secs"]:
                if self.chamber.beambreak.state is False and not self.reward_collected:
                    self.reward_collected = True
                    self.write_event("BeamBreakDuringReward", self.current_trial + 1)
                    self.chamber.reward_led.deactivate()
            else:
                self.default_stop_reward()
                self.write_event("RewardDispenseComplete", self.current_trial + 1)
                self.state = MustTouchState.POST_REWARD

        elif self.state == MustTouchState.POST_REWARD:
            if current_time - self.reward_start_time < self.config["beam_break_wait_time"]:
                if self.chamber.beambreak.state is False and not self.reward_collected:
                    self.reward_collected = True
                    self.write_event("BeamBreakAfterReward", self.current_trial + 1)
                    self.state = MustTouchState.ITI_START
            else:
                self.write_event("BeamBreakTimeout", self.current_trial + 1)
                self.state = MustTouchState.ITI_START

        elif self.state == MustTouchState.ITI_START:
            self.write_event("ITIStart", self.current_trial + 1)
            self.current_trial_iti = self.config["iti_duration"]
            self.iti_start_time = self.default_iti_start()
            self.state = MustTouchState.ITI

        elif self.state == MustTouchState.ITI:
            if current_time - self.iti_start_time < self.current_trial_iti:
                old_iti = self.current_trial_iti
                self.current_trial_iti = self.default_iti_check_beam_break(self.current_trial_iti)
                if self.current_trial_iti > old_iti:
                    self.write_event("BeamBreakDuringITI", self.current_trial + 1)
            else:
                self.state = MustTouchState.END_TRIAL

        elif self.state == MustTouchState.END_TRIAL:
            self.write_event("EndTrial", self.current_trial + 1)
            self.current_trial += 1
            self.state = MustTouchState.START_TRIAL

        elif self.state == MustTouchState.END_TRAINING:
            self.write_event("EndTraining", 1)
            self.stop_training()

    def stop_training(self):
        logger.info("Stopping MustTouch training session...")
        self.default_stop_training()
        self.state = MustTouchState.IDLE
