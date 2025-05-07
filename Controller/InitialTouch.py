import time
from datetime import datetime
from enum import Enum

from Trainer import Trainer
from Chamber import Chamber

import logging
logger = logging.getLogger(f"session_logger.{__name__}")

class InitialTouchState(Enum):
    """Enum for different states in the initial touch trainer."""
    IDLE = -1
    START_TRAINING = 0
    START_TRIAL = 1
    DELIVER_REWARD_START = 2
    DELIVERING_REWARD = 3
    POST_REWARD = 4
    ITI_START = 5
    ITI = 6
    END_TRIAL = 7
    END_TRAINING = 8

class InitialTouch(Trainer):

    def __init__(self, trainer_config = {}, chamber = None):
        super().__init__(trainer_config, chamber)
        self.trainer_name = "InitialTouch"
        self.trial_data = []

        self.num_trials = 30
        self.current_trial = 0

        self.state = InitialTouchState.IDLE

    def start_training(self):
        # Starting state
        #TODO: Turn screens off
        self.chamber.beambreak.deactivate()
        self.chamber.reward_led.deactivate()
        self.chamber.punishment_led.deactivate()
        self.chamber.buzzer.deactivate()
        self.chamber.reward.stop()

        # Start the training session
        logger.info("Starting training session")
        self.state = InitialTouchState.START_TRAINING
    
    def run_training(self):
       
        """Main loop for running the training session."""
        current_time = time.time()

        if self.state == InitialTouchState.IDLE:
            # IDLE state, waiting for the start signal
            logger.debug("Current state: IDLE")
            pass
