import pigpio

class LED:
    def __init__(self, pi, pin=21, r_pin=None, g_pin=None, b_pin=None, frequency=5000, range=255, brightness=140):
        if pi is None:
            pi = pigpio.pi()
        if not isinstance(pi, pigpio.pi):
            raise ValueError("pi must be an instance of pigpio.pi")

        self.pi = pi
        self.pin = pin
        self.frequency = frequency
        self.range = range
        self.brightness = brightness
        self.r_pin = r_pin
        self.g_pin = g_pin
        self.b_pin = b_pin
        self.color = (0, 0, 0)

        self.pi.set_mode(self.pin, pigpio.OUTPUT)
        self.pi.set_PWM_frequency(self.pin, self.frequency)
        self.pi.set_PWM_range(self.pin, self.range)
        self.pi.set_PWM_dutycycle(self.pin, 0)  
    
    def set_color(self, r, g, b):
        self.color = (r, g, b)
        if self.r_pin is not None:
            self.pi.set_PWM_dutycycle(self.r_pin, r)
        if self.g_pin is not None:
            self.pi.set_PWM_dutycycle(self.g_pin, g)
        if self.b_pin is not None:
            self.pi.set_PWM_dutycycle(self.b_pin, b)


    def activate(self):
        self.pi.set_PWM_dutycycle(self.pin, self.brightness)

    def deactivate(self):
        self.pi.set_PWM_dutycycle(self.pin, 0)
