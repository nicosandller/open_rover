"""

Example: 
from motor_driver import MotorDriver
motor = MotorDriver(in1_pin=24, in2_pin=23, ena_pin=12, in3_pin=22, in4_pin=27, enb_pin=13)
motor.stop()
motor.move(50, 20) # turn rigth
motor.cleanup()

"""

import time
import RPi.GPIO as GPIO


class MotorDriver:
    def __init__(self, in1_pin, in2_pin, ena_pin, in3_pin, in4_pin, enb_pin):
        """
        Initializes the MotorDriver with the specified GPIO pins for motor control.

        Parameters:
        in1_pin (int): GPIO pin for IN1 of the right motor.
        in2_pin (int): GPIO pin for IN2 of the right motor.
        ena_pin (int): GPIO pin for ENA (enable) of the right motor.
        in3_pin (int): GPIO pin for IN3 of the left motor.
        in4_pin (int): GPIO pin for IN4 of the left motor.
        enb_pin (int): GPIO pin for ENB (enable) of the left motor.
        """
        # Right motor (A)
        self.in1 = in1_pin
        self.in2 = in2_pin
        self.enA = ena_pin

        # Left motor (B)
        self.in3 = in3_pin
        self.in4 = in4_pin
        self.enB = enb_pin

        GPIO.setmode(GPIO.BCM)
        # Setup Motor A and B in a loop
        for pin in [self.in1, self.in2, self.enA, self.in3, self.in4, self.enB]:
            GPIO.setup(pin, GPIO.OUT)

        # Initialize PWM for motor speed control
        self.pwm_right = GPIO.PWM(self.enA, 1000)  # Frequency set to 1kHz
        self.pwm_left = GPIO.PWM(self.enB, 1000)  # Frequency set to 1kHz
        self.pwm_right.start(0)
        self.pwm_left.start(0)

    def _set_motor_direction(self, forward):
        """
        Set the direction for both motors based on the sign of forward.
        """
        if forward > 0:  # Forward
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

        return abs(forward)

    def move(self, forward, rightward):
        """
        Moves the motors based on the forward and rightward values as percentages (-100 to 100).

        Parameters:
        forward (int): The forward movement value. Positive for forward, negative for backward.
        rightward (int): The rightward movement value. Positive for right, negative for left.

        The method calculates the power for both motors to achieve the desired movement.
        """
        # Ensure forward and rightward values are within the range -100 to 100
        forward = max(-100, min(100, forward))
        rightward = max(-100, min(100, rightward))
        is_spinning = False
        print(f"Initial | forward: {forward}, rightward: {rightward}")

        # # Configure the motors to move in one direction based on the sign of forward
        # # The sign of "forward" doesn't matter for right-left calculations.
        # forward_abs = self._set_motor_direction(forward)
        

        # SPIN move: forward has to be within 20. Rightward more thant 20.
        if -20 <= forward <= 20 and (rightward < -20 or rightward > 20):
            is_spinning = True
            left_motor_forward = rightward > 0
            right_motor_forward = not left_motor_forward

            GPIO.output(self.in1, GPIO.HIGH if left_motor_forward else GPIO.LOW)
            GPIO.output(self.in2, GPIO.LOW if left_motor_forward else GPIO.HIGH)
            GPIO.output(self.in3, GPIO.LOW if right_motor_forward else GPIO.HIGH)
            GPIO.output(self.in4, GPIO.HIGH if right_motor_forward else GPIO.LOW)

            left_motor_power = rightward
            right_motor_power = rightward

        if is_spinning:
            # set one motor forward and the other backwards
            print("Spinning right" if left_motor_forward else "Spinning left")

        else:
            # Configure the motors to move in one direction based on the sign of forward
            # The sign of "forward" doesn't matter for right-left calculations.
            forward_abs = self._set_motor_direction(forward)
            if rightward >= 0:
                # Limit rightward to not exceed forward_abs.
                # Set left motor to maximum forward power.
                # Set right motor to maximum forward power minus rightward power.
                rightward = min(forward_abs, rightward)
                left_motor_power = forward_abs
                right_motor_power = forward_abs - (rightward * 0.8)

            elif rightward < 0:
                # Limit rightward to not exceed forward_abs.
                # Set right motor to maximum forward power.
                # Set left motor to maximum forward power plus the negative rightward power.
                rightward = (-1) * min(forward_abs, abs(rightward))
                right_motor_power = forward_abs
                left_motor_power = forward_abs + (rightward * 0.8)

        # Apply the calculated duty cycles to PWM
        self.pwm_right.ChangeDutyCycle(right_motor_power)
        self.pwm_left.ChangeDutyCycle(left_motor_power)
        print(f"Applied | right_motor_power: {right_motor_power}, left_motor_power: {left_motor_power}")

    def stop(self):
        """
        Stops both motors.
        """
        self.pwm_right.ChangeDutyCycle(0)
        self.pwm_left.ChangeDutyCycle(0)

    def cleanup(self):
        """
        Cleanup GPIO and PWM resources.
        """
        self.pwm_right.stop()
        self.pwm_left.stop()
        GPIO.cleanup()


if __name__ == "__main__":
    # GPIO18 shares same PWM channel as GPIO12
    motor = MotorDriver(in1_pin=24, in2_pin=23, ena_pin=12, in3_pin=22, in4_pin=27, enb_pin=18)
    motor.stop()

    print("Test 1: Move forward 50%")
    motor.move(50, 0)  # Move forward at 50% speed
    time.sleep(2)
    motor.stop()
    time.sleep(2)

    print("Test 3: Move back 50%")
    motor.move(-50, 0)  # Move backward at 50% speed
    time.sleep(2)
    motor.stop()
    time.sleep(2)

    print("Test 4: Move forward 50 and rigth 50%")
    motor.move(50, 20)  # Move backward at 50% speed
    time.sleep(2)
    motor.stop()
    time.sleep(2)

    print("Test 5: Move back 50 and left 50%")
    motor.move(50, -20)  # Move backward at 50% speed
    time.sleep(2)
    motor.stop()
    time.sleep(2)
    motor.cleanup()

