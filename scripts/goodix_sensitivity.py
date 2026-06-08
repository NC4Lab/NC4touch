#!/usr/bin/env python3
# goodix_sensitivity.py
# Aggressive tuning for small animal paw/nose detection on GT9271.
import smbus2
import time

bus = smbus2.SMBus(11)
addr = 0x5d

# --- Aggressive Sensitivity Tuning ---
NEW_TOUCH_THRESHOLD = 10    # 0x8053 (User requested)
NEW_LEAVE_THRESHOLD = 6    # 0x8054 (User requested)
NEW_NOISE_REDUCTION = 3    # 0x8052 (User requested)
NEW_LARGE_TOUCH     = 5    # 0x8051 (User requested)

# --- Hardware Gain & Integration Time ---
NEW_REFRESH_RATE    = 10   # 0x8056 (10ms; allows more integration time for weak signals)
NEW_DAC_GAIN        = 0x00 # 0x806A (Set to 0 for maximum DAC range)
NEW_PGA_GAIN        = 0x05 # 0x806C (Bits 0-2: Set PGA to max gear)
NEW_DUMP_SHIFT      = 0x01 # 0x806D (Digital multiplier: 0x02 = 4x signal boost)

def write_regs(start, data):
    """Write in 31-byte chunks to respect SMBus 32-byte limit."""
    data = list(data)
    offset = 0
    while offset < len(data):
        chunk = data[offset:offset + 31]
        reg = start + offset
        # Payload for 16-bit address: [LowByte, Data0, Data1, ...]
        payload = [reg & 0xFF] + chunk
        bus.write_i2c_block_data(addr, (reg >> 8) & 0xFF, payload)
        time.sleep(0.01)
        offset += 31

def read_regs(start, count):
    bus.write_i2c_block_data(addr, (start >> 8) & 0xFF, [start & 0xFF])
    time.sleep(0.01)
    return [bus.read_byte(addr) for _ in range(count)]

print("Step 1: Unbinding Goodix driver...")
try:
    with open('/sys/bus/i2c/drivers/Goodix-TS/unbind', 'w') as f:
        f.write('11-005d')
except OSError:
    print("  Driver already unbound or not found.")
time.sleep(0.5)

print("Step 2: Reading current config (Registers 0x8047 to 0x80FE)...")
# Reading 184 bytes (0x8047 to 0x80FE)
config = read_regs(0x8047, 0xB8) 

print("Step 3: Applying aggressive gain and threshold values...")
# User Thresholds
config[0x8051 - 0x8047] = NEW_LARGE_TOUCH
config[0x8052 - 0x8047] = NEW_NOISE_REDUCTION
config[0x8053 - 0x8047] = NEW_TOUCH_THRESHOLD
config[0x8054 - 0x8047] = NEW_LEAVE_THRESHOLD

# Integration & Filtering
config[0x804D - 0x8047] &= ~(1 << 3) # Disable Large Object Rejection Bit
config[0x8056 - 0x8047] = NEW_REFRESH_RATE

# Analog/Digital Gain Stages
config[0x806A - 0x8047] = NEW_DAC_GAIN
config[0x806C - 0x8047] = (config[0x806C - 0x8047] & 0xF8) | NEW_PGA_GAIN
config[0x806D - 0x8047] = NEW_DUMP_SHIFT

# Recalculate Checksum (2's complement of sum of 0x8047 to 0x80FE)
checksum = (~sum(config) + 1) & 0xFF
print(f"  New calculated checksum: 0x{checksum:02X}")

# Write Config
write_regs(0x8047, config)
# Write Checksum to 0x80FF
write_regs(0x80FF, [checksum])
# Trigger Refresh (Write 1 to 0x8100)
write_regs(0x8100, [0x01])
time.sleep(0.2)

print("Step 4: Verifying Hardware Gains...")
verify = read_regs(0x806A, 4) # Read 806A, 806B, 806C, 806D
print(f"  0x806A DAC Gain     : {verify[0]} (expected {NEW_DAC_GAIN})")
print(f"  0x806C PGA Gain     : {verify[2] & 0x07} (expected {NEW_PGA_GAIN})")
print(f"  0x806D Dump Shift   : {verify[3]} (expected {NEW_DUMP_SHIFT})")

print("Step 5: Rebinding Goodix driver...")
with open('/sys/bus/i2c/drivers/Goodix-TS/bind', 'w') as f:
    f.write('11-005d')
time.sleep(1)

print("\nDone! Please ensure the screen surface is clear for the initial baseline calibration.")