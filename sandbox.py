# On a Raspberry Pi 4, create initial functions for the project

import smbus
import RPi.GPIO as GPIO
import time

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(27, GPIO.OUT)

I2C_CHANNEL = 1

class Buzzer:
    def __init__(self, pin):
        self.pin = pin
        self.volume = 15

        GPIO.setup(self.pin, GPIO.OUT)
        self.pwm = GPIO.PWM(self.pin, 50)
        self.pwm.start(0)
    
    def activate(self):
        self.pwm.ChangeDutyCycle(self.volume)
        time.sleep(2.0)
        self.pwm.ChangeDutyCycle(0)
        
    


# Scan I2C bus for devices
def scan_i2c():
    i2c = smbus.SMBus(I2C_CHANNEL)
    devices = []
    for addr in range(0x03, 0x78):
        try:
            i2c.read_byte(addr)
            devices.append(addr)
        except:
            pass
    return devices

if __name__ == '__main__':
    print(scan_i2c())
    Buzzer buzzer(12)
    buzzer.activate()