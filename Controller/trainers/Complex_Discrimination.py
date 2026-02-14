import logging
from trainers.Simple_Discrimination import Simple_Discrimination

logger = logging.getLogger(f"session_logger.{__name__}")


class Complex_Discrimination(Simple_Discrimination):
    """Complex Discrimination uses different stimuli (E01/D01) but identical logic to Simple Discrimination."""

    def __init__(self, chamber, trainer_config={}, trainer_config_file="~/trainer_CD_config.yaml"):
        # Set complex discrimination defaults before parent init so ensure_param picks them up
        trainer_config.setdefault("correct_image", "E01")
        trainer_config.setdefault("incorrect_image", "D01")
        trainer_config.setdefault("trainer_name", "Complex Discrimination")
        super().__init__(chamber, trainer_config, trainer_config_file)
