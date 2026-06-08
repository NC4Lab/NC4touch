#!/usr/bin/env python3
# goodix_sensitivity.py
# Aggressive tuning for small animal paw/nose detection on GT9271.
import argparse
from pathlib import Path
import smbus2
import time

ADDR = 0x5D

# --- Aggressive Sensitivity Tuning ---
NEW_TOUCH_THRESHOLD = 14    # 0x8053 (User requested)
NEW_LEAVE_THRESHOLD = 8    # 0x8054 (User requested)
NEW_NOISE_REDUCTION = 4    # 0x8052 (User requested)
NEW_LARGE_TOUCH     = 5    # 0x8051 (User requested)
NEW_NORMAL_FILTER   = 5    # 0x8050

# --- Hardware Gain & Integration Time ---
NEW_REFRESH_RATE    = 10   # 0x8056 (10ms; allows more integration time for weak signals)
NEW_DAC_GAIN        = 0x00 # 0x806A (Set to 0 for maximum DAC range)
NEW_PGA_GAIN        = 0x05 # 0x806C (Bits 0-2: Set PGA to max gear)
NEW_DUMP_SHIFT      = 0x01 # 0x806D (Digital multiplier: 0x02 = 4x signal boost)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Aggressively tune Goodix GT9271 touchscreen sensitivity."
    )
    parser.add_argument(
        "--bus",
        type=int,
        help="I2C bus number (auto-detected if omitted)",
    )
    parser.add_argument(
        "--addr",
        type=lambda x: int(x, 0),
        default=ADDR,
        help="Touch controller I2C address (default: 0x5D)",
    )
    return parser.parse_args()


def find_device_ids(address):
    suffix = f"-{address:04x}"
    ids = []
    for path in Path("/sys/bus/i2c/devices").glob(f"*{suffix}"):
        name = path.name
        if "-" not in name:
            continue
        bus_str, _ = name.split("-", 1)
        if bus_str.isdigit():
            ids.append((int(bus_str), name))
    ids.sort(key=lambda x: x[0])
    return ids


def find_bound_driver(device_id):
    drivers_dir = Path("/sys/bus/i2c/drivers")
    for driver in drivers_dir.iterdir():
        if (driver / device_id).exists():
            return driver
    return None


def resolve_bus_and_id(args):
    if args.bus is not None:
        return args.bus, f"{args.bus}-{args.addr:04x}"

    ids = find_device_ids(args.addr)
    if not ids:
        raise RuntimeError(
            f"No I2C device found for address 0x{args.addr:02X} under /sys/bus/i2c/devices."
        )
    return ids[0]


def write_regs(bus, addr, start, data):
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


def read_regs(bus, addr, start, count):
    bus.write_i2c_block_data(addr, (start >> 8) & 0xFF, [start & 0xFF])
    time.sleep(0.01)
    return [bus.read_byte(addr) for _ in range(count)]


def main():
    args = parse_args()
    bus_num, device_id = resolve_bus_and_id(args)
    dev_path = Path(f"/dev/i2c-{bus_num}")
    if not dev_path.exists():
        raise FileNotFoundError(f"{dev_path} was not found on this host")

    print(f"Using I2C bus {bus_num}, address 0x{args.addr:02X} ({device_id})")

    print("Step 1: Unbinding touchscreen driver...")
    driver = find_bound_driver(device_id)
    if driver is not None:
        with (driver / "unbind").open("w") as f:
            f.write(device_id)
    else:
        print("  Driver already unbound or not found.")
    time.sleep(0.5)

    try:
        with smbus2.SMBus(bus_num) as bus:
            print("Step 2: Reading current config (Registers 0x8047 to 0x80FE)...")
            # Reading 184 bytes (0x8047 to 0x80FE)
            config = read_regs(bus, args.addr, 0x8047, 0xB8)

            print("Step 3: Applying aggressive gain and threshold values...")
            # User Thresholds
            config[0x8051 - 0x8047] = NEW_LARGE_TOUCH
            config[0x8052 - 0x8047] = NEW_NOISE_REDUCTION
            config[0x8053 - 0x8047] = NEW_TOUCH_THRESHOLD
            config[0x8054 - 0x8047] = NEW_LEAVE_THRESHOLD
            config[0x8050 - 0x8047] = NEW_NORMAL_FILTER

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
            write_regs(bus, args.addr, 0x8047, config)
            # Write Checksum to 0x80FF
            write_regs(bus, args.addr, 0x80FF, [checksum])
            # Trigger Refresh (Write 1 to 0x8100)
            write_regs(bus, args.addr, 0x8100, [0x01])
            time.sleep(0.2)

            print("Step 4: Verifying Hardware Gains...")
            verify = read_regs(bus, args.addr, 0x806A, 4) # Read 806A, 806B, 806C, 806D
            print(f"  0x806A DAC Gain     : {verify[0]} (expected {NEW_DAC_GAIN})")
            print(f"  0x806C PGA Gain     : {verify[2] & 0x07} (expected {NEW_PGA_GAIN})")
            print(f"  0x806D Dump Shift   : {verify[3]} (expected {NEW_DUMP_SHIFT})")
    finally:
        print("Step 5: Rebinding touchscreen driver...")
        if driver is not None:
            with (driver / "bind").open("w") as f:
                f.write(device_id)
            print(f"  Driver rebound: {driver.name}")
        else:
            print("  No driver to rebind.")
        time.sleep(1)

    print("\nDone! Please ensure the screen surface is clear for the initial baseline calibration.")


if __name__ == "__main__":
    main()