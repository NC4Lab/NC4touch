#!/bin/bash
cd /home/nc4/TouchscreenApparatus/src/drivers/z_obs_arc/ili9488/rpi-overlays

# Configuration
DTS_FILE="ili9488.dts"
DTBO_FILE="/boot/firmware/overlays/ili9488.dtbo"
OVERLAY_NAME="ili9488"

# Function to display warnings from device tree
function show_warnings() {
    echo "=== Extracting Warnings from Live Device Tree ==="
    dtc -I fs /proc/device-tree 2>&1 | grep -i "warning" || echo "No warnings found."
}

# Function to apply and validate the overlay
function apply_overlay() {
    echo "=== Compiling and Applying Overlay ==="
    sudo dtc -@ -I dts -O dtb -o "$DTBO_FILE" "$DTS_FILE" || { echo "Error: Compilation failed."; exit 1; }
    sudo dtoverlay -v "$OVERLAY_NAME" || { echo "Error: Failed to apply overlay."; exit 1; }
}

# Compile, apply, and check warnings
echo "=== Starting Iterative Test ==="
apply_overlay
show_warnings

# Check kernel logs for related errors
echo "=== Kernel Logs ==="
dmesg | tail -50 | grep -Ei "overlay|warning|error" || echo "No relevant kernel log messages."

echo "=== Iterative Test Complete ==="
