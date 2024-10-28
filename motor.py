import RPi.GPIO as GPIO
import time

class MotorDriver:
    def __init__(self, in1_pin, in2_pin, ena_pin, in3_pin, in4_pin, enb_pin, min_duty_cycle=45, max_duty_cycle=90):
        """
        DC motor driver with L298N chip using differential drive.
        
        Parameters:
        enA (int): PWM pin for Motor A speed control.
        in1 (int): Control pin 1 for Motor A direction.
        in2 (int): Control pin 2 for Motor A direction.
        enB (int): PWM pin for Motor B speed control.
        in3 (int): Control pin 1 for Motor B direction.
        in4 (int): Control pin 2 for Motor B direction.
        min_duty_cycle (int): Minimum duty cycle for effective motor operation.
        
        Note:
        - The duty cycle (0-100) controls the motor speed, where 0 is stop and 100 is full speed.
        - The input voltage of the battery affects the overall motor performance. Ensure the voltage is compatible with the motor specifications.
        """
        # Motor A (Left)
        self.in1 = in1_pin
        self.in2 = in2_pin
        self.enA = ena_pin
        
        # Motor B (Right)
        self.in3 = in3_pin
        self.in4 = in4_pin
        self.enB = enb_pin

        # Minimum / Maximum duty cycle for effective motor operation
        self.MIN_DUTY_CYCLE = min_duty_cycle  
        self.MAX_DUTY_CYCLE = max_duty_cycle
        
        GPIO.setmode(GPIO.BCM)
        # Setup Motor A and B in a loop
        for pin in [self.in1, self.in2, self.enA, self.in3, self.in4, self.enB]:
            GPIO.setup(pin, GPIO.OUT)

        # Initialize PWM for motor speed control
        self.pwmA = GPIO.PWM(self.enA, 1000)  # Frequency set to 1kHz
        self.pwmB = GPIO.PWM(self.enB, 1000)  # Frequency set to 1kHz
        self.pwmA.start(0)
        self.pwmB.start(0)

    def remap_speed(self, speed):
        """
        Remaps the speed value to be within the range of min_duty_cycle to 100.
        
        Parameters:
        speed (int): Original speed value (0-100).
        
        Returns:
        int: Remapped speed value within the range of min_duty_cycle to 100.
        """
        if speed == 0:
            return 0
        return min(int(self.MIN_DUTY_CYCLE + (speed / 100) * (100 - self.MIN_DUTY_CYCLE)), self.MAX_DUTY_CYCLE)

    def move(self, forward, right):
        """
        Moves the rover based on forward and right values.
        
        Parameters:
        forward (int): Forward movement value (-100 to 100). Negative values mean backward movement.
        right (int): Right movement value (-100 to 100). Negative values mean left movement.
        
        The method calculates the speed and direction for both motors to achieve the desired movement.
        
        Example:
        If forward=50 and right=25:
        - The rover should move forward, with a slight right turn.
        """
        # Ensure inputs are within range. This is just for safety.
        forward = max(-100, min(100, forward))
        right = max(-100, min(100, right))

        # Calculate motor speeds based on forward and right values
        # Forward contributes equally to both motors, while right/left adjusts the relative speed
        left_motor_speed = forward + right
        right_motor_speed = forward - right

        # Print intermediate values for debugging
        print(f"Raw left motor speed: {left_motor_speed}, Raw right motor speed: {right_motor_speed}")

        # Normalize motor speeds to be within 0 to 100
        max_speed = max(abs(left_motor_speed), abs(right_motor_speed), 100)
        left_motor_speed = int((left_motor_speed / max_speed) * 100)
        right_motor_speed = int((right_motor_speed / max_speed) * 100)

        # Remap speeds to ensure they meet the minimum duty cycle requirements
        left_motor_speed = self.remap_speed(left_motor_speed)
        right_motor_speed = self.remap_speed(right_motor_speed)

        # Print normalized values for debugging
        print(f"Remapped left motor speed: {left_motor_speed}, Remapped right motor speed: {right_motor_speed}")

        # Set directions and speeds for both motors
        if left_motor_speed >= 0:
            self.set_motor_a(left_motor_speed, 1)
        else:
            self.set_motor_a(abs(left_motor_speed), 0)

        if right_motor_speed >= 0:
            self.set_motor_b(right_motor_speed, 1)
        else:
            self.set_motor_b(abs(right_motor_speed), 0)

    def set_motor_a(self, speed, direction):
        """
        Sets Motor A speed and direction.
        
        Parameters:
        speed (int): Speed of the motor (0-100, as duty cycle percentage).
        direction (int): Direction of the motor (1 for forward, 0 for backward).
        """
        GPIO.output(self.in1, GPIO.HIGH if direction == 1 else GPIO.LOW)
        GPIO.output(self.in2, GPIO.LOW if direction == 1 else GPIO.HIGH)
        self.pwmA.ChangeDutyCycle(speed)

    def set_motor_b(self, speed, direction):
        """
        Sets Motor B speed and direction.
        
        Parameters:
        speed (int): Speed of the motor (0-100, as duty cycle percentage).
        direction (int): Direction of the motor (1 for forward, 0 for backward).
        """
        GPIO.output(self.in3, GPIO.HIGH if direction == 1 else GPIO.LOW)
        GPIO.output(self.in4, GPIO.LOW if direction == 1 else GPIO.HIGH)
        self.pwmB.ChangeDutyCycle(speed)

    def stop(self):
        """
        Stops both motors.
        """
        # GPIO.output(self.IN1, GPIO.LOW)
        # GPIO.output(self.IN2, GPIO.LOW)
        # GPIO.output(self.IN3, GPIO.LOW)# Minimum / Maximum duty cycle for effective motor operation
        # GPIO.output(self.IN4, GPIO.LOW)
        self.pwmA.ChangeDutyCycle(0)
        self.pwmB.ChangeDutyCycle(0)

    def cleanup(self):
        """
        Cleanup GPIO and PWM resources.
        """
        self.pwmA.stop()
        self.pwmB.stop()
        GPIO.cleanup()

if __name__ == "__main__":
    motor = MotorDriver(in1_pin=24, in2_pin=23, ena_pin=12, in3_pin=22, in4_pin=27, enb_pin=13)

    print("Test 1: Move forward 50%")
    motor.move(50, 0)  # Move forward at 50% speed
    time.sleep(2)
    motor.stop()
    time.sleep(2)

    print("Test 2: Move right 50%")
    motor.move(0, 50)  # Turn right at 50% speed
    time.sleep(2)
    motor.stop()
    time.sleep(2)

    print("Test 3: Move back 50%")
    motor.move(-50, 0)  # Move backward at 50% speed
    time.sleep(2)
    motor.stop()
    time.sleep(2)

    print("Test 4: Move forward 50 and rigth 50%")
    motor.move(50, 50)  # Move backward at 50% speed
    time.sleep(2)
    motor.stop()
    time.sleep(2)

    print("Test 5: Move back 50 and left 50%")
    motor.move(50, -50)  # Move backward at 50% speed
    time.sleep(2)
    motor.stop()
    time.sleep(2)
    motor.cleanup()