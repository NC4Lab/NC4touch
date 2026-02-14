try:
    import pigpio
except ImportError:
    pigpio = None
import logging
logger = logging.getLogger(f"session_logger.{__name__}")

class Buzzer:
    def __init__(self, pi=None, pin=16, volume=60, frequency=6000):
        self.pi = pi
        self.pin = pin
        self.volume = volume
        self.frequency = frequency

        if self.pi is not None:
            self.pi.set_mode(self.pin, pigpio.OUTPUT)
            self.pi.set_PWM_dutycycle(self.pin, 0)
            self.pi.set_PWM_range(self.pin, 100)
            self.pi.set_PWM_frequency(self.pin, self.frequency)

    def activate(self):
        if self.pi is not None:
            self.pi.set_PWM_dutycycle(self.pin, self.volume)
        logger.debug(f"Buzzer activated")

    def deactivate(self):
        if self.pi is not None:
            self.pi.set_PWM_dutycycle(self.pin, 0)
        logger.debug(f"Buzzer deactivated")
