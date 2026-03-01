import sys
import os
import time
import threading
import logging

# Add Controller directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'Controller')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'Controller', 'trainers')))

logging.basicConfig(level=logging.INFO, format='[%(asctime)s:%(name)s:%(levelname)s] %(message)s')
logger = logging.getLogger("automated_test")

from Virtual.VirtualChamber import VirtualChamber
from Simple_Discrimination import Simple_Discrimination
from PRL import PRL
from Punish_Incorrect import Punish_Incorrect
from InitialTouch import InitialTouch
from MustTouch import MustTouch
from Habituation import Habituation
from SoundTest import SoundTest
from Complex_Discrimination import Complex_Discrimination

def run_trainer_test(trainer_class, config_overrides, name):
    print(f"\n{'='*50}")
    print(f"Testing {name}")
    print(f"{'='*50}")

    chamber = VirtualChamber()
    chamber.initialize_m0s()
    chamber.beambreak.activate()

    trainer = trainer_class(chamber=chamber, trainer_config=config_overrides)
    
    # Run in background
    stop_event = threading.Event()
    def loop():
        trainer.start_training()
        while not stop_event.is_set() and trainer.state.name != "IDLE":
            trainer.run_training()
            time.sleep(0.05)
    
    t = threading.Thread(target=loop, daemon=True)
    t.start()

    time.sleep(1) # wait for start

    try:
        # Simulate actions based on the trainer
        for _ in range(100):  # limit to 100 sequences to avoid hanging
            time.sleep(0.5)
            state = trainer.state.name
            logger.info(f"[{name}] Current State: {state}")
            
            if state == "END_TRAINING" or state == "IDLE":
                break

            # Simulate Beambreak if needed
            if "REWARD" in state or "ITI" in state or "INITIATION" in state or "POST_REWARD" in state:
                chamber.beambreak.simulate_break()
                time.sleep(0.1)
                chamber.beambreak.simulate_restore()
            
            # Simulate Touch if needed
            if "WAIT_FOR_TOUCH" in state:
                chamber.get_left_m0().simulate_touch(100, 100)
                time.sleep(0.1)
                
    except Exception as e:
        logger.error(f"Error during {name} test: {e}")
    finally:
        stop_event.set()
        t.join(timeout=2)
        print(f"Finished testing {name}. Final state: {trainer.state.name}\n")


if __name__ == "__main__":
    # Base config for all to speed up tests
    base_config = {
        "num_trials": 2,
        "iti_duration": 1,
        "reward_pump_secs": 0.5,
        "touch_timeout": 2,
        "trainer_seq_dir": os.path.dirname(__file__),
        "trainer_seq_file": "seq_file.csv",
        "large_reward_duration": 0.5,
        "small_reward_duration": 0.5,
        "punish_duration": 0.5,
        "buzzer_duration": 0.2,
        "free_reward_duration": 0.5,
        "data_dir": ".",
        "num_loops": 1,
        "step_duration": 0.5,
        "max_iti_duration": 2,
    }

    run_trainer_test(Simple_Discrimination, base_config, "Simple_Discrimination")
    run_trainer_test(PRL, base_config, "PRL")
    run_trainer_test(Punish_Incorrect, base_config, "Punish_Incorrect")
    run_trainer_test(InitialTouch, base_config, "InitialTouch")
    run_trainer_test(MustTouch, base_config, "MustTouch")
    run_trainer_test(Habituation, base_config, "Habituation")
    run_trainer_test(SoundTest, base_config, "SoundTest")
    run_trainer_test(Complex_Discrimination, base_config, "Complex_Discrimination")

    print("\nAll automated trainer tests completed!")
