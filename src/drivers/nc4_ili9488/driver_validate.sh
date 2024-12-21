#!/bin/bash

OVERLAY_NAME="nc4_ili9488"
OVERLAY_DTBO="/boot/firmware/overlays/${OVERLAY_NAME}.dtbo"
DRIVER_NAME="nc4_ili9488"
DRIVER_PATH="/lib/modules/$(uname -r)/extra/${DRIVER_NAME}.ko"

echo "=== Starting Overlay and Driver Validation ==="

## Validate Overlay
echo "==== Validating Overlay ===="

# Check if overlay .dtbo exists
if [ -f "$OVERLAY_DTBO" ]; then
    echo "Overlay file found: $OVERLAY_DTBO"
else
    echo "Error: Overlay file not found: $OVERLAY_DTBO" >&2
    exit 1
fi

# Check if overlay nodes exist in the device tree
echo "Checking overlay nodes in the device tree..."

# Specify expected node names or identifiers from the overlay
EXPECTED_NODES=("pitft0" "pitft1" "pitft0@0" "pitft1@1")

# Search for each node in the flattened device tree
for NODE in "${EXPECTED_NODES[@]}"; do
    if grep -q "$NODE" <(dtc -I fs /proc/device-tree 2>/dev/null); then
        echo "Node '$NODE' found in the flattened device tree."
    else
        echo "Node '$NODE' not found. Check overlay or binding for issues."
    fi
done

# List all nodes in the relevant SPI path for additional validation
SPI_PATH="/proc/device-tree/soc/spi@7e204000"
echo "Listing all nodes under $SPI_PATH for verification:"
if [ -d "$SPI_PATH" ]; then
    ls "$SPI_PATH" || echo "No nodes found under $SPI_PATH."
else
    echo "SPI path $SPI_PATH does not exist."
fi

# Check kernel logs for overlay application
echo "Checking kernel logs for overlay application..."
if dmesg | grep -qi "$OVERLAY_NAME"; then
    echo "Overlay is logged in kernel messages."
else
    echo "Overlay not found in kernel messages. Check the logs for issues."
fi

# Verify overlay entries in config.txt
echo "Verifying overlay references in config.txt..."
if grep -q "dtoverlay=$OVERLAY_NAME" /boot/firmware/config.txt; then
    echo "Overlay is referenced in config.txt."
else
    echo "Overlay not found in config.txt. Ensure it is added correctly."
fi

# Debugging overlay issues
echo "Debugging overlay loading (if issues persist)..."
dmesg | grep -Ei 'overlay|dtoverlay|firmware|dt'

# Check frame buffer devices
echo "Checking active frame buffer devices..."
if ls /dev/fb* 1>/dev/null 2>&1; then
    echo "Frame buffer devices found: $(ls /dev/fb*)"
else
    echo "No frame buffer devices found. Overlay may not be fully functional."
fi

# Validate the .dtbo file
echo "Validating the .dtbo file syntax..."
if sudo dtc -I dtb -O dts -o /dev/null "$OVERLAY_DTBO" 2>/dev/null; then
    echo ".dtbo file is valid."
else
    echo "Error: .dtbo file contains syntax issues." >&2
    exit 1
fi

## Validate Driver
echo "==== Validating Driver ===="

# Check if the driver module exists
if [ -f "$DRIVER_PATH" ]; then
    echo "Driver file found: $DRIVER_PATH"
else
    echo "Error: Driver file not found: $DRIVER_PATH" >&2
    exit 1
fi

# Check if the module is loaded
echo "Checking if the driver module is loaded..."
if lsmod | grep -q "$DRIVER_NAME"; then
    echo "Driver module is loaded."
else
    echo "Driver module is not loaded. Attempting to load it..."
    sudo insmod "$DRIVER_PATH"
    if lsmod | grep -q "$DRIVER_NAME"; then
        echo "Driver module loaded successfully."
    else
        echo "Error: Failed to load the driver module." >&2
        exit 1
    fi
fi

# Check kernel logs for driver messages
echo "Checking kernel logs for driver messages..."
if dmesg | grep -qi "$DRIVER_NAME"; then
    echo "Driver messages found in kernel logs:"
    dmesg | grep -i "$DRIVER_NAME"
else
    echo "No driver messages found in kernel logs."
fi

# Check if the module is still available
echo "Checking if the module is still available..."
modinfo "$DRIVER_NAME" || echo "Module $DRIVER_NAME not found (expected if removed)."

# Check for residual device tree entries
echo "Checking for residual entries in /proc/device-tree..."
if grep -ril "$DRIVER_NAME" /proc/device-tree/; then
    echo "Residual device-tree entries found for $DRIVER_NAME."
else
    echo "No residual device-tree entries for $DRIVER_NAME."
fi

# Attempt to reload the module if issues persist
echo "Attempting to reload the driver module..."
sudo rmmod "$DRIVER_NAME" 2>/dev/null || echo "Module not currently loaded."
sudo insmod "$DRIVER_PATH"
if lsmod | grep -q "$DRIVER_NAME"; then
    echo "Driver module reloaded successfully."
else
    echo "Error: Failed to reload the driver module." >&2
    exit 1
fi

# Final kernel log check
echo "Final kernel logs:"
dmesg | grep -i "$DRIVER_NAME"

echo "=== Validation Complete ==="
