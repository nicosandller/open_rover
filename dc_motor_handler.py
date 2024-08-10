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

    def forward(self, speed, turn=0):
        """
        Moves forward with optional turning.
        
        :param speed: The base speed for both motors.
        :param turn: Positive values turn right, negative values turn left.
                     Range from -100 to 100. 0 means no turning.
        """
        if turn > 0:
            # Turning right: reduce speed on the right motor
            left_speed = speed
            right_speed = max(0, speed - (speed * turn / 100))
        elif turn < 0:
            # Turning left: reduce speed on the left motor
            left_speed = max(0, speed + (speed * turn / 100))
            right_speed = speed
        else:
            # No turning, both motors same speed
            left_speed = speed
            right_speed = speed

        GPIO.output(self.IN1, GPIO.HIGH)
        GPIO.output(self.IN2, GPIO.LOW)
        GPIO.output(self.IN3, GPIO.HIGH)
        GPIO.output(self.IN4, GPIO.LOW)
        
        self.pwmA.ChangeDutyCycle(left_speed)
        self.pwmB.ChangeDutyCycle(right_speed)

    def backward(self, speed):
        GPIO.output(self.IN1, GPIO.LOW)
        GPIO.output(self.IN2, GPIO.HIGH)
        GPIO.output(self.IN3, GPIO.LOW)
        GPIO.output(self.IN4, GPIO.HIGH)
        self.pwmA.ChangeDutyCycle(speed)
        self.pwmB.ChangeDutyCycle(speed)

    def stop(self):
        GPIO.output(self.IN1, GPIO.LOW)
        GPIO.output(self.IN2, GPIO.LOW)
        GPIO.output(self.IN3, GPIO.LOW)
        GPIO.output(self.IN4, GPIO.LOW)
        self.pwmA.ChangeDutyCycle(0)
        self.pwmB.ChangeDutyCycle(0)

    def cleanup(self):
        self.pwmA.stop()
        self.pwmB.stop()
        GPIO.cleanup()

# Test the MotorDriver class
if __name__ == "__main__":
    try:
        motor = MotorDriver(in1_pin=23, in2_pin=24, ena_pin=12, in3_pin=27, in4_pin=22, enb_pin=13)
        
        # Move forward without turning
        motor.forward(75)
        time.sleep(3)
        
        # Move forward with a right turn
        motor.forward(75, turn=50)  # Turn right moderately
        time.sleep(3)
        
        # Move forward with a left turn
        motor.forward(75, turn=-50)  # Turn left moderately
        time.sleep(3)
        
        motor.stop()
        time.sleep(2)
        
    except KeyboardInterrupt:
        pass
    finally:
        motor.cleanup()