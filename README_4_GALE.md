## Overview
The setup for the LCDs might be a bit confusing. Basically, it should just work with 2 displays so long as the wiring is correct.

Use the pin mapping found here:
/home/nc4/TouchscreenApparatus/src/drivers/nc4_ili9488/README.md

Wire the two LCDs based on the pins for LCD_1 and LCD_2 (CE1 and CE2) and skip LCD_0 (CE0). Why it is this way I have no idea.

The following class handles the display stuff:
/home/nc4/TouchscreenApparatus/src/peripherals/lcd.py

Setup the I2C using the suggested pin mapping from that same readme. Try I2C busses 1 and 3 or you can try 4.

You will likely need to set some things in the config file:
/boot/firmware/config.txt

Namely, in those settings, you will probably have to set some things to enable the additional I2C busses. I made some notes for this in the main README but you will need to confirm all this:
/home/nc4/TouchscreenApparatus/README.md

Use this script as the basis of your main python code:
/home/nc4/TouchscreenApparatus/main.py

In terms of wiring everything else up, I am not sure there will be enough pins. If we are not worried about adding the 3rd display's SPI and I2C, it may be fine. Otherwise, we may need an IO extender.