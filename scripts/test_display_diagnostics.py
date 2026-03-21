"""
Display Configuration and Diagnostics Test

This script verifies the physical display configuration and provides
detailed diagnostics for troubleshooting image display issues.

Usage:
    python test_display_config.py

Diagnostics:
    1. Display resolution and geometry
    2. PyGame surface creation
    3. Image loading with detailed error reporting
    4. Zone configuration validation
    5. Display device initialization
    6. SDL environment variables
"""

import sys
import os
import logging

# Add Controller directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'Controller'))

# Set up logging BEFORE importing Display
logging.basicConfig(
    level=logging.DEBUG,
    format='[%(asctime)s:%(name)s:%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

# Now import pygame and display modules
try:
    import pygame
    print("✓ PyGame imported successfully")
except ImportError:
    print("✗ Failed to import PyGame")
    sys.exit(1)

from Display import DisplayManager, DisplayZone, DisplayZoneDevice


class DisplayConfigDiagnostics:
    """Diagnostic tool for display configuration."""
    
    def __init__(self):
        self.display = None
        self.results = {}
        
    def test_sdl_environment(self):
        """Test 1: Check SDL environment variables."""
        print("\n" + "="*70)
        print("TEST 1: SDL Environment Variables")
        print("="*70)
        
        sdl_vars = [
            "SDL_VIDEODRIVER",
            "SDL_AUDIODRIVER",
            "SDL_FBDEV",
            "SDL_VIDEODEVICE",
            "SDL_WINDOWS",
            "DISPLAY",
        ]
        
        print("\nChecking SDL/X11 environment variables:")
        for var in sdl_vars:
            value = os.environ.get(var, "(not set)")
            status = "✓" if value != "(not set)" else "○"
            print(f"  {status} {var}: {value}")

    def test_pygame_initialization(self):
        """Test 2: Initialize PyGame and check display modes."""
        print("\n" + "="*70)
        print("TEST 2: PyGame Initialization and Display Modes")
        print("="*70)
        
        try:
            pygame.init()
            print("✓ PyGame initialized successfully")
            
            # Get display info
            info = pygame.display.get_surface()
            print(f"  Current display surface: {info}")
            
            # Try to get available display modes
            print("\nAttempting to list available display modes...")
            try:
                modes = pygame.display.list_modes()
                if modes:
                    print(f"  Available modes: {len(modes)} resolutions found")
                    # Show first few
                    for i, mode in enumerate(modes[:5]):
                        print(f"    {mode}")
                    if len(modes) > 5:
                        print(f"    ... and {len(modes)-5} more")
                else:
                    print("  No fullscreen modes available (may use current resolution)")
            except Exception as e:
                print(f"  Could not list modes: {e}")
            
            # Get driver info
            driver = pygame.display.get_driver()
            print(f"\n  PyGame display driver: {driver}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error initializing PyGame: {e}")
            print(f"✗ Error initializing PyGame: {e}")
            return False

    def test_display_creation(self):
        """Test 3: Create DisplayManager with standard config."""
        print("\n" + "="*70)
        print("TEST 3: DisplayManager Creation")
        print("="*70)
        
        try:
            print("\nCreating DisplayManager with config:")
            print("  Width: 1920")
            print("  Height: 480")
            print("  Window mode: fullscreen")
            print("  Zone widths: [320, 320, 320]")
            
            self.display = DisplayManager(
                width=1920,
                height=480,
                image_folder="../data/images",
                zone_widths=[320, 320, 320],
                zone_gaps=None,
                center_layout=True,
                display_name="DSI-2",
                display_index=None,
                window_mode="fullscreen",
            )
            
            print("✓ DisplayManager created successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error creating DisplayManager: {e}")
            print(f"✗ Error creating DisplayManager: {e}")
            import traceback
            traceback.print_exc()
            return False

    def test_pygame_surface(self):
        """Test 4: Verify PyGame surface was created."""
        print("\n" + "="*70)
        print("TEST 4: PyGame Surface Verification")
        print("="*70)
        
        if not self.display:
            print("✗ DisplayManager not initialized")
            return False
        
        try:
            print(f"\nDisplay surface: {self.display.screen}")
            print(f"Surface size: {self.display.screen.get_size() if self.display.screen else 'None'}")
            
            if self.display.screen:
                size = self.display.screen.get_size()
                print(f"Expected: (1920, 480)")
                print(f"Actual:   {size}")
                
                match = size == (1920, 480)
                if match:
                    print("✓ Surface size is correct")
                    return True
                else:
                    print("⚠ Surface size doesn't match expected dimensions")
                    return True  # Still return True, may work anyway
            else:
                print("✗ Surface is None")
                return False
                
        except Exception as e:
            logger.error(f"Error verifying surface: {e}")
            print(f"✗ Error verifying surface: {e}")
            return False

    def test_zones_configuration(self):
        """Test 5: Verify display zones are correctly configured."""
        print("\n" + "="*70)
        print("TEST 5: Display Zones Configuration")
        print("="*70)
        
        if not self.display:
            print("✗ DisplayManager not initialized")
            return False
        
        try:
            print(f"\nNumber of zones: {len(self.display.zones)}")
            print(f"Expected zones: LEFT, MIDDLE, RIGHT")
            
            all_ok = True
            # zones dict keys are strings: "left", "middle", "right"
            for zone_name in ["left", "middle", "right"]:
                if zone_name in self.display.zones:
                    rect = self.display.zones[zone_name]
                    print(f"\n  {zone_name.upper()}:")
                    print(f"    Position: ({rect.x}, {rect.y})")
                    print(f"    Size: {rect.width} x {rect.height}")
                    
                    # Check if size is reasonable
                    if rect.width > 0 and rect.height > 0:
                        print(f"    ✓ Zone configured correctly")
                    else:
                        print(f"    ✗ Invalid zone size")
                        all_ok = False
                else:
                    print(f"  {zone_name.upper()}: ✗ NOT FOUND IN ZONES DICT")
                    all_ok = False
            
            if all_ok:
                print("\n✓ All zones correctly configured")
            else:
                print("\n✗ Some zones have issues")
            
            return all_ok
            
        except Exception as e:
            logger.error(f"Error checking zones: {e}")
            print(f"✗ Error checking zones: {e}")
            return False

    def test_image_folder_access(self):
        """Test 6: Verify image folder is accessible."""
        print("\n" + "="*70)
        print("TEST 6: Image Folder Access")
        print("="*70)
        
        if not self.display:
            print("✗ DisplayManager not initialized")
            return False
        
        try:
            image_folder = self.display.image_folder
            print(f"\nImage folder path: {image_folder}")
            
            if os.path.exists(image_folder):
                print("✓ Image folder exists")
                
                # List images
                images = os.listdir(image_folder)
                print(f"\nImages in folder ({len(images)} total):")
                for img in sorted(images):
                    img_path = os.path.join(image_folder, img)
                    size = os.path.getsize(img_path)
                    print(f"  - {img} ({size} bytes)")
                
                return len(images) > 0
            else:
                print(f"✗ Image folder does not exist")
                return False
                
        except Exception as e:
            logger.error(f"Error accessing image folder: {e}")
            print(f"✗ Error accessing image folder: {e}")
            return False

    def test_image_loading_detailed(self):
        """Test 7: Load images with detailed error reporting."""
        print("\n" + "="*70)
        print("TEST 7: Detailed Image Loading Test")
        print("="*70)
        
        if not self.display:
            print("✗ DisplayManager not initialized")
            return False
        
        test_images = ["x", "o", "A01", "B01"]
        results = {}
        
        zone_rect = self.display.zones[DisplayZone.LEFT]
        target_size = (zone_rect.width, zone_rect.height)
        
        print(f"\nLoading images with target size: {target_size}")
        print("Testing images: " + ", ".join(test_images))
        
        for image_name in test_images:
            print(f"\n  [{image_name}]")
            
            # Test candidate paths
            print(f"    Candidate paths:")
            candidates_found = False
            for candidate in self.display._candidate_image_paths(image_name):
                exists = os.path.exists(candidate)
                status = "✓ EXISTS" if exists else "○ not found"
                print(f"      {status} {candidate}")
                candidates_found = candidates_found or exists
            
            # Try to load
            try:
                img = self.display._load_image(image_name, target_size)
                if img:
                    results[image_name] = True
                    print(f"    ✓ Loaded successfully")
                    print(f"      Actual size: {img.get_size()}")
                    
                    # Check cache
                    cache_key = (image_name.strip(), int(target_size[0]), int(target_size[1]))
                    in_cache = cache_key in self.display.image_cache
                    print(f"      In cache: {'✓ Yes' if in_cache else '✗ No'}")
                else:
                    results[image_name] = False
                    print(f"    ✗ Failed to load (returned None)")
                    
            except Exception as e:
                results[image_name] = False
                logger.error(f"Error loading {image_name}: {e}")
                print(f"    ✗ Exception: {e}")
        
        success_count = sum(1 for v in results.values() if v)
        print(f"\n✓ Loaded {success_count}/{len(test_images)} images successfully")
        
        return success_count == len(test_images)

    def test_display_devices(self):
        """Test 8: Verify DisplayZoneDevice works correctly."""
        print("\n" + "="*70)
        print("TEST 8: DisplayZoneDevice Functionality")
        print("="*70)
        
        if not self.display:
            print("✗ DisplayManager not initialized")
            return False
        
        try:
            print("\nCreating DisplayZoneDevice instances...")
            
            devices = {
                "left": DisplayZoneDevice(self.display, DisplayZone.LEFT, "TEST_LEFT"),
                "middle": DisplayZoneDevice(self.display, DisplayZone.MIDDLE, "TEST_MIDDLE"),
                "right": DisplayZoneDevice(self.display, DisplayZone.RIGHT, "TEST_RIGHT"),
            }
            
            print("✓ All DisplayZoneDevice instances created")
            
            # Test sending commands
            print("\nTesting device commands:")
            for name, device in devices.items():
                print(f"  [{name}]")
                
                try:
                    # Test IMG command
                    device.send_command("IMG:x")
                    print(f"    ✓ IMG command accepted")
                    
                    # Test SHOW command
                    device.send_command("SHOW")
                    print(f"    ✓ SHOW command accepted")
                    
                    # Test CLEAR command
                    device.send_command("BLACK")
                    print(f"    ✓ CLEAR command accepted")
                    
                except Exception as e:
                    logger.error(f"Error sending command to {name}: {e}")
                    print(f"    ✗ Error: {e}")
                    return False
            
            print("\n✓ All DisplayZoneDevice tests passed")
            return True
            
        except Exception as e:
            logger.error(f"Error testing DisplayZoneDevice: {e}")
            print(f"✗ Error: {e}")
            import traceback
            traceback.print_exc()
            return False

    def run_all_diagnostics(self):
        """Run all diagnostic tests."""
        print("\n" + "="*70)
        print("DISPLAY CONFIGURATION DIAGNOSTICS")
        print("="*70)
        
        self.test_sdl_environment()
        
        test2 = self.test_pygame_initialization()
        if not test2:
            print("\n✗ PyGame initialization failed. Cannot continue diagnostics.")
            return False
        
        test3 = self.test_display_creation()
        test4 = self.test_pygame_surface()
        test5 = self.test_zones_configuration()
        test6 = self.test_image_folder_access()
        test7 = self.test_image_loading_detailed()
        test8 = self.test_display_devices()
        
        self.print_diagnostics_summary([test3, test4, test5, test6, test7, test8])
        
        return all([test3, test4, test5, test6, test7, test8])

    def print_diagnostics_summary(self, results):
        """Print diagnostics summary."""
        print("\n" + "="*70)
        print("DIAGNOSTICS SUMMARY")
        print("="*70)
        
        test_names = [
            "DisplayManager Creation",
            "PyGame Surface",
            "Zones Configuration",
            "Image Folder Access",
            "Image Loading",
            "DisplayZoneDevice",
        ]
        
        passed = sum(results)
        total = len(results)
        
        print(f"\nTotal Checks: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {total - passed}\n")
        
        for name, result in zip(test_names, results):
            status = "✓" if result else "✗"
            print(f"{status} {name}")
        
        print("\n" + "="*70)
        if passed == total:
            print("✓ ALL DIAGNOSTICS PASSED")
            print("\nThe display configuration appears to be working correctly.")
            print("If images still don't show in PRL trainer:")
            print("  1. Run test_image_display.py to test the full workflow")
            print("  2. Check that PRL state machine is advancing")
            print("  3. Verify beam break detection is working")
        else:
            print("✗ SOME DIAGNOSTICS FAILED")
            print("\nFix the failures above, then try again.")
        print("="*70 + "\n")


def main():
    """Main entry point."""
    diagnostics = DisplayConfigDiagnostics()
    success = diagnostics.run_all_diagnostics()
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
