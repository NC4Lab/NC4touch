# Instructions to build, install, and test the nc4_ili9488 driver.

## Install dependencies

- Make sure you have installed kernel headers and build tools:
```
sudo apt-get update
```
```
sudo apt-get install raspberrypi-kernel-headers build-essential git device-tree-compiler fbi -y
```
The "fbi" tool is used for testing by showing images on the framebuffer.

## Set up the device tree overlay

Add the following lines to to /boot/firmware/config.txt:
```
sudo nano /boot/firmware/config.txt
```
```
[all]
# ili9488 dirver
dtoverlay=nc4_ili9488
# Use increased debugging level
dtdebug=on
```
Confirm this line is also present in config.txt:
```
dtparam=spi=on
```

Go to the driver directory:
```
cd /home/nc4/TouchscreenApparatus/src/drivers/nc4_ili9488
```

Compile the overlay file to a .dtbo binary:
```
sudo dtc -@ -I dts -O dtb -o /boot/overlays/nc4_ili9488.dtbo nc4_ili9488-overlay.dts
```

Print the contents o /boot/firmware/config.txt:
```
cat /boot/firmware/config.txt
```

Reboot if you are stopping here:
```
sudo reboot
```

All commands:
```
cd /home/nc4/TouchscreenApparatus/src/drivers/nc4_ili9488
sudo dtc -@ -I dts -O dtb -o /boot/overlays/nc4_ili9488.dtbo nc4_ili9488-overlay.dts
cat /boot/firmware/config.txt
sudo reboot
```

## Build the driver

Go to the driver directory:
```
cd /home/nc4/TouchscreenApparatus/src/drivers/nc4_ili9488
```

Do a build clean (Optional)
```
make clean || true
```

In the driver directory run:
```
make
```
If successful, this produces nc4_ili9488.ko

Verify the file was created:
```
ls nc4_ili9488.ko
```

All commands:
```
cd /home/nc4/TouchscreenApparatus/src/drivers/nc4_ili9488
make clean || true
make
ls nc4_ili9488.ko
```

## Install the driver

Create the /lib/modules/$(uname -r)/extra if needed:
```
sudo mkdir -p /lib/modules/$(uname -r)/extra
```

Copy the driver to it:
```
sudo cp nc4_ili9488.ko /lib/modules/$(uname -r)/extra/
```

Update module dependencies:
```
sudo depmod -a
```

Confirm that the driver is available:
```
modinfo nc4_ili9488
```

All commands:
```
sudo mkdir -p /lib/modules/$(uname -r)/extra
sudo cp nc4_ili9488.ko /lib/modules/$(uname -r)/extra/
sudo depmod -a
modinfo nc4_ili9488
```

## Load and install the driver:

Load the module:
```
sudo modprobe nc4_ili9488
```

Check if the module is loaded:
```
lsmod | grep nc4_ili9488
```

Check dmesg for logs:
```
dmesg | grep nc4_ili9488
```
If successful, you should see something like:
- "nc4_ili9488 panel registered at /dev/fb0"
- "nc4_ili9488 panel registered at /dev/fb1"

To load the driver at every boot, add "nc4_ili9488" to /etc/modules or create a file in /etc/modules-load.d/:
```
echo nc4_ili9488 | sudo tee /etc/modules-load.d/nc4_ili9488.conf
```

Reboot:
```
sudo reboot
```

## Run checks
    
Increase the console log level (Optional):
```
sudo dmesg -n 8
```

Verify the overlay's boot application using:
```
dmesg | grep -i 'nc4_ili9488'
```
Expected outcomes: Should see `Initialized nc4_ili9488` along with any error messages
If this fails try unloading and reloading the module
```
sudo rmmod nc4_ili9488
sudo insmod /lib/modules/$(uname -r)/extra/nc4_ili9488.ko
dmesg | grep -i 'nc4_ili9488'
```

