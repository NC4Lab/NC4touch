# Image Display Testing Guide

This directory contains comprehensive tests to verify that images are displaying correctly on the operant display for the PRL trainer.

## Test Files

### 1. `test_image_display.py` - Full Integration Test
**Purpose**: Complete end-to-end test of image display functionality

**Tests**:
- Image files exist in data/images/
- Images load into memory cache
- Display zones are properly configured
- Single zone image display
- Multiple zone image display simultaneously
- Display clearing operations
- Full PRL workflow simulation
- Image caching performance

**Run**:
```bash
cd /home/nc4touch/NC4touch/scripts
python test_image_display.py
```

**Good for**: Verifying that the entire image display pipeline works

---

### 2. `test_display_diagnostics.py` - Low-Level Diagnostics
**Purpose**: Diagnose display configuration and hardware issues

**Tests**:
- SDL environment variables
- PyGame initialization
- DisplayManager creation
- PyGame surface verification
- Display zones configuration
- Image folder accessibility
- Detailed image loading with error reporting
- DisplayZoneDevice functionality

**Run**:
```bash
cd /home/nc4touch/NC4touch/scripts
python test_display_diagnostics.py
```

**Good for**: Troubleshooting configuration issues, SDL/Display driver problems


---

### 3. `test_prl_specific.py` - PRL Trainer Test
**Purpose**: Test PRL trainer's specific image display workflow

**Tests**:
- Display command sequences (load, show, clear)
- PRL load_images() and show_images() methods
- PRL image configuration (left='x', right='o')
- Chamber display device initialization
- Display operation timing
- Rapid display cycles (simulating real trials)
- PRL trainer state initialization

**Run**:
```bash
cd /home/nc4touch/NC4touch/scripts
python test_prl_specific.py
```

**Good for**: Verifying PRL-specific functionality and timing

---

## Quick Start - Run All Tests

To run all tests in sequence:

```bash
cd /home/nc4touch/NC4touch/scripts

echo "=== Test 1: Image Display Integration ==="
python test_image_display.py

echo ""
echo "=== Test 2: Display Diagnostics ==="
python test_display_diagnostics.py

echo ""
echo "=== Test 3: PRL Specific Test ==="
python test_prl_specific.py
```

---

## Interpreting Results

### All Tests Pass ✓
If all tests pass, the image display system is working correctly. If images still aren't showing during actual PRL training:

1. **Virtual Chamber GUI**: Make sure the virtual chamber window is open and visible
2. **Focus**: Ensure the GUI window has focus (click on it if needed)
3. **Trial Progress**: Verify that trials are advancing by checking console logs
4. **Reward System**: Check that beam break detection is working
5. **Display Duration**: Images may be clearing too quickly to see - check ITI and trial timing

### Some Tests Fail ✗

**If `test_image_display.py` fails**:
- Check image files exist: `ls -la /home/nc4touch/NC4touch/data/images/`
- Run `test_display_diagnostics.py` for more details

**If `test_display_diagnostics.py` fails**:
- If PyGame initialization fails: Check SDL/X11 environment
- If zones not configured: Check Chamber.py display configuration
- If images don't load: Verify file paths and permissions

**If `test_prl_specific.py` fails**:
- Check trainer config file exists: `~/trainer_PRL_config.yaml`
- Verify config file is valid YAML (run: `python -c "import yaml; yaml.safe_load(open(os.path.expanduser('~/trainer_PRL_config.yaml')))`)
- Check PRL trainer initialization in the logs

---

## Common Issues and Solutions

### Issue: "Image not found" error
**Cause**: Image files don't exist in `data/images/`
**Solution**:
1. Check files exist: `ls data/images/`
2. Expected files: `x.bmp`, `o.bmp`, `A01.bmp`, `B01.bmp`, `C01.bmp`
3. Create missing files if needed

### Issue: "Could not create display" error
**Cause**: Display device not available or resolution incorrect
**Solution**:
1. Check display is connected
2. Verify display resolution: `xrandr`
3. Adjust resolution in Chamber.py if needed

### Issue: Images load in test but not in PRL
**Cause**: Timing issue - images may clear before being seen
**Solution**:
1. Run `test_prl_specific.py` to check timing
2. Adjust trial timing in PRL config file
3. Check virtual chamber GUI has focus

### Issue: "YAML constructor" error
**Cause**: Config file has Python-specific tags
**Solution**:
1. Already fixed in `trainer_PRL_config.yaml`
2. If error persists, check no `!!python/tuple` tags in YAML files

---

## Expected Output

### Successful test run looks like:
```
╔════════════════════════════════════════════════════════════════════╗
║          IMAGE DISPLAY VERIFICATION TEST SUITE                    ║
╚════════════════════════════════════════════════════════════════════╝

======================================================================
TEST 1: Image Files Exist
======================================================================
...
✓ All expected image files exist!

✓ ALL TESTS PASSED!
```

### Failed test run looks like:
```
✗ SOME TESTS FAILED

Debug steps:
  1. Check the test output above for specific failures
  2. Verify image files exist in data/images/
  3. Check display configuration in Chamber.py
  4. Review error messages in logs
```

---

## Display System Architecture

For reference, here's how the display system works:

```
PRL Trainer
    │
    ├─ load_images() → chamber.display_command("IMG:imagename")
    │
    ├─ show_images() → chamber.display_command("SHOW")
    │
    └─ clear_images() → chamber.display_command("BLACK")
            │
            ▼
    Chamber.display_command()
            │
            ├─ Looks up display_device for zone (left/middle/right)
            │
            └─ device.send_command()
                    │
                    ├─ IMG: command → DisplayZoneDevice._loaded_image = name
                    ├─ SHOW command → DisplayZoneDevice calls display.show_image()
                    └─ BLACK command → DisplayZoneDevice calls display.clear()
                            │
                            ├─ display.show_image() → pygame.blit() image to screen
                            └─ display.clear() → pygame.fill() with black
                                    │
                                    ▼
                        pygame.display.update() (refresh screen)
```

---

## Virtual Chamber GUI Notes

When running tests with the virtual chamber:

1. **Window appears**: A PyGame window will open showing the display
2. **Display zones**: Three zones (left, middle, right) will be visible
3. **Interactive**: You can interact with the display by clicking on zones
4. **Image updates**: You'll see images load and clear in real-time
5. **Close cleanly**: Close the window with the X button, don't force-quit

---

## For Debugging Long Sessions

If you want to run a longer test to see multiple image cycles:

```bash
# Run multiple PRL image display cycles
python test_prl_specific.py 2>&1 | tee prl_test_$(date +%Y%m%d_%H%M%S).log

# View logs
tail -f prl_test_*.log
```

---

## Contact & Support

If tests fail and you can't resolve the issue:

1. Collect all test outputs
2. Check Chamber.py and Display.py for configuration
3. Review Virtual/VirtualChamberGUI.py for rendering code
4. Run with debug logging: `python test_* -v` (if available)

---

**Last Updated**: 2026-03-20
**Test Coverage**: Images, Zones, Display Devices, PRL Integration, Timing, Caching
