import pigpio
import time

class Reward:
    def __init__(self, pi, pin):
        self.pi = pi
        self.pin = pin
        self.is_priming = False
        self.reward_duration_ms = 1500  
        self.setup_reward()

    def setup_reward(self):
        """PWM set up"""
        self.pi.set_mode(self.pin, pigpio.OUTPUT)
        self.pi.set_PWM_dutycycle(self.pin, 0)
        self.pi.set_PWM_range(self.pin, 255)
        self.pi.set_PWM_frequency(self.pin, 5000)

    def dispense_reward(self, duration_s=None):
        """
        Turn on the pump (max duty cycle).
        If duration_s is given, the main code is responsible for timing and stopping the pump.
        """
        print(f"Dispensing reward{' (duration_s=' + str(duration_s) + ')' if duration_s else ''}")
        self.pi.set_PWM_dutycycle(self.pin, 255)

    def stop_reward_dispense(self):
        self.pi.set_PWM_dutycycle(self.pin, 0)
        print("Reward dispensing stopped.")

    def prime_feeding_tube(self):
        self.is_priming = True
        start_time = time.time()
        print("Priming started")
        try:
            while self.is_priming and (time.time() - start_time) < 20:  # ~20 seconds max
                self.pi.set_PWM_dutycycle(self.pin, 255)
                time.sleep(0.1)
            self.pi.set_PWM_dutycycle(self.pin, 0)
            if self.is_priming:
                print("Priming finished.")
        except Exception as e:
            self.stop_priming()
            print(f"Error during priming: {e}")

    def stop_priming(self):
        self.pi.set_PWM_dutycycle(self.pin, 0)
        self.is_priming = False
        print("Priming stopped.")

    def cleanup(self):
        self.stop_reward_dispense()  
        self.pi.set_PWM_dutycycle(self.pin, 0)
