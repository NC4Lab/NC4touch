from Trainer import Trainer
from Chamber import Chamber

import logging
logger = logging.getLogger(f"session_logger.{__name__}")

class DoNothingTrainer(Trainer):
    """
    A trainer that does nothing. This is useful for testing purposes.
    """
    def __init__(self, trainer_config = {}, chamber = None):
        super().__init__(trainer_config, chamber)
        self.trainer_name = "DoNothingTrainer"

    def start_training(self):
        """Start the training session."""
        logger.info(f"Starting training session...")
    
    def run_training(self):
        """Run the training session."""
        logger.debug(f"Running training session...")

    def stop_training(self):
        """Stop the training session."""
        logger.info(f"Stopping training session...")
