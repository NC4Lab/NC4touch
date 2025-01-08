#!/bin/bash

LOG_DIR="/home/nc4/TouchscreenApparatus/src/drivers/nc4_ili9488/logs"
LOG_FILE="$LOG_DIR/diagnostic_nc4.log"

echo "==== Diagnostic Information for nc4 DRM Setup ====" | tee "$LOG_FILE"

# Section 1: DRM Resource Details
echo -e "\n==== DRM Resource Details ====" | tee -a "$LOG_FILE"

# List DRM devices
echo "Listing /dev/dri devices:" | tee -a "$LOG_FILE"
ls -l /dev/dri | tee -a "$LOG_FILE"

# Use drm_info if available
if command -v drm_info > /dev/null; then
    echo -e "\nDetailed DRM Information (via drm_info):" | tee -a "$LOG_FILE"
    drm_info | tee -a "$LOG_FILE"
else
    echo "drm_info not available. Skipping detailed DRM info." | tee -a "$LOG_FILE"
fi

# Use modetest if available
if command -v modetest > /dev/null; then
    echo -e "\nDetailed DRM Information (via modetest):" | tee -a "$LOG_FILE"
    modetest | tee -a "$LOG_FILE"
else
    echo "modetest not available. Skipping detailed DRM info." | tee -a "$LOG_FILE"
fi

# Section 2: Framebuffer Mapping
echo -e "\n==== Framebuffer to DRM Device Mapping ====" | tee -a "$LOG_FILE"

for FB in /sys/class/graphics/fb*; do
    echo "Inspecting $(basename $FB):" | tee -a "$LOG_FILE"
    if [ -L "$FB/device" ]; then
        REAL_PATH=$(readlink -f "$FB/device")
        echo "Linked to DRM device: $REAL_PATH" | tee -a "$LOG_FILE"
    else
        echo "No DRM device linked to $(basename $FB)" | tee -a "$LOG_FILE"
    fi
done

# Section 3: SPI Details
echo -e "\n==== SPI Device and Driver Details ====" | tee -a "$LOG_FILE"

for SPI in /sys/bus/spi/devices/spi1.*; do
    if [ -d "$SPI" ]; then
        echo "Inspecting $SPI:" | tee -a "$LOG_FILE"
        DRIVER_PATH="$SPI/driver"
        if [ -L "$DRIVER_PATH" ]; then
            DRIVER=$(readlink -f "$DRIVER_PATH")
            echo "Driver bound: $DRIVER" | tee -a "$LOG_FILE"
        else
            echo "No driver bound to $SPI" | tee -a "$LOG_FILE"
        fi
    else
        echo "$SPI not found or inaccessible" | tee -a "$LOG_FILE"
    fi
done

# Verify GPIO states for CS, DC, RES
echo -e "\n==== GPIO States for SPI Devices ====" | tee -a "$LOG_FILE"
GPIO_PINS=(18 17 16 12 13 22 23 24 25 27)
for PIN in "${GPIO_PINS[@]}"; do
    echo "Checking GPIO $PIN:" | tee -a "$LOG_FILE"
    raspi-gpio get $PIN | tee -a "$LOG_FILE"
done

# Completion
echo -e "\n==== Diagnostic Complete ====" | tee -a "$LOG_FILE"
echo "Logs saved to $LOG_FILE"
