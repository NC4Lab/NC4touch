A. Compile the Overlay
Create test_mini_overlay.dts in some folder, for example ~/overlays/.

Compile into a .dtbo:
```
cd /home/nc4/TouchscreenApparatus/tests/test_mini_driver
```
```
dtc -@ -I dts -O dtb -o test_mini_overlay.dtbo test_mini_overlay.dts
```

Copy it to your Pi’s overlay directory:
```
sudo cp test_mini_overlay.dtbo /boot/overlays/
```

Edit /boot/config.txt (or /boot/firmware/config.txt on some distros) to load your overlay at boot:
```
sudo nano /boot/firmware/config.txt
```
```
dtoverlay=test_mini_overlay
```

B. Reboot to Load the Overlay
Reboot:
```
sudo reboot
```

After reboot, check logs:
```
dmesg | grep -i 'test_mini'
```
You may see something like “(overlay) test_mini_overlay loaded successfully” if everything’s working.

Alternatively, you can inspect /proc/device-tree/soc/spi@7e204000 to see if test_mini@0 node is there:
```
ls /proc/device-tree/soc/spi@7e204000/
```
You should see a directory named test_mini@0.

C. Build and Insert the Driver
Build the out-of-tree driver:
```
cd /home/nc4/TouchscreenApparatus/tests/test_mini_driver
```
```
make
```

This should produce test_mini_driver.ko.

Insert the module:
```
sudo insmod test_mini_driver.ko
```
```
sudo modprobe test_mini_driver
```

If successful, you’ll see a test_mini_driver: Probed! message in dmesg if the overlay is present and the node matched.

Check logs:
```
dmesg | grep -i 'test_mini'
```
If the overlay node is found, the driver’s probe() function logs “Probed! (dev=...).”

Verify it’s loaded:
```
lsmod | grep test_mini
```
Should show test_mini_driver.

(Optional) Remove the module to test the remove() function:
```
sudo rmmod test_mini_driver
```
```
dmesg | grep -i 'test_mini'
```
You’ll see “Removed!” if it’s removed cleanly.
