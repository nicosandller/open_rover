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
        # Motor A (right)
        self.in1 = in1_pin
        self.in2 = in2_pin
        self.enA = ena_pin
        
        # Motor B (Left)
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

    def _set_motor_direction(self, forward_percentage):
        """
        Set the direction for both motors based on the sign of forward_percentage.
        """
        if forward_percentage > 0:  # Forward
            GPIO.output(self.in1, GPIO.HIGH)
            GPIO.output(self.in2, GPIO.LOW)
            GPIO.output(self.in3, GPIO.HIGH)
            GPIO.output(self.in4, GPIO.LOW)
            print("Moving forward")
        else:  # Backward
            GPIO.output(self.in1, GPIO.LOW)
            GPIO.output(self.in2, GPIO.HIGH)
            GPIO.output(self.in3, GPIO.LOW)
            GPIO.output(self.in4, GPIO.HIGH)
            print("Moving backward")

        return abs(forward_percentage)

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

    def move(self, forward_percentage, right_percentage):
        """
        Moves the rover based on forward and right values.
        
        Parameters:
        forward (int): Forward movement value (-100 to 100). Negative values mean backward movement.
        right (int): Right movement value (-1 to 1). Negative values mean left movement.
        
        The method calculates the speed and direction for both motors to achieve the desired movement.
        
        Example:
        If forward=50 and right=0.5:
        - The rover should move forward at 50% speed, with a 50% differential.
        """
        # Ensure inputs are within range. This is just for safety.
        forward_percentage = max(-100, min(100, forward_percentage))
        right_percentage = max(-1, min(1, right_percentage))

        print(f"Raw | forward motor speed percentage: {forward_percentage}, right percentage: {right_percentage}")

        forward_percentage = self._set_motor_direction(forward_percentage)

        # if right_percentage positive and forward positive then turn right Same backwards (forward negative)
        if right_percentage >= 0: 
            right_motor_speed = forward_percentage - (forward_percentage * right_percentage)
            left_motor_speed = forward_percentage + (forward_percentage * right_percentage)
        else:
            left_motor_speed = forward_percentage - (forward_percentage * right_percentage)
            right_motor_speed = forward_percentage + (forward_percentage * right_percentage)

        print(f"Adjusted | left motor speed: {left_motor_speed}, right motor speed: {right_motor_speed}")

        # Remap speeds to ensure they meet the minimum duty cycle requirements
        left_motor_speed = self.remap_speed(left_motor_speed)
        right_motor_speed = self.remap_speed(right_motor_speed)

        # Print normalized values for debugging
        print(f"Remapped | left motor speed: {left_motor_speed}, right motor speed: {right_motor_speed}")

        # Apply the calculated duty cycles to PWM
        self.pwmB.ChangeDutyCycle(left_motor_speed)
        self.pwmA.ChangeDutyCycle(right_motor_speed)

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
    # from motor import MotorDriver
    motor = MotorDriver(in1_pin=24, in2_pin=23, ena_pin=12, in3_pin=22, in4_pin=27, enb_pin=13)
    motor.stop()

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