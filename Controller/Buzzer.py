from pigpio_compat import pigpio
import logging
logger = logging.getLogger(f"session_logger.{__name__}")

class Buzzer:
    """Class to control a buzzer connected to a Raspberry Pi using pigpio."""
    def __init__(self, pi: pigpio.pi = None, pin: int = 16, volume: int = 60, frequency: int = 6000):
        """Initialize the Buzzer."""
        if pi is None and pigpio is not None:
            pi = pigpio.pi()
        if pigpio is not None and not isinstance(pi, pigpio.pi):
            logger.error("pi must be an instance of pigpio.pi")
            raise ValueError("pi must be an instance of pigpio.pi")
        if pi is not None and not getattr(pi, "connected", False):
            logger.error("pigpio client is not connected; Buzzer will run in no-hardware mode")
            pi = None

        self.pi = pi
        self.pin = pin
        self.volume = volume
        self.frequency = frequency

        if self.pi is None:
            logger.warning("pigpio not available; skipping buzzer pin setup")
            return

        self.pi.set_mode(self.pin, pigpio.OUTPUT)
        self.pi.set_PWM_dutycycle(self.pin, 0)
        self.pi.set_PWM_range(self.pin, 100)
        self.pi.set_PWM_frequency(self.pin, self.frequency)

    def activate(self):
        """Activate the buzzer."""
        if self.pi is None:
            logger.warning("pigpio not available; Buzzer.activate() simulated")
            return
        self.pi.set_PWM_dutycycle(self.pin, self.volume)
        logger.debug(f"Buzzer activated")

    def deactivate(self):
        """Deactivate the buzzer."""
        if self.pi is None:
            logger.warning("pigpio not available; Buzzer.deactivate() simulated")
            return
        self.pi.set_PWM_dutycycle(self.pin, 0)
        logger.debug(f"Buzzer deactivated")