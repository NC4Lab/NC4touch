from pigpio_compat import pigpio
import time

import logging
logger = logging.getLogger(f"session_logger.{__name__}")

class Reward:
    def __init__(self, pi=None, pin=27):
        if pi is None and pigpio is not None:
            pi = pigpio.pi()
        if pigpio is None:
            logger.error("pigpio is not available; cannot initialize Reward")
            raise RuntimeError("pigpio is not available; cannot initialize Reward")
        if not isinstance(pi, pigpio.pi):
            logger.error("pi must be an instance of pigpio.pi")
            raise ValueError("pi must be an instance of pigpio.pi")
        if not pi.connected:
            logger.error("pigpio daemon is not connected; cannot initialize Reward")
            raise RuntimeError("pigpio daemon is not connected; cannot initialize Reward")

        self.pi = pi
        self.pin = pin
        self.state = False

        """PWM set up"""
        mode_status = self.pi.set_mode(self.pin, pigpio.OUTPUT)
        if mode_status != 0:
            logger.error("Failed to set reward pin %s mode (status=%s)", self.pin, mode_status)
            raise RuntimeError(f"Failed to set reward pin mode for pin {self.pin}")
        # Explicitly write LOW immediately to override boot-time pull-up
        write_status = self.pi.write(self.pin, 0)
        if write_status != 0:
            logger.error("Failed to initialize reward pin %s low (status=%s)", self.pin, write_status)
            raise RuntimeError(f"Failed to initialize reward pin {self.pin} low")

        pwm_range_status = self.pi.set_PWM_range(self.pin, 255)
        if pwm_range_status < 0:
            logger.error("Failed to set PWM range for reward pin %s (status=%s)", self.pin, pwm_range_status)
            raise RuntimeError(f"Failed to set PWM range for reward pin {self.pin}")

        pwm_freq_status = self.pi.set_PWM_frequency(self.pin, 5000)
        if pwm_freq_status <= 0:
            logger.error("Failed to set PWM frequency for reward pin %s (status=%s)", self.pin, pwm_freq_status)
            raise RuntimeError(f"Failed to set PWM frequency for reward pin {self.pin}")

        pwm_init_status = self.pi.set_PWM_dutycycle(self.pin, 0)
        if pwm_init_status != 0:
            logger.error("Failed to initialize PWM duty cycle for reward pin %s (status=%s)", self.pin, pwm_init_status)
            raise RuntimeError(f"Failed to initialize PWM duty cycle for reward pin {self.pin}")
    
    def __del__(self):
        self.stop()

    def dispense(self):
        # Turn on the pump
        logger.debug("Dispensing reward")
        status = self.pi.set_PWM_dutycycle(self.pin, 255)
        if status != 0:
            logger.error("Failed to start reward pump on pin %s (status=%s)", self.pin, status)
            raise RuntimeError(f"Failed to start reward pump on pin {self.pin}")
        self.state = True

    def stop(self):
        logger.debug("Stopping reward")
        status = self.pi.set_PWM_dutycycle(self.pin, 0)
        if status != 0:
            logger.error("Failed to stop reward pump on pin %s (status=%s)", self.pin, status)
            raise RuntimeError(f"Failed to stop reward pump on pin {self.pin}")
        self.state = False