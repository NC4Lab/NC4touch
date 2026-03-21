"""
Image Display Test Suite

This script tests image display functionality on the operant display.
It verifies that images are loaded, displayed, and cleared correctly.

Usage:
    python test_image_display.py

Tests:
    1. Image file existence
    2. Image loading and caching
    3. Image display on individual zones
    4. Image display on all zones
    5. Clear display operations
    6. PRL trainer image display workflow
    7. Display zone configuration
"""

import sys
import os
import time
import logging

# Add Controller directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'Controller'))

from Display import DisplayManager, DisplayZone
from Virtual.VirtualChamber import VirtualChamber
from Virtual.VirtualChamberGUI import VirtualChamberGUI

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='[%(asctime)s:%(name)s@%(module)s:%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)


class ImageDisplayTester:
    """Test suite for image display functionality."""
    
    def __init__(self, use_virtual=True):
        """Initialize the display tester."""
        self.use_virtual = use_virtual
        self.chamber = None
        self.display = None
        self.test_results = []
        
    def test_image_files_exist(self):
        """Test 1: Verify all expected image files exist."""
        print("\n" + "="*70)
        print("TEST 1: Image Files Exist")
        print("="*70)
        
        # Expected images for PRL trainer
        expected_images = ["x", "o", "A01", "B01", "C01"]
        
        # Get image folder path
        code_dir = os.path.dirname(os.path.abspath(__file__))
        image_folder = os.path.abspath(os.path.join(code_dir, "../", "data", "images"))
        
        print(f"Image folder: {image_folder}")
        print(f"Checking for images: {expected_images}")
        
        results = {}
        all_exist = True
        
        for image_name in expected_images:
            # Check for both .bmp and .png
            bmp_path = os.path.join(image_folder, f"{image_name}.bmp")
            png_path = os.path.join(image_folder, f"{image_name}.png")
            
            bmp_exists = os.path.exists(bmp_path)
            png_exists = os.path.exists(png_path)
            
            exists = bmp_exists or png_exists
            all_exist = all_exist and exists
            
            status = "✓ EXISTS" if exists else "✗ MISSING"
            results[image_name] = exists
            
            if bmp_exists and png_exists:
                print(f"  {image_name}: {status} (both .bmp and .png)")
            elif bmp_exists:
                print(f"  {image_name}: {status} (.bmp)")
            elif png_exists:
                print(f"  {image_name}: {status} (.png)")
            else:
                print(f"  {image_name}: {status}")
        
        test_name = "Image Files Exist"
        self.test_results.append((test_name, all_exist, results))
        
        if all_exist:
            print("\n✓ All expected image files exist!")
            return True
        else:
            print("\n✗ Some image files are missing!")
            return False

    def setup_virtual_display(self):
        """Setup virtual chamber and display."""
        print("\nSetting up virtual chamber and display manager...")
        try:
            # Initialize virtual chamber for other components
            self.chamber = VirtualChamber()
            print("✓ Virtual chamber initialized")
            
            # Create DisplayManager directly (independent of chamber/device)
            from Display import DisplayManager
            self.display = DisplayManager(
                width=1920,
                height=480,
                image_folder="../data/images",
                zone_widths=[320, 320, 320],
                zone_gaps=None,
                center_layout=True,
                window_mode="fullscreen",
            )
            print("✓ DisplayManager initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize: {e}")
            print(f"✗ Failed to initialize: {e}")
            import traceback
            traceback.print_exc()
            return False

    def test_image_loading(self):
        """Test 2: Verify images load into memory cache."""
        print("\n" + "="*70)
        print("TEST 2: Image Loading and Caching")
        print("="*70)
        
        if not self.chamber:
            print("✗ Chamber not initialized. Skipping test.")
            return False
        
        test_images = ["x", "o"]
        results = {}
        all_loaded = True
        
        for image_name in test_images:
            try:
                # Load image using the display's internal method
                zone_rect = self.display.zones[DisplayZone.LEFT]
                img = self.display._load_image(image_name, (zone_rect.width, zone_rect.height))
                
                loaded = img is not None
                results[image_name] = loaded
                all_loaded = all_loaded and loaded
                
                status = "✓ LOADED" if loaded else "✗ FAILED"
                print(f"  {image_name}: {status}")
                
                if loaded:
                    print(f"    Image size: {img.get_size()}")
                    print(f"    Cached: {(image_name, zone_rect.width, zone_rect.height) in self.display.image_cache}")
                    
            except Exception as e:
                logger.error(f"Error loading {image_name}: {e}")
                results[image_name] = False
                all_loaded = False
                print(f"  {image_name}: ✗ ERROR - {e}")
        
        test_name = "Image Loading and Caching"
        self.test_results.append((test_name, all_loaded, results))
        
        if all_loaded:
            print("\n✓ All images loaded successfully!")
            return True
        else:
            print("\n✗ Some images failed to load!")
            return False

    def test_display_zones_configured(self):
        """Test 3: Verify display zones are properly configured."""
        print("\n" + "="*70)
        print("TEST 3: Display Zones Configuration")
        print("="*70)
        
        if not self.display:
            print("✗ Display not initialized. Skipping test.")
            return False
        
        print(f"Display resolution: {self.display.width} x {self.display.height}")
        print(f"Number of zones: {len(self.display.zones)}")
        
        results = {}
        all_configured = True
        
        # zones dict keys are strings: "left", "middle", "right"
        for zone_name in ["left", "middle", "right"]:
            if zone_name in self.display.zones:
                zone_rect = self.display.zones[zone_name]
                results[zone_name.upper()] = True
                print(f"  {zone_name.upper()}:")
                print(f"    Position: ({zone_rect.x}, {zone_rect.y})")
                print(f"    Size: {zone_rect.width} x {zone_rect.height}")
            else:
                results[zone_name.upper()] = False
                all_configured = False
                print(f"  {zone_name.upper()}: ✗ NOT CONFIGURED")
        
        test_name = "Display Zones Configuration"
        self.test_results.append((test_name, all_configured, results))
        
        if all_configured:
            print("\n✓ All display zones properly configured!")
            return True
        else:
            print("\n✗ Some display zones not configured!")
            return False

    def test_show_image_single_zone(self):
        """Test 4: Display image on a single zone."""
        print("\n" + "="*70)
        print("TEST 4: Display Image on Single Zone")
        print("="*70)
        
        if not self.chamber:
            print("✗ Chamber not initialized. Skipping test.")
            return False
        
        results = {}
        all_passed = True
        
        # Use string zone names since DisplayZone attributes are strings
        test_cases = [
            ("left", "x"),
            ("middle", "o"),
            ("right", "x"),
        ]
        
        for zone_name, image_name in test_cases:
            try:
                print(f"\n  Displaying '{image_name}' on {zone_name.upper()}...")
                self.display.show_image(zone_name, image_name)
                results[f"{zone_name.upper()}__{image_name}"] = True
                print(f"    ✓ Successfully displayed")
                time.sleep(0.5)  # Brief display time
                
            except Exception as e:
                logger.error(f"Error displaying {image_name} on {zone_name}: {e}")
                results[f"{zone_name.upper()}__{image_name}"] = False
                all_passed = False
                print(f"    ✗ Error: {e}")
        
        test_name = "Display Image on Single Zone"
        self.test_results.append((test_name, all_passed, results))
        
        if all_passed:
            print("\n✓ All single-zone display tests passed!")
            return True
        else:
            print("\n✗ Some single-zone display tests failed!")
            return False

    def test_display_multiple_images(self):
        """Test 5: Display different images on multiple zones simultaneously."""
        print("\n" + "="*70)
        print("TEST 5: Display Multiple Images (Different Images on Each Zone)")
        print("="*70)
        
        if not self.chamber:
            print("✗ Chamber not initialized. Skipping test.")
            return False
        
        try:
            print("\n  Displaying 'x' on LEFT, 'o' on MIDDLE, 'A01' on RIGHT...")
            self.display.show_image("left", "x")
            self.display.show_image("middle", "o")
            self.display.show_image("right", "A01")
            print("  ✓ All three zones updated")
            time.sleep(1.5)
            
            test_name = "Display Multiple Images"
            self.test_results.append((test_name, True, {}))
            return True
            
        except Exception as e:
            logger.error(f"Error displaying multiple images: {e}")
            print(f"  ✗ Error: {e}")
            test_name = "Display Multiple Images"
            self.test_results.append((test_name, False, {"error": str(e)}))
            return False

    def test_clear_image(self):
        """Test 6: Clear (black out) individual zones."""
        print("\n" + "="*70)
        print("TEST 6: Clear Display Zones")
        print("="*70)
        
        if not self.chamber:
            print("✗ Chamber not initialized. Skipping test.")
            return False
        
        results = {}
        all_passed = True
        
        zones_to_clear = ["left", "middle", "right"]
        
        for zone_name in zones_to_clear:
            try:
                print(f"\n  Clearing {zone_name.upper()}...")
                self.display.clear(zone_name)
                results[zone_name.upper()] = True
                print(f"    ✓ Successfully cleared")
                time.sleep(0.3)
                
            except Exception as e:
                logger.error(f"Error clearing {zone_name}: {e}")
                results[zone_name.upper()] = False
                all_passed = False
                print(f"    ✗ Error: {e}")
        
        test_name = "Clear Display Zones"
        self.test_results.append((test_name, all_passed, results))
        
        if all_passed:
            print("\n✓ All clear operations successful!")
            return True
        else:
            print("\n✗ Some clear operations failed!")
            return False

    def test_prl_workflow(self):
        """Test 7: Simulate PRL trainer image display workflow."""
        print("\n" + "="*70)
        print("TEST 7: PRL Trainer Workflow Simulation")
        print("="*70)
        
        if not self.chamber:
            print("✗ Chamber not initialized. Skipping test.")
            return False
        
        results = {}
        
        try:
            print("\n  Simulating PRL trainer workflow...")
            
            # Step 1: Load images (same as PRL.load_images())
            print("\n  Step 1: Loading images...")
            left_image = "x"
            right_image = "o"
            self.chamber.display_command("left", f"IMG:{left_image}")
            self.chamber.display_command("right", f"IMG:{right_image}")
            results["load_left"] = True
            results["load_right"] = True
            print("    ✓ Images loaded")
            time.sleep(0.3)
            
            # Step 2: Show images (same as PRL.show_images())
            print("\n  Step 2: Showing images...")
            self.chamber.display_command("left", "SHOW")
            self.chamber.display_command("right", "SHOW")
            results["show_left"] = True
            results["show_right"] = True
            print("    ✓ Images displayed")
            time.sleep(1)
            
            # Step 3: Clear images (same as PRL.clear_images())
            print("\n  Step 3: Clearing images...")
            self.chamber.display_command("left", "BLACK")
            self.chamber.display_command("right", "BLACK")
            results["clear_left"] = True
            results["clear_right"] = True
            print("    ✓ Images cleared")
            
            all_passed = all(results.values())
            test_name = "PRL Trainer Workflow Simulation"
            self.test_results.append((test_name, all_passed, results))
            
            if all_passed:
                print("\n✓ PRL workflow simulation completed successfully!")
                return True
            else:
                print("\n✗ PRL workflow simulation failed!")
                return False
                
        except Exception as e:
            logger.error(f"Error in PRL workflow: {e}")
            print(f"  ✗ Error: {e}")
            test_name = "PRL Trainer Workflow Simulation"
            self.test_results.append((test_name, False, {"error": str(e)}))
            return False

    def test_image_cache_effectiveness(self):
        """Test 8: Verify image caching improves performance."""
        print("\n" + "="*70)
        print("TEST 8: Image Cache Effectiveness")
        print("="*70)
        
        if not self.display:
            print("✗ Display not initialized. Skipping test.")
            return False
        
        import time
        
        # Clear cache
        cache_size_before = len(self.display.image_cache)
        print(f"Cache size before: {cache_size_before} images")
        
        # First load (should load from disk)
        start = time.time()
        zone_rect = self.display.zones["left"]
        img1 = self.display._load_image("x", (zone_rect.width, zone_rect.height))
        first_load_time = time.time() - start
        
        cache_size_after_first = len(self.display.image_cache)
        print(f"Cache size after first load: {cache_size_after_first} images")
        print(f"First load time: {first_load_time*1000:.2f} ms")
        
        # Second load (should load from cache)
        start = time.time()
        img2 = self.display._load_image("x", (zone_rect.width, zone_rect.height))
        cached_load_time = time.time() - start
        
        print(f"Cached load time: {cached_load_time*1000:.2f} ms")
        
        # Cached should be significantly faster
        speedup = first_load_time / cached_load_time if cached_load_time > 0 else float('inf')
        speedup_factor = max(1, speedup)
        
        cache_effective = cache_size_after_first > cache_size_before
        speedup_effective = speedup_factor > 2  # At least 2x faster when cached
        
        all_passed = cache_effective and speedup_effective
        
        results = {
            "cache_populated": cache_effective,
            "speedup_factor": speedup_factor,
            "speedup_effective": speedup_effective,
            "first_load_ms": f"{first_load_time*1000:.2f}",
            "cached_load_ms": f"{cached_load_time*1000:.2f}",
        }
        
        test_name = "Image Cache Effectiveness"
        self.test_results.append((test_name, all_passed, results))
        
        if all_passed:
            print("\n✓ Image caching is working effectively!")
            print(f"  Speedup factor: {speedup_factor:.1f}x")
            return True
        else:
            print("\n✗ Image caching is not effective!")
            if not cache_effective:
                print("  Cache was not populated")
            if not speedup_effective:
                print(f"  Speedup factor {speedup_factor:.1f}x is below 2x threshold")
            return False

    def run_all_tests(self):
        """Run all display tests."""
        print("\n" + "="*70)
        print("IMAGE DISPLAY TEST SUITE")
        print("="*70)
        
        # Test 1: Image files
        test1 = self.test_image_files_exist()
        
        # Setup display
        if not self.setup_virtual_display():
            print("\n✗ Cannot proceed without display. Aborting remaining tests.")
            self.print_summary()
            return False
        
        # Test 2-8: Display tests
        test2 = self.test_image_loading()
        test3 = self.test_display_zones_configured()
        test4 = self.test_show_image_single_zone()
        test5 = self.test_display_multiple_images()
        test6 = self.test_clear_image()
        test7 = self.test_prl_workflow()
        test8 = self.test_image_cache_effectiveness()
        
        self.print_summary()
        
        # Return True only if all tests passed
        return all([test1, test2, test3, test4, test5, test6, test7, test8])

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
            if details and len(str(details)) < 100:
                print(f"       Details: {details}")


def main():
    """Main entry point."""
    print("\n╔" + "="*68 + "╗")
    print("║" + " IMAGE DISPLAY VERIFICATION TEST SUITE ".center(68) + "║")
    print("╚" + "="*68 + "╝")
    
    tester = ImageDisplayTester(use_virtual=True)
    success = tester.run_all_tests()
    
    print("\n" + "="*70)
    if success:
        print("✓ ALL TESTS PASSED!")
        print("\nImages should display correctly on the PRL trainer.")
        print("If images are still not showing during PRL training, check:")
        print("  1. Virtual chamber GUI window is open and focused")
        print("  2. BeamBreak/touch detection is working")
        print("  3. Trial state machine is advancing correctly")
        print("  4. Image names match filenames in data/images/")
    else:
        print("✗ SOME TESTS FAILED")
        print("\nDebug steps:")
        print("  1. Check the test output above for specific failures")
        print("  2. Verify image files exist in data/images/")
        print("  3. Check display configuration in Chamber.py")
        print("  4. Review error messages in logs")
    print("="*70 + "\n")
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