Run the following command to ensure the nc4_ili9488 overlay was successfully loaded:
```
ls /proc/device-tree/overlays/nc4_ili9488
```
Expected outcomes: the directory exists and contains files like `status` and `name.

Check for errors in the .dtbo
```
sudo dtc -I dtb -O dts -o /dev/null /boot/overlays/nc4_ili9488.dtbo
```

## Debugging

### System checks

Check driver kernel log:
```
dmesg | grep nc4_ili9488
```
Check that:
- SPI wiring and GPIO assignments match your hardware.
- Your image matches the resolution. fbi will scale or crop as needed.

Check Kernel Logs for Overlay Errors
```
dmesg | grep -i 'overlay'
```

Verify the overlay's boot application using:
```
dmesg | grep -i 'nc4_ili9488'
```

Check active frame buffers
```
ls /dev/fb*
```

Check for SPI 
```
ls /dev/spi*
```

Directly Inspect the Alias Mapping: Run:
```
cat /sys/firmware/devicetree/base/aliases/gpio
```

### Manual Commands

Manually load the overlay at runtime to get immediate feedback:
```
sudo dtoverlay nc4_ili9488
dmesg | tail -50
```

Turn the backlight on (maximum brightness):
```
echo 1 | sudo tee /sys/class/backlight/soc:backlight/brightness
```

Turn the backlight off:
```
echo 0 | sudo tee /sys/class/backlight/soc:backlight/brightness
```

Draw an image to the fb0 buffer:
```
sudo fbi -d /dev/fb0 -T 1 /home/nc4/TouchscreenApparatus/data/images/A01.bmp
```

### General

### Search for a specific file that matches a string:
```
sudo find / -type f -name "*nc4_ili9488*" 2>/dev/null
```

### Search all files that contain a given string
```
sudo grep -rli "nc4_ili9488" / 2>/dev/null
```

### Search within subfolders for files that contain a given string
```
sudo grep -rli "nc4_ili9488" /home/nc4/TouchscreenApparatus/src/drivers/nc4_ili9488/ 2>/dev/null
```

### Other

Decompile the .dtbo to a .dts
```
sudo dtc -I dtb -O dts -o /home/nc4/TouchscreenApparatus/debug/nc4_ili9488.dts /boot/overlays/nc4_ili9488.dtbo
```

# Uninstall the nc4_ili9488 driver

## Unload the driver
```
sudo rmmod nc4_ili9488
```
If you encounter "module is in use", run:
```
sudo modprobe -r nc4_ili9488
```

## Remove the Driver File
```
sudo rm sudo insmod /lib/modules/$(uname -r)/extra/nc4_ili9488.ko
```

## Update Module Dependencies
```
sudo depmod
```

## Clear any cached kernel module information
```
sudo modprobe -c | grep nc4_ili9488
```
``` 
"spi0.0" | sudo tee /sys/bus/spi/drivers/nc4_ili9488/unbind
```

## Rebuild the Initramfs (Critical!):
```
sudo update-initramfs -u
```

## Remove the overlay
```
sudo rm /boot/firmware/overlays/nc4_ili9488.dtbo
```

## Comment out line in config.txt:
```
sudo nano /boot/firmware/config.txt
```
```
dtoverlay=nc4_ili9488
```

## Confirm the kernel module no longer loaded
```
lsmod | grep nc4_ili9488
```

## Power off
```
sudo poweroff
```

## All commands:
```
sudo rmmod nc4_ili9488
sudo modprobe -r nc4_ili9488
sudo rm /lib/modules/$(uname -r)/extra/nc4_ili9488.ko
sudo depmod
sudo modprobe -c | grep nc4_ili9488
"spi0.0" | sudo tee /sys/bus/spi/drivers/nc4_ili9488/unbind
sudo update-initramfs -u
sudo rm /boot/firmware/overlays/nc4_ili9488.dtbo
sudo nano /boot/firmware/config.txt
dtoverlay=nc4_ili9488
lsmod | grep nc4_ili9488
sudo poweroff
```

## Unplig and replug the power

## Verify Removal
```
modinfo nc4_ili9488
```

Check for Residual Entries in /proc/device-tree:
```
grep -ril 'nc4_ili9488' /proc/device-tree/
```

Verify No Kernel Logs Reference:
```
dmesg | grep -i 'nc4_ili9488'
```
Expected outcome: No references to nc4_ili9488 in the logs.

Check for Residual SPI Driver Bindings for each SPI device:
```
ls -l /sys/bus/spi/devices/spi0.0/driver
ls -l /sys/bus/spi/devices/spi0.1/driver
```

Search for Residual Configurations
```
grep -i 'nc4_ili9488' /boot/config.txt
```
```
grep -ril 'nc4_ili9488' /boot/
```

Confirm No Residual Modules in /lib/modules
```
find /lib/modules/$(uname -r)/ -name '*nc4_ili9488*'
```