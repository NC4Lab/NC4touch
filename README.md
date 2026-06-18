# NC4Touch



## Project Overview

NC4Touch is split into three connected parts:

- Physical chamber: the main runtime hardware stack in [Controller/Chamber.py](Controller/Chamber.py) combines the touchscreen display manager, LEDs, reward pump, beam-break sensor, buzzer, camera, and configuration system into one chamber interface used by the trainers.
- Virtual Chamber: the code under [Controller/Virtual/](Controller/Virtual) mirrors the physical chamber API so trainers, sessions, and display logic can be developed and tested without hardware.
- WebUI: [Controller/WebUI.py](Controller/WebUI.py) provides the NiceGUI control panel used to configure sessions, start and stop tasks, monitor logs, and interact with the chamber during runs.

---

# Setting Up Raspberry Pi OS with SSH and VS Code Remote Development

## Install Raspberry Pi OS

1. Instal Raspberry Pi Imager `https://www.raspberrypi.com/software/`.

2. Plug a micro SD card into an addapter on your computer.

3. Set the following:
   - Rasberry Pi Device: `Raspberry Pi 4`
   - Operating System: `Raspberry Pi OS (64-bit)`
   - Operating System: The drive associated with your SD card.

4. Edit settings when prompted:
   - **Set username and password**
      - **Username**: `nc4touch`
      - **Password**: `1434`
   - **Set lacale settings**
      - Check the box
      - **Timezone**: `US/Vanvouver`
      - **Keyboard**: `us`
- **SERVICES** Tab
   - **Enable SSH**: Checked and set to `Use password authentication` 

1. Apply the setup settings to the SD card.

2. Install Updates

   Plug in the SD card and power on the Pi
   Open a terminal and run:
   ```
   sudo apt update
   sudo apt full-upgrade -y
   ``` 
   
   Reboot:
   ```
   sudo reboot
   ```

## Hardware Modules

### Touchscreen Display Manager

The touchscreen display manager is the physical chamber's main stimulus surface. It drives the wide chamber display as three logical touch zones, handles image loading and clearing, and keeps the visual state synchronized with the trainers. The display layer also resolves the correct output and geometry for the physical panel so the chamber can use the touchscreen in fullscreen mode without exposing window chrome. In practice, trainers send commands such as show, clear, and image load through the chamber interface, and the display manager translates those commands into updates on the physical screens.

### LEDs

The chamber uses LEDs for state cues and task feedback. There is a back LED, a front LED, and a house LED, each controlled through the chamber abstraction so trainers do not need to touch GPIO directly. LEDs can be activated, deactivated, and in some cases brightness-adjusted or color-adjusted depending on the hardware wiring. They are used to signal task phases, reward states, and other behavioral cues, and they are also exposed in the chamber state so the WebUI and trainers can read or change them consistently.

### Reward Pump

The reward pump dispenses liquid reward on demand. It is driven from the chamber as a simple on/off actuator, with `dispense()` starting the pump and `stop()` shutting it down. Trainers use the reward system during reinforcement events and timed reward delivery, while the chamber keeps the pump pin in a known low state when idle. This module is intentionally minimal so reward timing stays under trainer control.

### Beam-Break Sensor

The beam-break sensor detects whether the animal is at the hopper. The chamber reads it as a latched state with a short memory window so brief transitions do not get lost between polling cycles. A broken beam means the subject is present, and a restored beam means the hopper is clear again after the memory interval expires. Trainers use this signal to gate reward delivery, session progression, and response timing.

### Buzzer

The buzzer provides audio cues for feedback and task events. It is controlled through PWM, which allows the chamber to switch the buzzer on and off cleanly while keeping the frequency and volume configurable. In training tasks, the buzzer can mark a phase change, reinforce a correct action, or provide a short alert without needing any direct UI intervention.

### Camera

The camera module starts and manages the live video stream used by the WebUI. It automatically finds a usable video device when possible, starts the streaming process, and can reinitialize if the stream needs to be restarted. On physical hardware, this is what gives the operator a live view of the chamber while a task is running. The module also supports recording workflows and camera-specific controls when the underlying device exposes them.

### Configuration System

The configuration system is the glue that keeps the chamber, trainers, and WebUI aligned. It stores chamber parameters such as pin assignments, display geometry, camera device paths, and default brightness values, while also remembering which settings were explicitly supplied versus filled in by defaults. This makes it possible to run the same code across physical and virtual setups without rewriting every caller. Most components read their settings from the shared chamber configuration, so behavior stays consistent from startup through training.

## Pi-Level / Headless Mode

The physical chamber does not need the Raspberry Pi desktop environment. For day-to-day use, it is cleaner to boot straight to the console and start the WebUI from a shell or service instead of launching a graphical session.

To do that, keep the Pi in multi-user mode with the desktop disabled, for example by using the boot option already shown earlier in this document:

```text
systemd.unit=multi-user.target autologin-user=nc4 nosplash
```

Then start the launcher from SSH or a local tty:

```bash
cd /mnt/shared/code/NC4Touch
./scripts/start_webUI.sh
```

In this mode, the chamber display is controlled directly by the application, the touchscreen screens stay tied to task execution, and no separate desktop interface is shown on the Pi itself.

   