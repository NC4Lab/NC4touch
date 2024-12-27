#!/bin/bash

# Step 1: Clean up existing overlays
echo "Cleaning up existing overlays..."
sudo rmdir /sys/kernel/config/device-tree/overlays/* 2>/dev/null || echo "No overlays to remove."

# Step 2: Check GPIO and SPI status before applying overlay
echo "Current GPIO state:"
sudo raspi-gpio get

echo "Current SPI devices:"
ls /dev/spi* || echo "No SPI devices found."

# Step 3: Compile the overlay
echo "Compiling the overlay..."
dtc -@ -I dts -O dtb -o minimal-overlay.dtbo minimal-overlay.dts
if [ $? -ne 0 ]; then
    echo "Error: Overlay compilation failed."
    exit 1
fi

# Step 4: Copy the compiled overlay to the firmware directory
echo "Copying the overlay to /boot/firmware/overlays/..."
sudo cp minimal-overlay.dtbo /boot/firmware/overlays/

# Step 5: Apply the overlay
echo "Applying the overlay..."
sudo dtoverlay -v minimal-overlay
if [ $? -ne 0 ]; then
    echo "Error: Overlay application failed."
else
    echo "Overlay applied successfully."
fi

# Step 6: Capture kernel logs after applying overlay
echo "Kernel logs after applying overlay:"
dmesg | tail -50

# Step 7: Check GPIO and SPI status after applying overlay
echo "GPIO state after applying overlay:"
sudo raspi-gpio get

echo "SPI devices after applying overlay:"
ls /dev/spi* || echo "No SPI devices found."

# Step 8: Confirm loaded overlays
echo "Currently loaded overlays:"
ls /sys/kernel/config/device-tree/overlays/
