#!/bin/bash

# Define the output directory and file
OUTPUT_DIR="/home/nc4/TouchscreenApparatus/src/drivers/debug/SPI1_debug"
OUTPUT_FILE="$OUTPUT_DIR/spi1-3cs_debug_1.log"

# Ensure the output directory exists
if [ ! -d "$OUTPUT_DIR" ]; then
  echo "Output directory does not exist. Creating: $OUTPUT_DIR"
  mkdir -p "$OUTPUT_DIR"
fi

# Start writing to the log file
echo "=== SPI1 Debugging Logs ===" > "$OUTPUT_FILE"
echo "Timestamp: $(date)" >> "$OUTPUT_FILE"
echo >> "$OUTPUT_FILE"

# Check kernel logs for overlay application errors
echo "=== Kernel Logs: Overlay Loading Errors ===" >> "$OUTPUT_FILE"
dmesg | grep -i "overlay\|dtdebug\|spi\|ili9488" >> "$OUTPUT_FILE" 2>&1
echo >> "$OUTPUT_FILE"

# Decompile live Device Tree
echo "=== Decompiled Device Tree ===" >> "$OUTPUT_FILE"
sudo dtc -I fs -O dts -o "$OUTPUT_DIR/live_device_tree.dts" /proc/device-tree
if [ -f "$OUTPUT_DIR/live_device_tree.dts" ]; then
  echo "Decompiled device tree saved to: $OUTPUT_DIR/live_device_tree.dts" >> "$OUTPUT_FILE"
else
  echo "Failed to decompile live device tree." >> "$OUTPUT_FILE"
fi
echo >> "$OUTPUT_FILE"

# Check for SPI nodes in the live Device Tree
echo "=== SPI Nodes in Live Device Tree ===" >> "$OUTPUT_FILE"
grep -E "spidev|spi" "$OUTPUT_DIR/live_device_tree.dts" >> "$OUTPUT_FILE" 2>&1
echo >> "$OUTPUT_FILE"

# Check GPIO configurations
echo "=== GPIO States ===" >> "$OUTPUT_FILE"
if command -v raspi-gpio &> /dev/null; then
  raspi-gpio get >> "$OUTPUT_FILE" 2>&1
else
  echo "raspi-gpio command not found. Skipping GPIO state verification." >> "$OUTPUT_FILE"
fi
echo >> "$OUTPUT_FILE"

# Check loaded overlays using vcdbg
echo "=== vcdbg Logs for Overlays ===" >> "$OUTPUT_FILE"
if command -v vcdbg &> /dev/null; then
  vcdbg log msg |& grep -i "overlay" >> "$OUTPUT_FILE" 2>&1
else
  echo "vcdbg command not found. Skipping overlay verification with vcdbg." >> "$OUTPUT_FILE"
fi
echo >> "$OUTPUT_FILE"

# Summary of results
echo "Debug information saved to: $OUTPUT_FILE"
