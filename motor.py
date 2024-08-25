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

        # Current speed and direction tracking
        self.current_speed_a = 0
        self.current_speed_b = 0
        self.current_direction = 'stopped'  # 'forward', 'backward', or 'stopped'

        # Minimum speed threshold
        self.MIN_SPEED = 45

    def ramp_speed(self, pwm_a, pwm_b, current_speed_a, current_speed_b, target_speed_a, target_speed_b, direction, ramp_time=1.0, steps=10):
        """
        Gradually ramps the speed of both motors to their target speeds, considering direction changes.
        
        :param pwm_a: The PWM object for motor A.
        :param pwm_b: The PWM object for motor B.
        :param current_speed_a: The current speed of motor A.
        :param current_speed_b: The current speed of motor B.
        :param target_speed_a: The target speed for motor A.
        :param target_speed_b: The target speed for motor B.
        :param direction: The new direction ('forward' or 'backward').
        :param ramp_time: The total time to reach the target speed.
        :param steps: The number of steps to increase the speed.
        """
        if self.current_direction != direction and self.current_direction != 'stopped':
            # First, ramp down to zero
            steps_to_zero = steps
            step_delay = ramp_time / steps_to_zero
            speed_step_a = -current_speed_a / steps_to_zero
            speed_step_b = -current_speed_b / steps_to_zero
            
            for _ in range(steps_to_zero):
                current_speed_a += speed_step_a
                current_speed_b += speed_step_b
                pwm_a.ChangeDutyCycle(max(self.MIN_SPEED, min(100, current_speed_a)))
                pwm_b.ChangeDutyCycle(max(self.MIN_SPEED, min(100, current_speed_b)))
                time.sleep(step_delay)
            
            self.current_direction = 'stopped'
            current_speed_a = 0
            current_speed_b = 0

        # Now, ramp up to the target speed in the new direction
        steps_to_target = steps
        step_delay = ramp_time / steps_to_target
        speed_step_a = (target_speed_a - current_speed_a) / steps_to_target
        speed_step_b = (target_speed_b - current_speed_b) / steps_to_target
        
        for _ in range(steps_to_target):
            current_speed_a += speed_step_a
            current_speed_b += speed_step_b
            pwm_a.ChangeDutyCycle(max(self.MIN_SPEED, min(100, current_speed_a)))
            pwm_b.ChangeDutyCycle(max(self.MIN_SPEED, min(100, current_speed_b)))
            time.sleep(step_delay)
        
        self.current_direction = direction
        return target_speed_a, target_speed_b

    def forward(self, speed, turn=0):
        speed = max(self.MIN_SPEED, speed)
        turn_adjustment = abs(turn) * (speed - self.MIN_SPEED) / 100
        
        if turn > 0:
            # Turning right: left motor speed is set to the base speed,
            # right motor speed is reduced by the turn adjustment
            left_speed = speed
            right_speed = max(self.MIN_SPEED, speed - turn_adjustment)
        elif turn < 0:
            # Turning left: right motor speed is set to the base speed,
            # left motor speed is reduced by the turn adjustment
            left_speed = max(self.MIN_SPEED, speed - turn_adjustment)
            right_speed = speed
        else:
            left_speed = speed
            right_speed = speed

        GPIO.output(self.IN1, GPIO.HIGH)
        GPIO.output(self.IN2, GPIO.LOW)
        GPIO.output(self.IN3, GPIO.HIGH)
        GPIO.output(self.IN4, GPIO.LOW)
        
        self.current_speed_a, self.current_speed_b = self.ramp_speed(
            self.pwmA, self.pwmB,
            self.current_speed_a, self.current_speed_b,
            left_speed, right_speed,
            'forward'
        )

    def backward(self, speed):
        speed = max(self.MIN_SPEED, speed)
        GPIO.output(self.IN1, GPIO.LOW)
        GPIO.output(self.IN2, GPIO.HIGH)
        GPIO.output(self.IN3, GPIO.LOW)
        GPIO.output(self.IN4, GPIO.HIGH)
        
        self.current_speed_a, self.current_speed_b = self.ramp_speed(
            self.pwmA, self.pwmB,
            self.current_speed_a, self.current_speed_b,
            speed, speed,
            'backward'
        )

    def spin(self, speed, direction='right'):
        speed = max(self.MIN_SPEED, speed)
        # Set the spin direction and speed directly without ramping up
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
        
        self.pwmA.ChangeDutyCycle(speed)
        self.pwmB.ChangeDutyCycle(speed)
        self.current_direction = 'spin'

    def stop(self):
        # Immediate stop
        GPIO.output(self.IN1, GPIO.LOW)
        GPIO.output(self.IN2, GPIO.LOW)
        GPIO.output(self.IN3, GPIO.LOW)
        GPIO.output(self.IN4, GPIO.LOW)
        self.pwmA.ChangeDutyCycle(0)
        self.pwmB.ChangeDutyCycle(0)
        self.current_speed_a = 0
        self.current_speed_b = 0
        self.current_direction = 'stopped'

    def gradual_stop(self, ramp_time=1.0, steps=10):
        # Gradual stop by ramping down to zero
        self.current_speed_a, self.current_speed_b = self.ramp_speed(
            self.pwmA, self.pwmB,
            self.current_speed_a, self.current_speed_b,
            0, 0,
            'stopped',
            ramp_time=ramp_time,
            steps=steps
        )
        GPIO.output(self.IN1, GPIO.LOW)
        GPIO.output(self.IN2, GPIO.LOW)
        GPIO.output(self.IN3, GPIO.LOW)
        GPIO.output(self.IN4, GPIO.LOW)
        self.current_direction = 'stopped'

    def cleanup(self):
        self.pwmA.stop()
        self.pwmB.stop()
        GPIO.cleanup()

# Test the MotorDriver class
if __name__ == "__main__":
    # from motor_handler import MotorDriver
    motor = MotorDriver(in1_pin=24, in2_pin=23, ena_pin=12, in3_pin=22, in4_pin=27, enb_pin=13)
    print("starting motor tests...")
    time.sleep(3)

    set_speed = 55

    try:
        print("Test 1: move forward without turning")
        motor.forward(set_speed)
        time.sleep(2)
        motor.stop()
        time.sleep(2)
        
        print("Test 2: move forward with right turn turning")
        motor.forward(set_speed, turn=50)
        time.sleep(2)
        motor.stop()
        time.sleep(2)
        
        print("Test 3: move forward with left turning")
        motor.forward(set_speed, turn=-50)
        time.sleep(2)
        motor.stop()
        time.sleep(2)

        print("Test 4: move backwards")
        motor.backward(set_speed)
        time.sleep(2)
        motor.stop()
        time.sleep(2)
        
        print("Test 5: spin right")
        motor.spin(set_speed, direction='right')
        time.sleep(2)
        motor.stop()
        time.sleep(2)

        print("Test 6: spin left")
        motor.spin(set_speed, direction='left')
        time.sleep(2)
        motor.stop()
        time.sleep(2)

        print("Test 7: gradual stop.")
        motor.forward(set_speed)
        motor.gradual_stop()
        
        print("Finished tests!")
        
    except KeyboardInterrupt:
        pass
    finally:
        motor.cleanup()