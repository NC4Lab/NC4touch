# Virtual Chamber Image Setup Guide

## Quick Setup

Your virtual chamber needs BMP image files to display stimuli on virtual touchscreens, just like the physical touchscreen controllers have images stored locally.

### 1. Put Your BMP Files Here

**Default location**: `NC4touch/data/images/`

```
NC4touch/
  data/
    images/
      A01.bmp    ← Your stimulus images
      B01.bmp
      C01.bmp
      ...
```

### 2. That's It!

Your trainer code will work automatically:

```python
# This works exactly like physical chamber
chamber.display_command("left", "IMG:A01")   # Loads A01.bmp
chamber.display_command("left", "SHOW")       # Displays it
```

## Custom Image Directory

If your images are elsewhere:

```python
from Virtual.VirtualChamber import VirtualChamber

chamber = VirtualChamber(chamber_config={
    "image_dir": "/your/custom/path/to/images"
})
```

Or in `chamber_config.yaml`:
```yaml
image_dir: /absolute/path/to/your/images
```

## Testing With Template Script

In `scripts/test_trainer_template.py`:

```python
# Configure image directory at top of main()
chamber_config = {
    "image_dir": "/path/to/your/bmp/files",  # Optional
}

# Pass it to your test
test_trainer_with_gui(YourTrainer, 
    trainer_config={...},
    chamber_config=chamber_config  # ← Here
)
```

## Supported Commands

The virtual display-zone devices understand the same commands as physical touchscreen controllers:

- `IMG:filename` - Load image (automatically adds `.bmp` extension)
- `SHOW` - Display the loaded image
- `BLACK` - Clear screen to black
- `CLEAR` - Alternative to BLACK
- `DISPLAY:path` - Legacy command (still works)

## Troubleshooting

**"Image file not found" warnings?**

Check:
1. File is actually `.bmp` format
2. File is in the image directory
3. Filename matches (case-sensitive)
4. Use image name without `.bmp` extension in command

Example:
```python
# ✓ Correct
chamber.display_command("left", "IMG:A01")   # Looks for A01.bmp

# ✗ Wrong
chamber.display_command("left", "IMG:A01.bmp")  # Looks for A01.bmp.bmp
```

**Can't find images in logs?**

Enable debug logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

The virtual display device will log:
- When images are loaded
- When images are displayed
- If image files aren't found (with full path tried)

## Where to Get Sample Images

Your existing BMP files from the physical chamber work perfectly! Just copy them:

```bash
# From your touchscreen controller storage (or any source folder)
cp /path/to/images/*.bmp ~/NC4touch/data/images/
```

Or create new ones (320x480 pixels, 24-bit BMP format recommended).
