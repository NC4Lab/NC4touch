#!/usr/bin/env python3
# dump_touchscreen_config.py
import smbus2, time

bus = smbus2.SMBus(11)
addr = 0x5d

def read_regs(start, count):
    bus.write_i2c_block_data(addr, (start >> 8) & 0xFF, [start & 0xFF])
    time.sleep(0.01)
    return [bus.read_byte(addr) for _ in range(count)]

# Unbind driver to allow direct I2C access
with open('/sys/bus/i2c/drivers/Goodix-TS/unbind', 'w') as f:
    f.write('11-005d')
time.sleep(0.5)

config = read_regs(0x8047, 0xBA)

with open('gt9271_config_backup.bin', 'wb') as f:
    f.write(bytes(config))
print("Backup saved to gt9271_config_backup.bin")
print(f"Touch threshold (0x8053): {config[0x8053 - 0x8047]}")

# Rebind driver
with open('/sys/bus/i2c/drivers/Goodix-TS/bind', 'w') as f:
    f.write('11-005d')
print("Driver rebound.")