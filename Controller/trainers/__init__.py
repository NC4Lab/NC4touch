import importlib
from trainers.Trainer import Trainer

# Maps the trainer name (used in config/UI) to (module_path, class_name)
_TRAINER_CLASSES = {
    "DoNothingTrainer":       ("trainers.DoNothingTrainer",       "DoNothingTrainer"),
    "Habituation":            ("trainers.Habituation",            "Habituation"),
    "InitialTouch":           ("trainers.InitialTouch",           "InitialTouch"),
    "MustTouch":              ("trainers.MustTouch",              "MustTouch"),
    "Punish_Incorrect":       ("trainers.Punish_Incorrect",       "PunishIncorrect"),
    "Simple_Discrimination":  ("trainers.Simple_Discrimination",  "SimpleDiscrimination"),
    "Complex_Discrimination": ("trainers.Complex_Discrimination", "ComplexDiscrimination"),
    "PRL":                    ("trainers.PRL",                    "PRL"),
    "SoundTest":              ("trainers.SoundTest",              "SoundTest"),
}

def get_trainers():
    return list(_TRAINER_CLASSES.keys())

def get_trainer_class(trainer_name):
    """Return the trainer class for the given trainer name string."""
    if trainer_name not in _TRAINER_CLASSES:
        raise ImportError(f"Unknown trainer: {trainer_name}")
    module_path, class_name = _TRAINER_CLASSES[trainer_name]
    module = importlib.import_module(module_path)
    return getattr(module, class_name)
