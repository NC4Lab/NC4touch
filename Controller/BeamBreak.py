from pigpio_compat import pigpio
import time
import threading

import logging
logger = logging.getLogger(f"session_logger.{__name__}")

class BeamBreak:
    """Class to manage a beam break sensor using pigpio."""
    def __init__(self, pi: pigpio.pi = None, pin: int = 4, beam_break_memory: float = 0.2):
        """Initialize the BeamBreak sensor."""
        if pi is None and pigpio is not None:
            pi = pigpio.pi()
        if pigpio is not None and not isinstance(pi, pigpio.pi):
            logger.error("pi must be an instance of pigpio.pi")
            raise ValueError("pi must be an instance of pigpio.pi")
        if pi is not None and not getattr(pi, "connected", False):
            logger.error("pigpio client is not connected; BeamBreak will run in no-hardware mode")
            pi = None

        self.pi = pi
        self.pin = pin

        self.last_break_time = time.time()
        self.beam_break_memory = beam_break_memory  # 200 ms
        self.read_interval = 0.05  # 50 ms
        self.read_timer = threading.Timer(self.read_interval, self._read_loop)
        self.state = False  # False = beam broken, True = beam not broken

        if self.pi is None:
            logger.warning("pigpio not available; skipping beam break pin setup")
            return

        self.pi.set_mode(self.pin, pigpio.INPUT)
        self.pi.set_pull_up_down(self.pin, pigpio.PUD_UP)
    
    def _read_loop(self):
        """Internal method to read the beam break state."""
        self.read_timer.cancel()
        current_time = time.time()

        if self.pi is None:
            self.state = True
            self.read_timer = threading.Timer(self.read_interval, self._read_loop)
            self.read_timer.start()
            return

        reading = self.pi.read(self.pin)
        if reading == 0: # Beam is broken
            self.last_break_time = current_time
            self.state = False
        elif current_time - self.last_break_time > self.beam_break_memory:
            self.state = True

        self.read_timer = threading.Timer(self.read_interval, self._read_loop)
        self.read_timer.start()

    def activate(self):
        """Start the beam break sensor reading loop."""
        if self.pi is None:
            logger.warning("pigpio not available; BeamBreak.activate() simulated")
        self.read_timer.cancel()
        self.read_timer = threading.Timer(self.read_interval, self._read_loop)
        self.read_timer.start()
        logger.debug("BeamBreak activated.")

    def deactivate(self):
        """Stop the beam break sensor reading loop."""
        self.read_timer.cancel()
        logger.debug("BeamBreak deactivated.")