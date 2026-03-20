import time
from enum import Enum, auto
import os

from trainers.Trainer import Trainer

import logging
logger = logging.getLogger(f"session_logger.{__name__}")


class PunishIncorrectState(Enum):
    """Enum for different states in the punish-incorrect trainer."""
    IDLE = auto()                    # Trainer is idle, waiting to start
    START_TRAINING = auto()          # Initialize training session

    START_TRIAL = auto()             # Start a new trial
    ITI_START = auto()               # Start inter-trial interval
    ITI = auto()                     # Inter-trial interval

    WAIT_FOR_TOUCH = auto()          # Waiting for animal to touch screen
    CORRECT = auto()                 # Correct touch detected
    INCORRECT = auto()               # Incorrect touch detected
    NO_TOUCH = auto()                # No touch within timeout

    REWARD_START = auto()            # Start reward delivery
    DELIVERING_REWARD = auto()       # Delivering reward
    PUNISH_START = auto()            # Start punishment
    DELIVERING_PUNISH = auto()       # Delivering punishment

    END_TRIAL = auto()               # End current trial
    END_TRAINING = auto()            # End training session


class PunishIncorrect(Trainer):
    def __init__(self, chamber, trainer_config = {}, trainer_config_file = '~/trainer_PunishIncorrect_config.yaml'):
        super().__init__(chamber=chamber, trainer_config=trainer_config, trainer_config_file=trainer_config_file)

        # Initialize the trainer configuration.
        # All configurable parameters should be set here to allow easy modification.
        self.config.ensure_param("trainer_name", "PunishIncorrect")
        self.config.ensure_param("num_trials", 30)             # Total number of trials
        self.config.ensure_param("iti_duration", 10)           # Inter-trial interval duration (seconds)
        self.config.ensure_param("reward_duration", 3.0)       # Reward duration for correct response
        self.config.ensure_param("punish_duration", 5.0)       # Punishment duration for incorrect response
        self.config.ensure_param("buzzer_duration", 0.5)       # Duration of buzzer during punishment
        self.config.ensure_param("touch_timeout", 300)         # Time allowed for touch response
        self.config.ensure_param("trainer_seq_dir", "")        # Directory containing sequence file
        self.config.ensure_param("trainer_seq_file", "")       # Sequence file name
        self.config.ensure_param("correct_image", "A01")       # Image identifier for correct choice

        # Local variables used during training
        self.current_trial = 0
        self.reward_start_time = 0.0
        self.punish_start_time = 0.0
        self.iti_start_time = 0.0
        self.trial_start_time = 0.0

        # Image identifiers for current trial
        self.left_image = ""
        self.right_image = ""

        # Initialize trainer state
        self.state = PunishIncorrectState.IDLE

    def start_training(self):
        # Starting the training session
        logger.info("Starting Punish Incorrect training session...")
        trainer_seq_dir = str(self.config["trainer_seq_dir"] or "")
        trainer_seq_file_name = str(self.config["trainer_seq_file"] or "")
        num_trials = int(self.config["num_trials"] or 0)

        # Reset chamber hardware to default state
        self.chamber.default_state()

        # Open and read the trainer sequence file
        trainer_seq_file = os.path.join(trainer_seq_dir, trainer_seq_file_name)
        self.trials = self.read_trainer_seq_file(trainer_seq_file, 2)
        if not self.trials:
            logger.error(f"Failed to read trainer sequence file: {trainer_seq_file}")
            return

        # Validate number of trials in the sequence file
        if len(self.trials) > num_trials:
            logger.warning(
                f"Number of trials in the sequence file exceeds the expected number of trials: {num_trials}"
            )
            # Truncate trials if too many
            self.trials = self.trials[:num_trials]
        elif len(self.trials) < num_trials:
            logger.error(
                f"Number of trials in the sequence file does not match the expected number of trials: {num_trials}"
            )
            return

        # Start recording data
        self.open_data_file()

        # Transition to training start state
        self.state = PunishIncorrectState.START_TRAINING

    def load_images(self, trial_num):
        """Load images for the current trial."""
        # Get image identifiers from the sequence file
        self.left_image = str(self.trials[trial_num][0]).strip()
        self.right_image = str(self.trials[trial_num][1]).strip()
        left_token = self.left_image.upper()
        right_token = self.right_image.upper()
        side_hint = ""
        if len(self.trials[trial_num]) >= 3:
            side_hint = str(self.trials[trial_num][2]).strip().upper()

        # PunishIncorrect should present only one active stimulus per trial.
        # Active side is determined by sequence row values.
        left_is_black = left_token == "BLACK"
        right_is_black = right_token == "BLACK"
        if not left_is_black and not right_is_black:
            if side_hint in ("LEFT", "L"):
                self.right_image = "BLACK"
                right_token = "BLACK"
            elif side_hint in ("RIGHT", "R"):
                self.left_image = "BLACK"
                left_token = "BLACK"
            else:
                # Keep behavior deterministic if sequence row is ambiguous.
                self.right_image = "BLACK"
                right_token = "BLACK"
                logger.warning(
                    "Trial %s has two active stimuli but no valid side hint in column 3; defaulting to LEFT active.",
                    trial_num + 1,
                )

        # Send commands to M0 devices to load images
        if left_token == "BLACK":
            self.chamber.get_left_m0().send_command("BLACK")
        else:
            self.chamber.get_left_m0().send_command(f"IMG:{self.left_image}")

        if right_token == "BLACK":
            self.chamber.get_right_m0().send_command("BLACK")
        else:
            self.chamber.get_right_m0().send_command(f"IMG:{self.right_image}")

    def show_images(self):
        """Display images on the M0 devices."""
        # Send show command to both screens
        if self.left_image.upper() != "BLACK":
            self.chamber.get_left_m0().send_command("SHOW")
        if self.right_image.upper() != "BLACK":
            self.chamber.get_right_m0().send_command("SHOW")

    def clear_images(self):
        """Clear the images on the M0 devices."""
        # Blank both screens
        self.chamber.get_left_m0().send_command("BLACK")
        self.chamber.get_right_m0().send_command("BLACK")

    def run_training(self):
        """Main loop controlling the training state machine."""
        current_time = time.time()
        num_trials = int(self.config["num_trials"] or 0)
        iti_duration = float(self.config["iti_duration"] or 0.0)
        touch_timeout = float(self.config["touch_timeout"] or 0.0)
        reward_duration = float(self.config["reward_duration"] or 0.0)
        buzzer_duration = float(self.config["buzzer_duration"] or 0.0)
        punish_duration = float(self.config["punish_duration"] or 0.0)
        correct_image = str(self.config["correct_image"] or "").strip().upper()

        if self.state == PunishIncorrectState.IDLE:
            # IDLE state, waiting for training to start
            pass

        elif self.state == PunishIncorrectState.START_TRAINING:
            # Initialize training session
            logger.debug("Current state: START_TRAINING")
            self.write_event("StartTraining", 1)

            self.current_trial = 1
            self.state = PunishIncorrectState.START_TRIAL

        elif self.state == PunishIncorrectState.START_TRIAL:
            # Start a new trial
            logger.debug("Current state: START_TRIAL")
            if self.current_trial <= num_trials:
                trial_number = self.current_trial
                logger.info("Starting trial %s", trial_number)
                self.write_event("StartTrial", trial_number)
                self.load_images(self.current_trial - 1)
                self.show_images()
                self.trial_start_time = current_time
                self.state = PunishIncorrectState.WAIT_FOR_TOUCH
            else:
                # All trials completed
                self.state = PunishIncorrectState.END_TRAINING

        elif self.state == PunishIncorrectState.ITI_START:
            # Begin inter-trial interval
            logger.debug("Current state: ITI_START")
            self.iti_start_time = current_time
            self.write_event("ITIStart", self.current_trial)
            self.state = PunishIncorrectState.ITI

        elif self.state == PunishIncorrectState.ITI:
            # Waiting during inter-trial interval
            logger.debug("Current state: ITI")
            if current_time - self.iti_start_time >= iti_duration:
                self.state = PunishIncorrectState.END_TRIAL

        # ---------------- CHOICE LOGIC ---------------- #

        elif self.state == PunishIncorrectState.WAIT_FOR_TOUCH:
            # Waiting for screen touch
            logger.debug("Current state: WAIT_FOR_TOUCH")
            if current_time - self.trial_start_time <= touch_timeout:
                side = self.check_touch()
                if side == "LEFT":
                    self.write_event("LeftScreenTouched", self.current_trial)
                    touched_image = self.left_image
                    self.state = (
                        PunishIncorrectState.CORRECT
                        if str(touched_image).strip().upper() == correct_image
                        else PunishIncorrectState.INCORRECT
                    )
                elif side == "RIGHT":
                    self.write_event("RightScreenTouched", self.current_trial)
                    touched_image = self.right_image
                    self.state = (
                        PunishIncorrectState.CORRECT
                        if str(touched_image).strip().upper() == correct_image
                        else PunishIncorrectState.INCORRECT
                    )
            else:
                # Touch timeout
                self.write_event("TouchTimeout", self.current_trial)
                self.state = PunishIncorrectState.NO_TOUCH

        elif self.state == PunishIncorrectState.CORRECT:
            # Correct touch detected
            logger.debug("Current state: CORRECT")
            self.write_event("CorrectTouch", self.current_trial)
            self.clear_images()
            self.state = PunishIncorrectState.REWARD_START

        elif self.state == PunishIncorrectState.INCORRECT:
            # Incorrect touch detected
            logger.debug("Current state: INCORRECT")
            self.write_event("IncorrectTouch", self.current_trial)
            self.clear_images()
            self.state = PunishIncorrectState.PUNISH_START

        elif self.state == PunishIncorrectState.NO_TOUCH:
            # No response detected
            logger.debug("Current state: NO_TOUCH")
            self.clear_images()
            self.state = PunishIncorrectState.ITI_START

        elif self.state == PunishIncorrectState.REWARD_START:
            # Start reward delivery
            logger.debug("Current state: REWARD_START")
            self.reward_start_time = current_time
            self.write_event("RewardStart", self.current_trial)
            self.chamber.reward.dispense()
            self.chamber.reward_led.activate()
            self.state = PunishIncorrectState.DELIVERING_REWARD

        elif self.state == PunishIncorrectState.DELIVERING_REWARD:
            # Delivering reward
            logger.debug("Current state: DELIVERING_REWARD")
            if current_time - self.reward_start_time >= reward_duration:
                self.chamber.reward.stop()
                self.chamber.reward_led.deactivate()
                self.state = PunishIncorrectState.ITI_START

        elif self.state == PunishIncorrectState.PUNISH_START:
            # Start punishment
            logger.debug("Current state: PUNISH_START")
            self.punish_start_time = current_time
            self.write_event("PunishStart", self.current_trial)
            self.chamber.punishment_led.activate()
            self.chamber.buzzer.activate()
            self.state = PunishIncorrectState.DELIVERING_PUNISH

        elif self.state == PunishIncorrectState.DELIVERING_PUNISH:
            # Delivering punishment
            logger.debug("Current state: DELIVERING_PUNISH")
            elapsed = current_time - self.punish_start_time

            if elapsed >= buzzer_duration:
                self.chamber.buzzer.deactivate()

            if elapsed >= punish_duration:
                self.chamber.punishment_led.deactivate()
                self.state = PunishIncorrectState.ITI_START

        elif self.state == PunishIncorrectState.END_TRIAL:
            # End of trial cleanup
            logger.debug("Current state: END_TRIAL")
            self.write_event("EndTrial", self.current_trial)
            self.current_trial += 1

            self.state = PunishIncorrectState.START_TRIAL

        elif self.state == PunishIncorrectState.END_TRAINING:
            # End the training session
            logger.debug("Current state: END_TRAINING")
            self.write_event("EndTraining", 1)
            self.state = PunishIncorrectState.IDLE
            self.stop_training()

    def stop_training(self):
        # Stop the training session and reset hardware
        logger.info("Stopping Punish Incorrect training session...")
        self.chamber.reward.stop()
        self.chamber.reward_led.deactivate()
        self.chamber.punishment_led.deactivate()
        self.chamber.buzzer.deactivate()
        self.close_data_file()
        self.state = PunishIncorrectState.IDLE