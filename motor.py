import RPi.GPIO as GPIO
import time

class MotorDriver:
    """
    DC motor driver with L298N chip.
    """
    def __init__(self, in1_pin, in2_pin, ena_pin, in3_pin, in4_pin, enb_pin, pwm_freq=1000):
        # Motor A (Left)
        self.IN1 = in1_pin
        self.IN2 = in2_pin
        self.ENA = ena_pin
        
        # Motor B (Right)
        self.IN3 = in3_pin
        self.IN4 = in4_pin
        self.ENB = enb_pin
        
        GPIO.setmode(GPIO.BCM)
        
        # Setup Motor A
        GPIO.setup(self.IN1, GPIO.OUT)
        GPIO.setup(self.IN2, GPIO.OUT)
        GPIO.setup(self.ENA, GPIO.OUT)
        
        # Setup Motor B
        GPIO.setup(self.IN3, GPIO.OUT)
        GPIO.setup(self.IN4, GPIO.OUT)
        GPIO.setup(self.ENB, GPIO.OUT)
        
        # Initialize PWM for both motors
        self.pwmA = GPIO.PWM(self.ENA, pwm_freq)
        self.pwmB = GPIO.PWM(self.ENB, pwm_freq)
        self.pwmA.start(0)
        self.pwmB.start(0)

        # Current speed tracking
        self.current_speed_right = 0
        self.current_speed_left = 0

        # Minimum speed threshold
        self.MIN_DUTY_CYCLE = 45

        # Incremental step size for speed adjustment
        self.speed_step = 5

    def map_speed_to_duty_cycle(self, speed):
        """
        Maps the input speed (0-100) to a duty cycle (45-100).
        
        :param speed: Input speed from 0 to 100.
        :return: Mapped duty cycle from 45 to 100.
        """
        # if speed is 0 then duty cycle must be 0, not MIN_DUTY_CYCLE.
        if speed == 0:
            return 0

        # Else return duty cycle from 45 to 100
        return self.MIN_DUTY_CYCLE + (speed * (100 - self.MIN_DUTY_CYCLE) / 100)

    def move(self, set_speed, turn_factor=0):
        """
        Gradually adjust the speed and direction based on set speed and turn factor.
        
        :param set_speed: Target speed for the movement (-100 to +100).
        :param turn_factor: Turn factor from -100 (full left) to +100 (full right).
        """
        # Calculate the base speed step
        base_speed_step = self.speed_step

        # Calculate speed steps for left and right motors based on turn_factor
        if turn_factor >= 0:
            left_speed_step = base_speed_step
            right_speed_step = base_speed_step * (1 - turn_factor / 100)
        else:
            right_speed_step = base_speed_step
            left_speed_step = base_speed_step * (1 + turn_factor / 100)

        # Use absolute value of set_speed for comparison, but maintain its sign for direction
        abs_set_speed = abs(set_speed)

        # Increment current speeds towards the set speed using modified steps
        if self.current_speed_right < abs_set_speed:
            self.current_speed_right = min(self.current_speed_right + right_speed_step, abs_set_speed)
        elif self.current_speed_right > abs_set_speed:
            self.current_speed_right = max(self.current_speed_right - right_speed_step, abs_set_speed)

        if self.current_speed_left < abs_set_speed:
            self.current_speed_left = min(self.current_speed_left + left_speed_step, abs_set_speed)
        elif self.current_speed_left > abs_set_speed:
            self.current_speed_left = max(self.current_speed_left - left_speed_step, abs_set_speed)

        # Set the direction for both motors based on the sign of set_speed
        if set_speed >= 0:  # Forward
            GPIO.output(self.IN1, GPIO.HIGH)
            GPIO.output(self.IN2, GPIO.LOW)
            GPIO.output(self.IN3, GPIO.HIGH)
            GPIO.output(self.IN4, GPIO.LOW)
        else:  # Backward
            GPIO.output(self.IN1, GPIO.LOW)
            GPIO.output(self.IN2, GPIO.HIGH)
            GPIO.output(self.IN3, GPIO.LOW)
            GPIO.output(self.IN4, GPIO.HIGH)

        # Apply mapped speeds to PWM
        self.pwmA.ChangeDutyCycle(self.map_speed_to_duty_cycle(self.current_speed_right))
        self.pwmB.ChangeDutyCycle(self.map_speed_to_duty_cycle(self.current_speed_left))

    def spin(self, set_speed, direction='right'):
        """
        Spin the rover in place.
        
        :param set_speed: Speed for the spin (0-100).
        :param direction: Direction of spin ('right' or 'left').
        """
        base_speed = abs(set_speed)  # Use absolute value of speed for spinning

        if direction == 'right':
            GPIO.output(self.IN1, GPIO.HIGH)
            GPIO.output(self.IN2, GPIO.LOW)
            GPIO.output(self.IN3, GPIO.LOW)
            GPIO.output(self.IN4, GPIO.HIGH)
        elif direction == 'left':
            GPIO.output(self.IN1, GPIO.LOW)
            GPIO.output(self.IN2, GPIO.HIGH)
            GPIO.output(self.IN3, GPIO.HIGH)
            GPIO.output(self.IN4, GPIO.LOW)
        
        self.pwmA.ChangeDutyCycle(self.map_speed_to_duty_cycle(base_speed))
        self.pwmB.ChangeDutyCycle(self.map_speed_to_duty_cycle(base_speed))

    def stop(self):
        # Stop immediately and halt ongoing movement
        GPIO.output(self.IN1, GPIO.LOW)
        GPIO.output(self.IN2, GPIO.LOW)
        GPIO.output(self.IN3, GPIO.LOW)
        GPIO.output(self.IN4, GPIO.LOW)
        self.pwmA.ChangeDutyCycle(0)
        self.pwmB.ChangeDutyCycle(0)
        self.current_speed_right = 0
        self.current_speed_left = 0

    def cleanup(self):
        self.pwmA.stop()
        self.pwmB.stop()
        GPIO.cleanup()

