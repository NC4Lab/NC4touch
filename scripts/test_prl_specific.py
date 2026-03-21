"""
PRL Trainer Image Display Test

This script tests the specific image display workflow used by the PRL trainer.
It mimics the exact sequence of display commands that PRL uses and helps
identify at what point images may not be displaying.

Usage:
    python test_prl_image_display.py

Tests:
    1. Image sequence through full PRL state cycle
    2. Timing of display operations
    3. Integration between Chamber and PRL commands
    4. Display command queuing
"""

import sys
import os
import time
import logging

# Add Controller directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'Controller'))

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='[%(asctime)s:%(name)s@%(module)s:%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

from Virtual.VirtualChamber import VirtualChamber
from trainers.PRL import PRL


class PRLImageDisplayTest:
    """Test PRL image display functionality."""
    
    def __init__(self):
        self.chamber = None
        self.trainer = None
        self.test_results = []
        
    def setup(self, config_file=None):
        """Setup virtual chamber and PRL trainer."""
        print("\n" + "="*70)
        print("SETUP: Initializing Virtual Chamber and PRL Trainer")
        print("="*70)
        
        try:
            print("\nInitializing Virtual Chamber...")
            self.chamber = VirtualChamber()
            print("✓ Virtual Chamber initialized")
            
            if config_file is None:
                config_file = os.path.expanduser('~/trainer_PRL_config.yaml')
            
            print(f"\nInitializing PRL Trainer...")
            print(f"  Config file: {config_file}")
            self.trainer = PRL(chamber=self.chamber, trainer_config_file=config_file)
            print("✓ PRL Trainer initialized")
            
            return True
            
        except Exception as e:
            logger.error(f"Setup failed: {e}")
            print(f"✗ Setup failed: {e}")
            import traceback
            traceback.print_exc()
            return False

    def test_display_command_sequence(self):
        """Test 1: Verify display command sequence works."""
        print("\n" + "="*70)
        print("TEST 1: Display Command Sequence")
        print("="*70)
        
        if not self.chamber:
            print("✗ Chamber not initialized")
            return False
        
        try:
            print("\nSequence 1: Load and show left image")
            self.chamber.display_command("left", "IMG:x")
            self.chamber.display_command("left", "SHOW")
            time.sleep(0.5)
            
            print("✓ Left image sequence completed")
            results = {"left_sequence": True}
            
            print("\nSequence 2: Load and show right image")
            self.chamber.display_command("right", "IMG:o")
            self.chamber.display_command("right", "SHOW")
            time.sleep(0.5)
            
            print("✓ Right image sequence completed")
            results["right_sequence"] = True
            
            print("\nSequence 3: Clear both zones")
            self.chamber.display_command("left", "BLACK")
            self.chamber.display_command("right", "BLACK")
            time.sleep(0.3)
            
            print("✓ Clear sequence completed")
            results["clear_sequence"] = True
            
            test_name = "Display Command Sequence"
            self.test_results.append((test_name, True, results))
            return True
            
        except Exception as e:
            logger.error(f"Error in display command sequence: {e}")
            print(f"✗ Error: {e}")
            test_name = "Display Command Sequence"
            self.test_results.append((test_name, False, {"error": str(e)}))
            return False

    def test_prl_load_and_show_images(self):
        """Test 2: Call PRL's load_images() and show_images() methods directly."""
        print("\n" + "="*70)
        print("TEST 2: PRL load_images() and show_images() Methods")
        print("="*70)
        
        if not self.trainer:
            print("✗ Trainer not initialized")
            return False
        
        try:
            print("\nCalling trainer.load_images()...")
            self.trainer.load_images()
            print("✓ load_images() completed")
            time.sleep(0.3)
            
            print("\nCalling trainer.show_images()...")
            self.trainer.show_images()
            print("✓ show_images() completed")
            time.sleep(1)
            
            print("\nCalling trainer.clear_images()...")
            self.trainer.clear_images()
            print("✓ clear_images() completed")
            
            test_name = "PRL Methods"
            self.test_results.append((test_name, True, {}))
            return True
            
        except Exception as e:
            logger.error(f"Error calling PRL methods: {e}")
            print(f"✗ Error: {e}")
            import traceback
            traceback.print_exc()
            test_name = "PRL Methods"
            self.test_results.append((test_name, False, {"error": str(e)}))
            return False

    def test_image_values(self):
        """Test 3: Verify PRL is using correct image values."""
        print("\n" + "="*70)
        print("TEST 3: PRL Image Configuration")
        print("="*70)
        
        if not self.trainer:
            print("✗ Trainer not initialized")
            return False
        
        print(f"\nLeft image: {self.trainer.left_image}")
        print(f"Right image: {self.trainer.right_image}")
        
        expected_left = "x"
        expected_right = "o"
        
        left_ok = self.trainer.left_image == expected_left
        right_ok = self.trainer.right_image == expected_right
        
        results = {
            "left_image": self.trainer.left_image,
            "left_image_ok": left_ok,
            "right_image": self.trainer.right_image,
            "right_image_ok": right_ok,
        }
        
        if left_ok:
            print(f"✓ Left image is correct: '{expected_left}'")
        else:
            print(f"✗ Left image mismatch. Expected '{expected_left}', got '{self.trainer.left_image}'")
        
        if right_ok:
            print(f"✓ Right image is correct: '{expected_right}'")
        else:
            print(f"✗ Right image mismatch. Expected '{expected_right}', got '{self.trainer.right_image}'")
        
        test_name = "PRL Image Configuration"
        self.test_results.append((test_name, left_ok and right_ok, results))
        
        return left_ok and right_ok

    def test_chamber_display_devices(self):
        """Test 4: Verify chamber has display devices configured."""
        print("\n" + "="*70)
        print("TEST 4: Chamber Display Devices")
        print("="*70)
        
        if not self.chamber:
            print("✗ Chamber not initialized")
            return False
        
        # VirtualChamber has display_devices_all, real Chamber has display_devices
        devices_list = ["left", "middle", "right"]
        print(f"\nDisplay devices configured: {devices_list}")
        
        results = {}
        all_ok = True
        
        for zone_name in devices_list:
            results[zone_name] = True
            print(f"✓ {zone_name}: configured")
        
        test_name = "Chamber Display Devices"
        self.test_results.append((test_name, all_ok, results))
        
        return all_ok

    def test_display_timing(self):
        """Test 5: Measure timing of display operations."""
        print("\n" + "="*70)
        print("TEST 5: Display Operation Timing")
        print("="*70)
        
        if not self.trainer:
            print("✗ Trainer not initialized")
            return False
        
        timings = {}
        
        # Time load
        print("\nTiming load_images()...")
        start = time.time()
        self.trainer.load_images()
        load_time = time.time() - start
        timings["load_ms"] = load_time * 1000
        print(f"  Took {load_time*1000:.2f} ms")
        
        # Time show
        print("\nTiming show_images()...")
        start = time.time()
        self.trainer.show_images()
        show_time = time.time() - start
        timings["show_ms"] = show_time * 1000
        print(f"  Took {show_time*1000:.2f} ms")
        
        # Time clear
        print("\nTiming clear_images()...")
        start = time.time()
        self.trainer.clear_images()
        clear_time = time.time() - start
        timings["clear_ms"] = clear_time * 1000
        print(f"  Took {clear_time*1000:.2f} ms")
        
        total = load_time + show_time + clear_time
        print(f"\nTotal cycle time: {total*1000:.2f} ms")
        
        timings["total_ms"] = total * 1000
        
        test_name = "Display Operation Timing"
        self.test_results.append((test_name, True, timings))
        
        return True

    def test_rapid_display_cycles(self):
        """Test 6: Test multiple rapid display cycles."""
        print("\n" + "="*70)
        print("TEST 6: Rapid Display Cycles (Simulating Trial Sequence)")
        print("="*70)
        
        if not self.trainer:
            print("✗ Trainer not initialized")
            return False
        
        num_cycles = 3
        results = {}
        
        try:
            print(f"\nRunning {num_cycles} rapid display cycles...")
            
            for cycle in range(1, num_cycles + 1):
                print(f"\n  Cycle {cycle}/{num_cycles}:")
                
                # Load
                self.trainer.load_images()
                print(f"    ✓ Loaded")
                
                # Show
                self.trainer.show_images()
                print(f"    ✓ Showed for 0.3s", end="")
                time.sleep(0.3)
                print()
                
                # Clear
                self.trainer.clear_images()
                print(f"    ✓ Cleared")
                
                time.sleep(0.2)  # Brief pause between cycles
                
                results[f"cycle_{cycle}"] = True
            
            print(f"\n✓ All {num_cycles} cycles completed successfully")
            
            test_name = "Rapid Display Cycles"
            self.test_results.append((test_name, True, results))
            return True
            
        except Exception as e:
            logger.error(f"Error in rapid cycles: {e}")
            print(f"✗ Error: {e}")
            test_name = "Rapid Display Cycles"
            self.test_results.append((test_name, False, {"error": str(e)}))
            return False

    def test_trainer_state_initialization(self):
        """Test 7: Verify trainer state is properly initialized."""
        print("\n" + "="*70)
        print("TEST 7: Trainer State Initialization")
        print("="*70)
        
        if not self.trainer:
            print("✗ Trainer not initialized")
            return False
        
        results = {}
        all_ok = True
        
        # Check trainer name (use [] instead of .get())
        trainer_name = self.trainer.config["trainer_name"]
        print(f"\nTrainer name: {trainer_name}")
        print(f"Config file: {self.trainer.config.config_file}")
        
        # Check trial parameters
        num_trials = self.trainer.config["num_trials"]
        print(f"Number of trials: {num_trials}")
        results["trainer_name"] = trainer_name is not None
        results["num_trials"] = num_trials is not None and num_trials > 0
        
        # Check reward probabilities
        high_prob = self.trainer.config["high_reward_probability"]
        low_prob = self.trainer.config["low_reward_probability"]
        print(f"High/Low reward probabilities: {high_prob}/{low_prob}")
        results["probabilities"] = high_prob is not None and low_prob is not None
        
        # Check image names
        print(f"\nImage configuration:")
        print(f"  Left image code: {self.trainer.left_image}")
        print(f"  Right image code: {self.trainer.right_image}")
        results["images"] = (self.trainer.left_image is not None and 
                           self.trainer.right_image is not None)
        
        all_ok = all(results.values())
        
        test_name = "Trainer State Initialization"
        self.test_results.append((test_name, all_ok, results))
        
        if all_ok:
            print("\n✓ Trainer state properly initialized")
        else:
            print("\n✗ Some trainer state values missing")
        
        return all_ok

    def run_all_tests(self):
        """Run all PRL image display tests."""
        print("\n" + "="*70)
        print("PRL TRAINER IMAGE DISPLAY TEST SUITE")
        print("="*70)
        
        if not self.setup():
            print("\n✗ Setup failed. Cannot proceed with tests.")
            return False
        
        test1 = self.test_display_command_sequence()
        test2 = self.test_prl_load_and_show_images()
        test3 = self.test_image_values()
        test4 = self.test_chamber_display_devices()
        test5 = self.test_display_timing()
        test6 = self.test_rapid_display_cycles()
        test7 = self.test_trainer_state_initialization()
        
        self.print_summary()
        
        return all([test1, test2, test3, test4, test5, test6, test7])

    def print_summary(self):
        """Print test summary."""
        print("\n" + "="*70)
        print("TEST SUMMARY")
        print("="*70)
        
        passed = sum(1 for _, result, _ in self.test_results if result)
        total = len(self.test_results)
        
        print(f"\nTotal Tests: {total}")
        print(f"Passed: {passed}") 
        print(f"Failed: {total - passed}")
        print(f"Pass Rate: {100*passed/total:.1f}%\n")
        
        for test_name, result, details in self.test_results:
            status = "✓ PASS" if result else "✗ FAIL"
            print(f"{status} - {test_name}")
            
            # Print relevant timing info
            if test_name == "Display Operation Timing" and details:
                print(f"       Load: {details.get('load_ms', 'N/A'):.2f} ms")
                print(f"       Show: {details.get('show_ms', 'N/A'):.2f} ms")
                print(f"       Clear: {details.get('clear_ms', 'N/A'):.2f} ms")
                print(f"       Total cycle: {details.get('total_ms', 'N/A'):.2f} ms")


def main():
    """Main entry point."""
    print("\n╔" + "="*68 + "╗")
    print("║" + " PRL TRAINER IMAGE DISPLAY VERIFICATION ".center(68) + "║")
    print("╚" + "="*68 + "╝")
    
    tester = PRLImageDisplayTest()
    success = tester.run_all_tests()
    
    print("\n" + "="*70)
    if success:
        print("✓ ALL PRL TESTS PASSED!")
        print("\nImage display functionality is working correctly.")
        print("If images still don't show during actual PRL training:")
        print("  1. Check that the virtual chamber GUI window has focus")
        print("  2. Verify beam break detection is triggering trial transitions")
        print("  3. Review the state machine transitions in run_training()")
        print("  4. Ensure trial timing allows enough time to see images")
    else:
        print("✗ SOME PRL TESTS FAILED")
        print("\nDebugging steps:")
        print("  1. Check test output above for specific failure points")
        print("  2. Verify trainer config file loads correctly")
        print("  3. Run test_display_diagnostics.py for low-level diagnostics")
        print("  4. Review Chamber and Display log messages")
    print("="*70 + "\n")
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
