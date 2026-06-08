#!/usr/bin/env python3
# dump_touchscreen_config.py
import argparse
from pathlib import Path
import time

import smbus2

ADDR = 0x5D
DEFAULT_OUTPUT = "gt9271_config_backup.bin"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Dump GT9271/Goodix touchscreen config over I2C."
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
    parser.add_argument(
        "--output",
        default=DEFAULT_OUTPUT,
        help=f"Output file path (default: {DEFAULT_OUTPUT})",
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

    driver = find_bound_driver(device_id)
    if driver is not None:
        print(f"Unbinding from driver: {driver.name}")
        with (driver / "unbind").open("w") as f:
            f.write(device_id)
        time.sleep(0.5)
    else:
        print("No bound kernel driver found; continuing with direct I2C access.")

    try:
        with smbus2.SMBus(bus_num) as bus:
            config = read_regs(bus, args.addr, 0x8047, 0xBA)
    finally:
        if driver is not None:
            with (driver / "bind").open("w") as f:
                f.write(device_id)
            print(f"Driver rebound: {driver.name}")

    with open(args.output, "wb") as f:
        f.write(bytes(config))

    threshold = config[0x8053 - 0x8047]
    print(f"Backup saved to {args.output}")
    print(f"Touch threshold (0x8053): {threshold}")


if __name__ == "__main__":
    main()