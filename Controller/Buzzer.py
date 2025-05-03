import pigpio

class Buzzer:
    def __init__(self, pi=pigpio.pi(), pin=16, volume=60, frequency=6000):
        if not isinstance(pi, pigpio.pi):
            raise ValueError("pi must be an instance of pigpio.pi")

        self.pi = pi
        self.pin = pin
        self.volume = volume
        self.frequency = frequency

        self.pi.set_mode(self.pin, pigpio.OUTPUT)
        self.pi.set_PWM_dutycycle(self.pin, 0)  
        self.pi.set_PWM_range(self.pin, 100) 
        self.pi.set_PWM_frequency(self.pin, self.frequency)

    def activate(self):
        self.pi.set_PWM_dutycycle(self.pin, self.volume)
        print("Buzzer activated.")

    def deactivate(self):
        self.pi.set_PWM_dutycycle(self.pin, 0)
        print("Buzzer deactivated.")