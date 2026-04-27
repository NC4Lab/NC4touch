# Goodix GT9271 Touch Sensitivity Tuning
## Waveshare 8.8-DSI-TOUCH-A on Raspberry Pi 5

Tuning guide for increasing touchscreen sensitivity for small contact areas (e.g. mouse paws in behavioural chambers).

---

## Hardware & Software Context

| Item | Detail |
|---|---|
| Display | Waveshare 8.8-DSI-TOUCH-A (480×1920, DSI) |
| Touch controller | Goodix GT9271 (10-point capacitive) |
| Host | Raspberry Pi 5 |
| OS | Raspberry Pi OS Bookworm |
| I2C bus | Bus 11 (RP1 PCIe I2C) |
| I2C address | 0x5d |
| Kernel driver | `Goodix-TS` |
| Input device | `/dev/input/event5` |

> **Note:** The I2C bus and input event number may differ on your system. Verify with:
> ```bash
> dmesg | grep -i goodix
> ```
> Look for a line like: `input: Goodix Capacitive TouchScreen as /devices/.../11-005d/input/input5`

---

## How It Works

The GT9271 has a configurable **touch detection threshold** register (`0x8053`). The default value (80) is tuned for adult human fingertips. Mouse paws produce a weaker capacitive signal and a smaller contact area, so they fall below this threshold and are not registered.

By lowering the threshold and related registers via I2C, we allow the controller to register lighter/smaller contacts.

### Key Registers

| Register | Name | Default | Tuned Value |
|---|---|---|---|
| `0x8051` | Large touch filter | 25 | 10 |
| `0x8052` | Noise reduction | 5 | 3 |
| `0x8053` | **Screen touch level (sensitivity)** | 80 | 20 |
| `0x8054` | Leave touch level (hysteresis) | 50 | 10 |
| `0x80FF` | Config checksum | 0xD1 | recalculated |
| `0x8100` | Config fresh flag | 0 | 1 (trigger apply) |

> **Important:** Any change to registers `0x8047–0x80FE` requires recalculating the checksum at `0x80FF` and writing `0x01` to `0x8100` to apply the changes.

---

## Prerequisites

```bash
sudo apt install python3 i2c-tools evtest
pip install smbus2 --break-system-packages
```

---

## Step 1: Dump Current Config (optional but recommended)

Run this before making changes to save a backup of the factory config:

```python
#!/usr/bin/env python3
# dump_gt9271.py
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
```

```bash
sudo python3 dump_gt9271.py
```

---

## Step 2: Apply Sensitivity Settings

Save this as `/usr/local/bin/goodix-sensitivity.py`:

```python
#!/usr/bin/env python3
# goodix-sensitivity.py
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
```

```bash
sudo cp goodix-sensitivity.py /usr/local/bin/goodix-sensitivity.py
sudo python3 /usr/local/bin/goodix-sensitivity.py
```


---

## Step 3: Make It Permanent (systemd service)

The GT9271 config is volatile — it resets on power loss. A systemd service reapplies the settings at every boot.

Create `/etc/systemd/system/goodix-sensitivity.service`:

```ini
[Unit]
Description=Set Goodix GT9271 touch sensitivity for mouse chamber
After=systemd-udev-settle.service
Wants=systemd-udev-settle.service

[Service]
Type=oneshot
ExecStart=/usr/bin/python3 /usr/local/bin/goodix-sensitivity.py
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
```

Enable it:

```bash
sudo systemctl daemon-reload
sudo systemctl enable goodix-sensitivity.service
sudo systemctl start goodix-sensitivity.service
```

Verify it ran correctly:

```bash
sudo systemctl status goodix-sensitivity.service
```

---

## Testing

```bash
# Install evtest if not already present
sudo apt install evtest

# Watch raw touch events
sudo evtest /dev/input/event3 #check sudo evtest for the correct event number
```

Touch the screen with a mouse paw. You should see `EV_ABS` events including `ABS_MT_POSITION_X` and `ABS_MT_POSITION_Y`. If nothing appears, the threshold may need to go lower.

---

## Restoring Factory Settings

```bash
sudo python3 - << 'EOF'
import smbus2, time

bus = smbus2.SMBus(11)
addr = 0x5d

def write_regs(start, data):
    data = list(data)
    offset = 0
    while offset < len(data):
        chunk = data[offset:offset + 31]
        reg = start + offset
        bus.write_i2c_block_data(addr, (reg >> 8) & 0xFF, [reg & 0xFF] + chunk)
        time.sleep(0.01)
        offset += 31

def read_regs(start, count):
    bus.write_i2c_block_data(addr, (start >> 8) & 0xFF, [start & 0xFF])
    time.sleep(0.01)
    return [bus.read_byte(addr) for _ in range(count)]

with open('/sys/bus/i2c/drivers/Goodix-TS/unbind', 'w') as f:
    f.write('11-005d')
time.sleep(0.5)

config = read_regs(0x8047, 0xB9)
config[0x8051 - 0x8047] = 25
config[0x8052 - 0x8047] = 5
config[0x8053 - 0x8047] = 80
config[0x8054 - 0x8047] = 50
checksum = (~sum(config) + 1) & 0xFF
write_regs(0x8047, config)
write_regs(0x80FF, [checksum])
write_regs(0x8100, [0x01])
time.sleep(0.1)

with open('/sys/bus/i2c/drivers/Goodix-TS/bind', 'w') as f:
    f.write('11-005d')
print('Restored to factory values.')
EOF
```

---

## Troubleshooting

**`OSError: [Errno 19] No such device` on unbind**
The driver name may differ. Check with:
```bash
ls /sys/bus/i2c/drivers/ | grep -i goodix
```
Update the unbind/bind path in the script to match exactly.

**`ValueError: Data length cannot exceed 32 bytes`**
SMBus limits writes to 32 bytes. Ensure the `write_regs` function uses 31-byte chunking as shown above (1 byte is used for the low byte of the register address).

**Ghost touches / cursor moving on its own**
The threshold is too low. Increase `NEW_TOUCH_THRESHOLD` in steps of 10 until ghost touches stop.

**Still no touch events after lowering threshold**
- Confirm the driver rebound: `dmesg | grep -i goodix`
- Confirm the device is on the expected event node: `sudo evtest`
- Try lowering threshold further (minimum ~10 before noise becomes a problem)

**Settings lost after reboot**
Confirm the systemd service is enabled:
```bash
sudo systemctl is-enabled goodix-sensitivity.service
sudo systemctl status goodix-sensitivity.service
```

---

## Notes

- The GT9271 config is stored in volatile RAM on the chip — it does not persist through power cycles without the systemd service.
- The mainline Linux `goodix.c` driver on Pi 5 / Bookworm does not support loading config from `/lib/firmware/`, so the systemd approach is required.
- The `UU` entries in `i2cdetect` are expected — they indicate the kernel driver owns the bus. Always unbind before direct I2C access and rebind immediately after.
- Changes take effect immediately after `Config_Fresh` (`0x8100`) is set to `0x01` — no reboot required for testing.
