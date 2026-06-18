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

## Pi-Level / Minimal Display Mode

The physical chamber does not need the full Raspberry Pi desktop interface, but it does need a graphical session. The display manager uses Pygame and `xrandr` to render stimulus images on the touchscreen, so booting into pure multi-user console mode can prevent images from displaying.

The recommended setup is a minimal LXDE-pi session: X is running, but the panel, desktop file manager, and screensaver are disabled for the chamber user.

### Use Desktop Autologin

Use Raspberry Pi's configuration tool:

```bash
sudo raspi-config
```

Choose:

```text
System Options -> Boot / Auto Login -> Desktop Autologin
```

This boots to the graphical target with X running, which Pygame needs.

### Disable LXDE Session Components Per Pi

Create a per-user LXDE autostart override. This is better than editing `/etc/xdg/lxsession/LXDE-pi/autostart` because the code directory is shared, while each chamber/Pi can keep its own local desktop behavior.

```bash
mkdir -p ~/.config/lxsession/LXDE-pi
cp /etc/xdg/lxsession/LXDE-pi/autostart ~/.config/lxsession/LXDE-pi/autostart
nano ~/.config/lxsession/LXDE-pi/autostart
```

Comment out or remove the desktop UI components:

```bash
# @lxpanel --profile LXDE-pi
# @pcmanfm --desktop --profile LXDE-pi
# @xscreensaver -no-splash
```

Add display power-management disables so the chamber display does not blank during long sessions:

```bash
@xset s off
@xset -dpms
@xset s noblank
```

Then reboot:

```bash
sudo reboot
```

This configuration:
- Boots to the graphical desktop (X11 server runs)
- Skips the panel and file manager
- Disables the screensaver/display blanking
- Leaves the physical display clear for WebUI stimuli
- Allows SSH access and remote development
- Enables Pygame to render fullscreen stimuli on the touchscreen

**Important:** Do not use `systemd.unit=multi-user.target` in `/boot/cmdline.txt` for chamber operation. It disables the graphical session entirely, which can break Pygame image rendering.

### Start the WebUI Manually

After the Pi boots, SSH into it and run:

```bash
cd /mnt/shared/code/NC4Touch
./scripts/start_webUI.sh
```

The WebUI runs on the Pi and can be opened from another computer on the same network at:

```text
http://<pi-ip-address>:8081
```

The live camera stream uses port `8080`.

### Start the WebUI Automatically

For regular chamber use, install a systemd service so the WebUI starts after boot. Create `/etc/systemd/system/nc4touch-webui.service`:

```ini
[Unit]
Description=NC4Touch WebUI
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=nc4touch
WorkingDirectory=/mnt/shared/code/NC4Touch
ExecStart=/mnt/shared/code/NC4Touch/scripts/start_webUI.sh
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Then enable and start it:

```bash
sudo systemctl daemon-reload
sudo systemctl enable nc4touch-webui.service
sudo systemctl start nc4touch-webui.service
```

Check status and logs with:

```bash
sudo systemctl status nc4touch-webui.service
journalctl -u nc4touch-webui.service -f
```

In this mode, the Pi has no separate desktop UI. NC4Touch owns the chamber display during tasks, while operators control the chamber through the WebUI from another machine.

   
