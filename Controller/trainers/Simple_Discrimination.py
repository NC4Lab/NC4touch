import os
from enum import Enum, auto
import time
import logging
from trainers.Trainer import Trainer

logger = logging.getLogger(f"session_logger.{__name__}")

class SDState(Enum):
    IDLE = auto()
    START_TRAINING = auto()
    START_TRIAL = auto()
    INITIATION = auto()
    SHOW_STIMULI = auto()
    WAIT_FOR_TOUCH = auto()
    CORRECT = auto()
    ERROR = auto()
    DELIVERING_REWARD = auto()
    DELIVERING_PUNISH = auto()
    ITI_START = auto()
    ITI = auto()
    END_TRIAL = auto()
    END_TRAINING = auto()

class SimpleDiscrimination(Trainer):

    def __init__(self, chamber, trainer_config={}, trainer_config_file="~/trainer_SD_config.yaml"):
        super().__init__(chamber, trainer_config, trainer_config_file)

        self.config.ensure_param("trainer_name", "Simple Discrimination")
        self.config.ensure_param("num_trials", 30)
        self.config.ensure_param("reward_pump_secs", 0.5)
        self.config.ensure_param("punish_duration", 5.0)
        self.config.ensure_param("buzzer_duration", 0.5)
        self.config.ensure_param("iti_duration", 10)
        self.config.ensure_param("touch_timeout", 300)
        self.config.ensure_param("session_timeout_minutes", 60)
        self.config.ensure_param("trainer_seq_dir", "")
        self.config.ensure_param("trainer_seq_file", "")
        self.config.ensure_param("correct_image", "A01")

        self.state = SDState.IDLE
        self.current_trial = 0  # successful trials completed
        self.correction_count = 0

        self.left_image = ""
        self.right_image = ""

        self.trials = []
        self.session_start_time = 0.0
        self.trial_start_time = 0.0
        self.reward_start_time = 0.0
        self.punish_start_time = 0.0
        self.iti_start_time = 0.0

        self.trial_success = False
        self.repeat_trial = False

    # ---------- helper methods ----------

    def _normalize_image_id(self, image_id):
        return str(image_id).strip().upper()

    def _is_correct_image(self, image_id):
        return self._normalize_image_id(image_id) == self._normalize_image_id(self.config["correct_image"])

    def load_images(self, trial_index):
        self.left_image = str(self.trials[trial_index][0]).strip()
        self.right_image = str(self.trials[trial_index][1]).strip()

        if self._normalize_image_id(self.left_image) == "BLACK":
            self.chamber.get_left_m0().send_command("BLACK")
        else:
            self.chamber.get_left_m0().send_command(f"IMG:{self.left_image}")

        if self._normalize_image_id(self.right_image) == "BLACK":
            self.chamber.get_right_m0().send_command("BLACK")
        else:
            self.chamber.get_right_m0().send_command(f"IMG:{self.right_image}")

    def show_images(self):
        if self._normalize_image_id(self.left_image) != "BLACK":
            self.chamber.get_left_m0().send_command("SHOW")
        if self._normalize_image_id(self.right_image) != "BLACK":
            self.chamber.get_right_m0().send_command("SHOW")

    def clear_images(self):
        self.chamber.get_left_m0().send_command("BLACK")
        self.chamber.get_right_m0().send_command("BLACK")

    # ---------- session control ----------

    def start_training(self):
        logger.info("Starting Simple Discrimination training")
        trainer_seq_dir = str(self.config["trainer_seq_dir"] or "")
        trainer_seq_file_name = str(self.config["trainer_seq_file"] or "")
        num_trials = int(self.config["num_trials"] or 0)

        trainer_seq_file = os.path.join(trainer_seq_dir, trainer_seq_file_name)
        self.trials = self.read_trainer_seq_file(trainer_seq_file, 2)
        if not self.trials:
            logger.error("Failed to read trainer sequence file: %s", trainer_seq_file)
            return
        if len(self.trials) < num_trials:
            logger.error(
                "Sequence file has fewer rows (%s) than num_trials (%s).",
                len(self.trials),
                num_trials,
            )
            return
        if len(self.trials) > num_trials:
            logger.warning(
                "Sequence file has more rows (%s) than num_trials (%s); truncating.",
                len(self.trials),
                num_trials,
            )
            self.trials = self.trials[:num_trials]

        self.chamber.default_state()
        self.open_data_file()
        self.session_start_time = time.time()
        self.state = SDState.START_TRAINING

    def run_training(self):
        now = time.time()
        num_trials = int(self.config["num_trials"] or 0)
        touch_timeout = float(self.config["touch_timeout"] or 0.0)
        reward_pump_secs = float(self.config["reward_pump_secs"] or 0.0)
        punish_duration = float(self.config["punish_duration"] or 0.0)
        buzzer_duration = float(self.config["buzzer_duration"] or 0.0)
        iti_duration = float(self.config["iti_duration"] or 0.0)
        session_timeout_secs = float(self.config["session_timeout_minutes"] or 0.0) * 60.0

        if (
            self.state not in (SDState.IDLE, SDState.END_TRAINING)
            and session_timeout_secs > 0
            and (now - self.session_start_time) >= session_timeout_secs
        ):
            logger.info("Session timeout reached at %.1f minutes.", session_timeout_secs / 60.0)
            self.write_event("SessionTimeout", self.current_trial)
            self.state = SDState.END_TRAINING

        if self.state == SDState.START_TRAINING:
            self.write_event("StartTraining", 1)
            self.current_trial = 0
            self.correction_count = 0
            self.repeat_trial = False
            self.state = SDState.START_TRIAL

        elif self.state == SDState.START_TRIAL:
            if self.current_trial >= num_trials:
                self.state = SDState.END_TRAINING
                return

            trial_number = self.current_trial + 1
            if not self.repeat_trial:
                self.correction_count = 0
                logger.info("Starting trial %s", trial_number)
            else:
                logger.info("Repeating trial %s (correction #%s)", trial_number, self.correction_count)
            self.write_event("StartTrial", trial_number)

            self.load_images(self.current_trial)
            self.state = SDState.INITIATION

        elif self.state == SDState.INITIATION:
            if self.wait_for_trial_initiation():
                self.state = SDState.SHOW_STIMULI

        elif self.state == SDState.SHOW_STIMULI:
            self.show_images()
            self.prepare_touch_window(drain_events=True)
            self.trial_start_time = now
            self.state = SDState.WAIT_FOR_TOUCH

        elif self.state == SDState.WAIT_FOR_TOUCH:
            if now - self.trial_start_time > touch_timeout:
                self.write_event("TouchTimeout", self.current_trial + 1)
                self.trial_success = False
                self.clear_images()
                self.state = SDState.ITI_START
                return

            side = self.check_touch()
            if side is None:
                return

            if side == "LEFT":
                self.write_event("LeftScreenTouched", self.current_trial + 1)
                touched_image = self.left_image
            elif side == "RIGHT":
                self.write_event("RightScreenTouched", self.current_trial + 1)
                touched_image = self.right_image
            else:
                return

            if self._is_correct_image(touched_image):
                self.state = SDState.CORRECT
            else:
                self.state = SDState.ERROR

        elif self.state == SDState.CORRECT:
            trial_number = self.current_trial + 1
            self.write_event("CorrectTouch", trial_number)
            self.clear_images()
            self.reward_start_time = now
            self.write_event("RewardStart", trial_number)
            self.chamber.reward.dispense()
            self.chamber.reward_led.activate()
            self.state = SDState.DELIVERING_REWARD

        elif self.state == SDState.ERROR:
            trial_number = self.current_trial + 1
            self.write_event("IncorrectTouch", trial_number)
            self.clear_images()
            self.correction_count += 1
            self.punish_start_time = now
            self.write_event("PunishStart", trial_number)
            self.chamber.punishment_led.activate()
            self.chamber.buzzer.activate()
            self.state = SDState.DELIVERING_PUNISH

        elif self.state == SDState.DELIVERING_REWARD:
            if now - self.reward_start_time >= reward_pump_secs:
                self.chamber.reward.stop()
                self.chamber.reward_led.deactivate()
                self.trial_success = True
                self.state = SDState.ITI_START

        elif self.state == SDState.DELIVERING_PUNISH:
            elapsed = now - self.punish_start_time
            if elapsed >= buzzer_duration:
                self.chamber.buzzer.deactivate()
            if elapsed >= punish_duration:
                self.chamber.punishment_led.deactivate()
                self.trial_success = False
                self.state = SDState.ITI_START

        elif self.state == SDState.ITI_START:
            self.write_event("ITIStart", self.current_trial + 1)
            self.iti_start_time = now
            self.state = SDState.ITI

        elif self.state == SDState.ITI:
            if now - self.iti_start_time >= iti_duration:
                self.state = SDState.END_TRIAL

        elif self.state == SDState.END_TRIAL:
            self.write_event("EndTrial", self.current_trial + 1)
            if self.trial_success:
                self.current_trial += 1
                self.repeat_trial = False
            else:
                self.repeat_trial = True
            self.state = SDState.START_TRIAL

        elif self.state == SDState.END_TRAINING:
            self.write_event("EndTraining", 1)
            self.stop_training()

    def stop_training(self):
        logger.info("Stopping Simple Discrimination...")
        self.chamber.reward.stop()
        self.chamber.reward_led.deactivate()
        self.chamber.punishment_led.deactivate()
        self.chamber.buzzer.deactivate()
        self.chamber.beambreak.deactivate()
        self.clear_images()
        self.close_data_file()
        self.state = SDState.IDLE
