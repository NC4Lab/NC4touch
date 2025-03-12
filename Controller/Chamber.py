# Chamber class for the Touchscreen chamber
#
# Manu Madhav
# 2025

import pigpio
from LED import LED
from Reward import Reward
from BeamBreak import BeamBreak
from Buzzer import Buzzer
from M0Initializer import M0Initializer
from m0_devices import M0Device

import time
import serial

class Chamber:
  def __init__(self,
               reward_LED_pin = 21,
               reward_pump_pin = 27,
               beambreak_pin = 4,
               punishment_LED_pin = 17,
               buzzer_pin = 16,
               reset_pins = [6, 5, 25]):
    self.reward_LED_pin = reward_LED_pin
    self.reward_pump_pin = reward_pump_pin
    self.beambreak_pin = beambreak_pin
    self.punishment_LED_pin = punishment_LED_pin
    self.buzzer_pin = buzzer_pin
    self.reset_pins = reset_pins

    self.pi = pigpio.pi()

    # self.reward_LED = LED(self.pi, self.reward_LED_pin, brightness = 140)
    # self.reward = Reward(self.pi, self.reward_pump_pin)
    # self.beambreak = BeamBreak(self.pi, self.beambreak_pin)
    # self.punishment_LED = LED(self.pi, self.punishment_LED_pin, brightness = 255)
    # self.buzzer = Buzzer(self.pi, self.buzzer_pin)

    # Initialize M0s and find the ports
    self.m0_initializer = M0Initializer(self.pi)
    self.m0_initializer.find_all_m0_devices()

    self.m0s = []
    k=0
    for device, port in self.m0_initializer.device_map.items():
      k+=1
      m0 = M0Device(f"M0_{k}", port_path = port, pi = self.pi)
      self.m0s.append(m0)
      print(f"Initialized M0 {device} on {port}")


if __name__ == "__main__":
  chamber = Chamber()
  print("Chamber initialized.")
  input("Press Enter to exit.")
  print("Chamber stopped.")