from trainers.Trainer import Trainer

def get_trainers():
    return [
        "DoNothingTrainer",
        "Habituation",
        "InitialTouch",
        "MustTouch",
        "Punish_Incorrect",
        "Simple_Discrimination",
        "Complex_Discrimination",
        "PRL",
        "SoundTest",
    ]
