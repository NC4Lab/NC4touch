"""Compatibility wrapper for pigpio on newer Raspberry Pi hardware.

This module prefers real pigpio when available/connected, but can fall back to
local RPi.GPIO (rpi-lgpio shim) for single-host GPIO control.
"""

import logging
import importlib
from typing import Any

logger = logging.getLogger(f"session_logger.{__name__}")

try:
    import pigpio as _real_pigpio
except ImportError:
    _real_pigpio = None

try:
    _gpio: Any = importlib.import_module("RPi.GPIO")
except ModuleNotFoundError:
    _gpio = None


def _is_local_host(host):
    if host is None:
        return True
    if isinstance(host, str) and host.strip() in {"", "localhost", "127.0.0.1"}:
        return True
    return False


def _prefer_local_fallback():
    """Return True on local platforms known to be unsupported by pigpio daemon."""
    try:
        with open("/proc/device-tree/compatible", "rb") as fh:
            compatible = fh.read()
        return b"brcm,bcm2712" in compatible
    except OSError:
        return False


class _LocalPi:
    """Small subset of pigpio.pi API implemented via RPi.GPIO."""

    _mode_set = False

    def __init__(self):
        self.connected = _gpio is not None
        self._pwm_ranges = {}
        self._pwm_freqs = {}
        self._pwms = {}

        if self.connected and not _LocalPi._mode_set:
            _gpio.setwarnings(False)
            _gpio.setmode(_gpio.BCM)
            _LocalPi._mode_set = True

    def set_mode(self, pin, mode):
        if not self.connected:
            return
        if mode == pigpio.OUTPUT:
            _gpio.setup(pin, _gpio.OUT, initial=_gpio.LOW)
        else:
            _gpio.setup(pin, _gpio.IN)

    def set_pull_up_down(self, pin, pud):
        if not self.connected:
            return
        pull = _gpio.PUD_OFF
        if pud == pigpio.PUD_UP:
            pull = _gpio.PUD_UP
        elif pud == pigpio.PUD_DOWN:
            pull = _gpio.PUD_DOWN
        _gpio.setup(pin, _gpio.IN, pull_up_down=pull)

    def read(self, pin):
        if not self.connected:
            return 1
        return _gpio.input(pin)

    def write(self, pin, value):
        if not self.connected:
            return
        _gpio.output(pin, _gpio.HIGH if value else _gpio.LOW)

    def set_PWM_range(self, pin, pwm_range):
        self._pwm_ranges[pin] = max(int(pwm_range), 1)

    def set_PWM_frequency(self, pin, frequency):
        freq = max(int(frequency), 1)
        self._pwm_freqs[pin] = freq
        pwm = self._pwms.get(pin)
        if pwm is not None:
            pwm.ChangeFrequency(freq)
        return freq

    def set_PWM_dutycycle(self, pin, dutycycle):
        if not self.connected:
            return

        pwm_range = self._pwm_ranges.get(pin, 255)
        duty = max(0, min(int(dutycycle), pwm_range))
        duty_pct = (100.0 * duty) / float(pwm_range)

        if pin not in self._pwms:
            if pin not in self._pwm_freqs:
                self._pwm_freqs[pin] = 5000
            _gpio.setup(pin, _gpio.OUT, initial=_gpio.LOW)
            self._pwms[pin] = _gpio.PWM(pin, self._pwm_freqs[pin])
            self._pwms[pin].start(0)

        self._pwms[pin].ChangeDutyCycle(duty_pct)


class _PigpioCompat:
    # Match common pigpio constant values so existing code behavior stays intact.
    INPUT = getattr(_real_pigpio, "INPUT", 0)
    OUTPUT = getattr(_real_pigpio, "OUTPUT", 1)
    PUD_OFF = getattr(_real_pigpio, "PUD_OFF", 0)
    PUD_DOWN = getattr(_real_pigpio, "PUD_DOWN", 1)
    PUD_UP = getattr(_real_pigpio, "PUD_UP", 2)

    class pi:
        def __init__(self, host=None, port=8888):
            self.connected = False
            self._backend = None
            self._using_fallback = False

            wants_local = _is_local_host(host)
            prefer_fallback = wants_local and _prefer_local_fallback()

            if _real_pigpio is not None and not prefer_fallback:
                if host is None:
                    backend = _real_pigpio.pi()
                else:
                    backend = _real_pigpio.pi(str(host), int(port))
                if getattr(backend, "connected", False):
                    self._backend = backend
                    self.connected = True
                    return
                if not wants_local:
                    self._backend = backend
                    self.connected = False
                    return

            if wants_local and _gpio is not None:
                self._backend = _LocalPi()
                self.connected = bool(getattr(self._backend, "connected", False))
                self._using_fallback = self.connected
                if self.connected:
                    logger.warning(
                        "Using local RPi.GPIO backend because pigpio daemon is unavailable."
                    )

        def __getattr__(self, name):
            if self._backend is None:
                raise AttributeError(name)
            return getattr(self._backend, name)


pigpio = _PigpioCompat()
