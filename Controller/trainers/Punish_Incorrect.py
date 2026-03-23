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

    PRELOAD_FIRST = auto()           # Preload images for the first trial
    FREE_REWARD_START = auto()       # Start free reward for first trial
    DELIVERING_FREE_REWARD = auto()  # Delivering free reward
    SHOW_FIRST = auto()              # Show images for first trial

    START_TRIAL = auto()             # Start a new trial
    ITI_START = auto()               # Start inter-trial interval
    ITI = auto()                     # Inter-trial interval
    WAIT_FOR_INITIATION = auto()     # Waiting for trial initiation
    SHOW_IMAGES = auto()             # Display images on screens

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
        self.config.ensure_param("free_reward_duration", 4.0)  # Duration of free reward on first trial
        self.config.ensure_param("reward_duration", 3.0)       # Reward duration for correct response
        self.config.ensure_param("punish_duration", 5.0)       # Punishment duration for incorrect response
        self.config.ensure_param("buzzer_duration", 0.5)       # Duration of buzzer during punishment
        self.config.ensure_param("touch_timeout", 300)         # Time allowed for touch response
        self.config.ensure_param("trainer_seq_dir", "")        # Directory containing sequence file
        self.config.ensure_param("trainer_seq_file", "")       # Sequence file name
        self.config.ensure_param("correct_image", "A01")       # Image identifier for correct choice
        self.config.ensure_param("initiation_timeout", 300)    # Timeout for trial initiation (seconds)

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

    def _normalize_image_id(self, image_id):
        """Normalize image IDs from CSV/config for reliable comparisons."""
        return str(image_id).strip().upper()

    def _is_correct_image(self, image_id):
        """Return True if the touched image matches the configured correct image."""
        return self._normalize_image_id(image_id) == self._normalize_image_id(self.config["correct_image"])

    def start_training(self):
        # Starting the training session
        logger.info("Starting Punish Incorrect training session...")

        # Reset chamber hardware to default state
        self.chamber.default_state()

        # Open and read the trainer sequence file
        trainer_seq_file = os.path.join(self.config["trainer_seq_dir"], self.config["trainer_seq_file"])
        self.trials = self.read_trainer_seq_file(trainer_seq_file, 2)
        if not self.trials:
            logger.error(f"Failed to read trainer sequence file: {trainer_seq_file}")
            return

        # Validate number of trials in the sequence file
        if len(self.trials) > self.config["num_trials"]:
            logger.warning(
                f"Number of trials in the sequence file exceeds the expected number of trials: {self.config['num_trials']}"
            )
            # Truncate trials if too many
            self.trials = self.trials[:self.config["num_trials"]]
        elif len(self.trials) < self.config["num_trials"]:
            logger.error(
                f"Number of trials in the sequence file does not match the expected number of trials: {self.config['num_trials']}"
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

        # Send commands to display zones to load images.
        # Treat BLACK as an explicit clear state (not a filename).
        if str(self.left_image).strip().upper() == "BLACK":
            self.chamber.display_command("left", "BLACK")
        else:
            self.chamber.display_command("left", f"IMG:{self.left_image}")

        if str(self.right_image).strip().upper() == "BLACK":
            self.chamber.display_command("right", "BLACK")
        else:
            self.chamber.display_command("right", f"IMG:{self.right_image}")

    def show_images(self):
        """Display images on the operant display zones."""
        if str(self.left_image).strip().upper() != "BLACK":
            self.chamber.display_command("left", "SHOW")
        if str(self.right_image).strip().upper() != "BLACK":
            self.chamber.display_command("right", "SHOW")

    def clear_images(self):
        """Clear images on the operant display zones."""
        # Blank both screens
        self.chamber.display_command("left", "BLACK")
        self.chamber.display_command("right", "BLACK")

    def _prepare_touch_window(self):
        """Clear any stale touches before starting a new touch response window."""
        # Ensure queued display operations/events are processed first where supported.
        self.chamber.display_flush()
        self.chamber.display_clear_touches(drain_events=True)

    def run_training(self):
        """Main loop controlling the training state machine."""
        current_time = time.time()

        if self.state == PunishIncorrectState.IDLE:
            # IDLE state, waiting for training to start
            pass

        elif self.state == PunishIncorrectState.START_TRAINING:
            # Initialize training session
            logger.debug("Current state: START_TRAINING")
            self.write_event("StartTraining", 1)

            self.current_trial = 1
            logger.info("Starting trial %s", self.current_trial)
            self.write_event("StartTrial", self.current_trial)
            self.state = PunishIncorrectState.PRELOAD_FIRST

        # ---------------- TRIAL 1 (FREE REWARD) ---------------- #

        elif self.state == PunishIncorrectState.PRELOAD_FIRST:
            # Preload images for the first trial
            logger.debug("Current state: PRELOAD_FIRST")
            self.load_images(0)
            self.state = PunishIncorrectState.FREE_REWARD_START

        elif self.state == PunishIncorrectState.FREE_REWARD_START:
            # Start free reward delivery
            logger.debug("Current state: FREE_REWARD_START")
            self.reward_start_time = current_time
            logger.info("Dispensing free reward")
            self.write_event("FreeRewardStart", 1)
            self.chamber.reward.dispense()
            self.chamber.reward_led.activate()
            self.state = PunishIncorrectState.DELIVERING_FREE_REWARD

        elif self.state == PunishIncorrectState.DELIVERING_FREE_REWARD:
            # Delivering free reward
            logger.debug("Current state: DELIVERING_FREE_REWARD")
            if current_time - self.reward_start_time >= self.config["free_reward_duration"]:
                self.chamber.reward.stop()
                self.chamber.reward_led.deactivate()
                self.state = PunishIncorrectState.SHOW_FIRST

        elif self.state == PunishIncorrectState.SHOW_FIRST:
            # Show images after free reward
            logger.debug("Current state: SHOW_FIRST")
            self.show_images()
            self._prepare_touch_window()
            self.trial_start_time = current_time
            self.state = PunishIncorrectState.WAIT_FOR_TOUCH

        # ---------------- SUBSEQUENT TRIALS ---------------- #

        elif self.state == PunishIncorrectState.START_TRIAL:
            # Start a new trial
            logger.debug("Current state: START_TRIAL")
            if self.current_trial <= self.config["num_trials"]:
                trial_number = self.current_trial
                logger.info("Starting trial %s", trial_number)
                self.write_event("StartTrial", trial_number)
                self.state = PunishIncorrectState.ITI_START
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
            if current_time - self.iti_start_time >= self.config["iti_duration"]:
                self.initiation_start_time = current_time
                self.state = PunishIncorrectState.WAIT_FOR_INITIATION

        elif self.state == PunishIncorrectState.WAIT_FOR_INITIATION:
            #  initiation logic
            logger.debug("Current state: WAIT_FOR_INITIATION")
            self.load_images(self.current_trial - 1)
            if self.chamber.beambreak.state==False:
                logger.info(f"Trial {self.current_trial} initiated by beam break") 
                self.state = PunishIncorrectState.SHOW_IMAGES
            elif current_time - self.initiation_start_time >= self.config["initiation_timeout"]:
                logger.info(f"Initiation timeout on trial {self.current_trial}")
                self.state = PunishIncorrectState.SHOW_IMAGES

        elif self.state == PunishIncorrectState.SHOW_IMAGES:
            # Display images for the trial
            logger.debug("Current state: SHOW_IMAGES")
            self.show_images()
            self._prepare_touch_window()
            self.trial_start_time = current_time
            self.state = PunishIncorrectState.WAIT_FOR_TOUCH

        # ---------------- CHOICE LOGIC ---------------- #

        elif self.state == PunishIncorrectState.WAIT_FOR_TOUCH:
            # Waiting for screen touch
            logger.debug("Current state: WAIT_FOR_TOUCH")
            if current_time - self.trial_start_time <= self.config["touch_timeout"]:
                touched_side = None
                touched_image = None

                if self.chamber.display_was_touched("left"):
                    self.write_event("LeftScreenTouched", self.current_trial)
                    touched_side = "left"
                    touched_image = self.left_image

                elif self.chamber.display_was_touched("right"):
                    self.write_event("RightScreenTouched", self.current_trial)
                    touched_side = "right"
                    touched_image = self.right_image

                if touched_side is not None:
                    if self._is_correct_image(touched_image):
                        self.state = PunishIncorrectState.CORRECT
                        logger.info(
                            "Trial %s %s touch (%s) -> CORRECT",
                            self.current_trial,
                            touched_side,
                            touched_image,
                        )
                    else:
                        self.state = PunishIncorrectState.INCORRECT
                        logger.info(
                            "Trial %s %s touch (%s) -> INCORRECT (correct=%s)",
                            self.current_trial,
                            touched_side,
                            touched_image,
                            self.config["correct_image"],
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
            self.state = PunishIncorrectState.END_TRIAL

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
            if current_time - self.reward_start_time >= self.config["reward_duration"]:
                self.chamber.reward.stop()
                self.chamber.reward_led.deactivate()
                self.state = PunishIncorrectState.END_TRIAL

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

            if elapsed >= self.config["buzzer_duration"]:
                self.chamber.buzzer.deactivate()

            if elapsed >= self.config["punish_duration"]:
                self.chamber.punishment_led.deactivate()
                self.state = PunishIncorrectState.END_TRIAL

        elif self.state == PunishIncorrectState.END_TRIAL:
            # End of trial cleanup
            logger.debug("Current state: END_TRIAL")
            self.write_event("EndTrial", self.current_trial)
            self.current_trial += 1

            # Preload images for next trial if available
            if self.current_trial <= len(self.trials):
                self.load_images(self.current_trial - 1)

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