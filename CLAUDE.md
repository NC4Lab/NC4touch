# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

NC4Touch is a Python-controlled rodent touchscreen behavioral experiment system built by NC4Lab at UBC. It runs on Raspberry Pi 5 hardware connected to DFRobot M0 microcontrollers (SAMD21-based) that drive ILI9488 touchscreens with GT911 capacitive touch. The system manages training sessions through a state machine architecture, controlling peripherals (reward pump, LEDs, buzzer, beam break sensor) via pigpio, and M0 touchscreens via serial (USB-ACM).

## Running the System

```bash
# On the Raspberry Pi (production):
scripts/start_webUI.sh
# Which does: sudo pigpiod && uv run Controller/WebUI.py

# Virtual chamber testing (no hardware needed, works on any platform):
python scripts/demo_virtual_chamber.py
python scripts/test_virtual_chamber.py
```

The WebUI runs on NiceGUI (port 8081) and derives the chamber name from the Pi's IP address last octet (e.g., IP ending .11 = Chamber1).

## Architecture

### Two-tier control flow

**Session** (`Controller/Session.py`) is the top-level orchestrator. It owns a **Chamber** and a **Trainer**. The Session runs a repeating `threading.Timer` that calls `trainer.run_training()` at a configurable interval (default 0.1s). Trainers are loaded dynamically via `importlib.import_module(f"trainers.{trainer_name}")`.

**Chamber** (`Controller/Chamber.py`) owns all hardware: 3 M0Devices (left/middle/right), reward pump, reward LED, punishment LED, house LED, beam break, buzzer, and camera. It uses `arduino-cli` for board discovery and sketch upload, and `pigpio` for GPIO control.

**Trainer** (`Controller/trainers/Trainer.py`) is an abstract base class. All trainers live in the `Controller/trainers/` package. Each training phase is a concrete subclass implementing a state machine via `run_training()`. The training phases in progression order are:
1. **Habituation** - reward exposure only, no stimuli
2. **InitialTouch** - any touch gets a reward
3. **MustTouch** - must touch the correct stimulus (A01)
4. **Punish_Incorrect** - incorrect touch triggers buzzer + punishment LED
5. **Simple_Discrimination** - correct/incorrect with correction trials (up to 3)
6. **Complex_Discrimination** - same as simple but with different stimuli (E01/D01)
7. **PRL** (Probabilistic Reversal Learning) - probabilistic reward contingencies

### State machine pattern

Each trainer uses an Enum-based state machine. `run_training()` is called repeatedly by the Session timer and advances one state transition per call. States follow: IDLE → START_TRAINING → START_TRIAL → [phase-specific states] → END_TRIAL → END_TRAINING. This non-blocking pattern allows the WebUI to remain responsive.

### M0 serial protocol

The M0 firmware (`M0Touch/M0Touch.ino`) responds to serial commands:
- `WHOAREYOU?` → `ID:M0_X` (board identification via address pins)
- `IMG:<name>` → preloads BMP from SD card (backlight stays off)
- `SHOW` → turns on backlight, enables single touch detection
- `BLACK` → backlight off, but touch detection stays active
- `OFF` → backlight off, touch detection disabled
- Touch events come back as `TOUCH:X=<x>,Y=<y>`

The newer `Controller/M0Device.py` manages serial via a state machine: UNINITIALIZED → PORT_CLOSED → PORT_OPEN → SERIAL_COMM. The older `Controller/m0_devices.py` is a simpler version (legacy).

### Virtual chamber

`Controller/Virtual/` provides hardware-free equivalents of all components (`VirtualChamber`, `VirtualM0Device`, `VirtualBeamBreak`, `VirtualLED`, `VirtualReward`, `VirtualBuzzer`) with identical APIs. Enable with `virtual_mode: true` in session config. Includes a tkinter GUI (`VirtualChamberGUI.py`) for interactive testing.

### Configuration

YAML-based configuration at three levels, loaded via `Config` class (`Controller/Config.py`):
- `~/session_config.yaml` - session-level (trainer name, rodent name, ITI, directories)
- `~/chamber_config.yaml` - chamber-level (GPIO pin assignments, camera device)
- `~/trainer_<Name>_config.yaml` - trainer-specific parameters

Config uses `ensure_param()` to set defaults without overwriting existing values.

### Data output

- Training data → JSON files in `/mnt/shared/data/` (event-based with timestamps)
- Video → `.ts` files in `/mnt/shared/videos/`
- Logs → `log/` directory (per-session, includes chamber name)

### Legacy code

`Controller/Main.py` and `Controller/GUI.py` contain an older PyQt5-based implementation with inline training logic (no state machines). The `src/peripherals/` directory has older peripheral classes used by `main.py`. The `Controller/m0_devices.py` is the legacy M0 device handler. Current development uses the newer state-machine trainers with WebUI.

## Key Dependencies

- **pigpio** - GPIO control (must run `sudo pigpiod` before use; gracefully degraded when unavailable)
- **pyserial** - M0 serial communication
- **nicegui** - Web-based control UI
- **netifaces** - IP address detection for auto-configuring chamber identity
- **PyYAML** - Configuration file handling
- **arduino-cli** - M0 sketch compilation and upload (located at `~/bin/arduino-cli`)
- Python 3.11, managed by `uv` (see `pyproject.toml` and `.python-version`)

## Hardware pin defaults (from Chamber.py)

- Reward LED (RGB): pins 13, 21, 26
- Punishment LED (RGB): pins 18, 19, 17
- House LED: pin 20
- Reward pump: pin 27
- Beam break: pin 4
- Buzzer: pin 16
- M0 reset pins: 25, 5, 6 (left, middle, right)

## Writing new trainers

1. Create `Controller/trainers/<TrainerName>.py`
2. Subclass `Trainer` (from `trainers.Trainer import Trainer`)
3. Define a `<TrainerName>State` Enum with at minimum: IDLE, START_TRAINING, START_TRIAL, END_TRIAL, END_TRAINING
4. Implement `start_training()`, `run_training()` (state machine, called repeatedly), and `stop_training()`
5. Use `self.config.ensure_param()` for all tunable parameters
6. Use default behavior methods: `default_start_trial()`, `default_iti_start()`, `default_stop_training()`, etc.
7. Use `self.write_event(event_name, data)` for data logging
8. Add the trainer name to `get_trainers()` in `Controller/trainers/__init__.py`
9. Access hardware via `self.chamber` (e.g., `self.chamber.left_m0.send_command("SHOW")`, `self.chamber.reward.dispense()`)

## Qwen3 local coding helper

A local coding model is available for boilerplate generation:
```bash
bash -lc 'qwen3_coder.sh "<prompt>"'
```
Backend: Qwen3-Coder-30B at `10.0.0.219:8080`. Review its output carefully before integrating.

# Access to physical hardware

Connect to a chamber at (ssh) nc4touch@100.109.168.91 for physical testing