# Test the MotorDriver class
if __name__ == "__main__":
    motor = MotorDriver(in1_pin=24, in2_pin=23, ena_pin=12, in3_pin=22, in4_pin=27, enb_pin=13)
    print("starting motor tests...")
    time.sleep(3)

    set_speed = 40

    try:
        print("Test 1: move forward without turning")
        for _ in range(8):
            motor.move(set_speed)
            time.sleep(0.25)
        motor.stop()
        time.sleep(2)

        print("Test 2: move backward")
        for _ in range(8):
            motor.move(-set_speed)
            time.sleep(0.25)
        motor.stop()
        time.sleep(2)
        
        print("Test 3: move forward with rigth turn")
        for _ in range(8):
            motor.move(set_speed, turn_factor=85)
            time.sleep(0.25)
        motor.stop()
        time.sleep(2)

        print("Test 4: move backward with right turn")
        for _ in range(8):
            motor.move(-set_speed,  turn_factor=85)
            time.sleep(0.25)
        motor.stop()
        time.sleep(2)

        print("Test 5: move forward with left turn")
        for _ in range(8):
            motor.move(set_speed, turn_factor=-85)
            time.sleep(0.25)
        motor.stop()
        time.sleep(2)

        print("Test 6: move backward with left turn")
        for _ in range(8):
            motor.move(-set_speed,  turn_factor=-85)
            time.sleep(0.25)
        motor.stop()
        time.sleep(2)
        
        print("Test 7: spin right")
        motor.spin(20, direction='right')
        time.sleep(2)
        motor.stop()
        time.sleep(2)

        print("Test 7: spin left")
        motor.spin(20, direction='left')
        time.sleep(2)
        motor.stop()
        time.sleep(2)

        print("Finished tests!")
        
    except KeyboardInterrupt:
        pass
    finally:
        motor.cleanup()