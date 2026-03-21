"""
PRL Hardware Display Test

Tests image display on real hardware during PRL training.
Run this to diagnose why images might not be showing.

Usage:
    python test_prl_hardware_display.py
"""

import sys
import os
import time

# Add Controller directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'Controller'))

from Chamber import Chamber
from trainers.PRL import PRL
import logging

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='[%(asctime)s:%(name)s@%(module)s:%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)


def test_display_initialization():
    """Test 1: Verify Chamber and Display initialize correctly."""
    print("\n" + "="*70)
    print("TEST 1: Chamber and Display Initialization")
    print("="*70)
    
    try:
        print("\nInitializing Chamber...")
        chamber = Chamber()
        
        print("✓ Chamber initialized")
        print(f"  Display resolution: {chamber.display.width} x {chamber.display.height}")
        print(f"  Zones configured: {len(chamber.display.zones)}")
        
        # Test that display devices exist
        print(f"\nDisplay devices configured:")
        for zone_name in ["left", "middle", "right"]:
            if zone_name in chamber.display_devices:
                device = chamber.display_devices[zone_name]
                print(f"  ✓ {zone_name}: {device.id}")
            else:
                print(f"  ✗ {zone_name}: NOT FOUND")
                return False
        
        return chamber
        
    except Exception as e:
        logger.error(f"Failed to initialize Chamber: {e}")
        print(f"✗ Initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_direct_image_display(chamber):
    """Test 2: Display images directly without PRL state machine."""
    print("\n" + "="*70)
    print("TEST 2: Direct Image Display (Manual Commands)")
    print("="*70)
    
    try:
        print("\nTest sequence:")
        print("1. Loading 'x' image on left zone")
        chamber.display_command("left", "IMG:x")
        
        print("2. Loading 'o' image on right zone")
        chamber.display_command("right", "IMG:o")
        
        print("3. Showing left image")
        chamber.display_command("left", "SHOW")
        
        print("4. Showing right image")
        chamber.display_command("right", "SHOW")
        
        print("5. Displaying for 3 seconds...")
        time.sleep(3)
        
        print("6. Clearing display")
        chamber.display_command("left", "BLACK")
        chamber.display_command("right", "BLACK")
        
        print("✓ Direct image display test completed")
        return True
        
    except Exception as e:
        logger.error(f"Error during direct display test: {e}")
        print(f"✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_prl_image_loading(chamber):
    """Test 3: Test PRL's load_images() and show_images() methods."""
    print("\n" + "="*70)
    print("TEST 3: PRL Image Loading Methods")
    print("="*70)
    
    try:
        print("\nInitializing PRL trainer...")
        trainer = PRL(chamber=chamber)
        print("✓ PRL trainer initialized")
        
        print("\nPRL configuration:")
        print(f"  Left image: {trainer.left_image}")
        print(f"  Right image: {trainer.right_image}")
        
        print("\nCalling trainer.load_images()...")
        trainer.load_images()
        
        print("Calling trainer.show_images()...")
        trainer.show_images()
        
        print("Displaying for 3 seconds...")
        time.sleep(3)
        
        print("Calling trainer.clear_images()...")
        trainer.clear_images()
        
        print("✓ PRL image loading test completed")
        return True
        
    except Exception as e:
        logger.error(f"Error during PRL image loading test: {e}")
        print(f"✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_prl_state_machine_cycle(chamber):
    """Test 4: Run PRL state machine for one complete trial cycle."""
    print("\n" + "="*70)
    print("TEST 4: PRL State Machine - One Trial Cycle")
    print("="*70)
    
    try:
        print("\nInitializing PRL trainer with minimal config...")
        trainer_config = {
            "num_trials": 1,  # Just run one trial
            "touch_timeout": 5,  # 5 second timeout
            "iti_duration": 2,
        }
        trainer = PRL(chamber=chamber, trainer_config=trainer_config)
        print("✓ PRL trainer initialized")
        
        print("\nCalling trainer.start_training()...")
        trainer.start_training()
        
        print("\nRunning state machine for one complete cycle...")
        print("(This will load/show images during START_TRIAL state)")
        
        # Run through one complete trial cycle
        max_iterations = 200  # Max 20 seconds (0.1s per iteration)
        iteration = 0
        
        while iteration < max_iterations:
            current_state = trainer.state.name if hasattr(trainer.state, 'name') else str(trainer.state)
            logger.debug(f"[Iteration {iteration}] State: {current_state}")
            
            trainer.run_training()
            
            if current_state == "END_TRIAL":
                print(f"\n✓ Trial cycle completed at iteration {iteration}")
                print(f"  Final state: {current_state}")
                break
            
            time.sleep(0.1)  # Same interval as Session
            iteration += 1
        
        if iteration >= max_iterations:
            print(f"\n⚠ State machine did not complete trial within {max_iterations} iterations")
            print(f"  Stopped at state: {current_state}")
        
        # Clean up
        print("\nCleaning up...")
        trainer.clear_images()
        
        return True
        
    except Exception as e:
        logger.error(f"Error during state machine test: {e}")
        print(f"✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main entry point."""
    print("\n" + "="*70)
    print("PRL HARDWARE DISPLAY TEST")
    print("="*70)
    
    # Test 1: Initialization
    chamber = test_display_initialization()
    if chamber is None:
        print("\n✗ Cannot proceed without properly initialized Chamber")
        return 1
    
    # Test 2: Direct display
    if not test_direct_image_display(chamber):
        print("\n⚠ Direct display test failed")
    
    # Test 3: PRL methods
    if not test_prl_image_loading(chamber):
        print("\n⚠ PRL image loading test failed")
    
    # Test 4: State machine
    if not test_prl_state_machine_cycle(chamber):
        print("\n⚠ PRL state machine test failed")
    
    print("\n" + "="*70)
    print("DIAGNOSTICS COMPLETE")
    print("="*70)
    print("\nDiagnosis summary:")
    print("1. If images showed during tests 2-4, the hardware is working")
    print("2. If images didn't show:")
    print("   - Check display cable connection")
    print("   - Verify display resolution with: xrandr or wlr-randr")
    print("   - Check logs for pygame/SDL errors")
    print("   - Try running with SDL debug: SDL_VIDEODRIVER=x11 python ...")
    print("3. Review Chamber and Display logs above for error messages")
    print("="*70 + "\n")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
