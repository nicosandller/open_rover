"""

Example: 
from motor_driver import MotorDriver
motor = MotorDriver(in1_pin=24, in2_pin=23, ena_pin=12, in3_pin=22, in4_pin=27, enb_pin=13)

"""

import time
import RPi.GPIO as GPIO


class MotorDriver:
    def __init__(self, in1_pin, in2_pin, ena_pin, in3_pin, in4_pin, enb_pin):
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
        # depending on the sign configure the motors to move in one direction
        # the sign of "forward" doesn't matter for right left calculations.
        forward_abs = self._set_motor_direction(forward)
        print(f"Initial | forward: {forward}, rightward: {rightward}, forward_abs: {forward_abs}")

        # if turning right
        if rightward >= 0:
            # limit rightward to not be > forward_abs
            rightward = min(forward_abs, rightward)
            # set left motor to max set forward power
            left_motor_power = forward_abs
            # set right motor to max set forward power - rightward power
            right_motor_power = forward_abs - rightward

        # if turning left
        if rightward < 0:
            # limit rightward to not be > forward_abs
            rightward = (-1) * min(forward_abs, abs(rightward))
            # set right motor to max set forward power
            right_motor_power = forward_abs
            # set left motor to max set forward power + (-) rightward power
            left_motor_power = forward_abs + rightward

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

