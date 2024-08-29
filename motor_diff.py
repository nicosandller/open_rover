import RPi.GPIO as GPIO
import time

class MotorDriver:
    """
    DC motor driver with L298N chip using differential drive principles.


    :param wheel_base_width: distance from wheel to wheel in centimeters).
    """
    def __init__(self, in1_pin, in2_pin, ena_pin, in3_pin, in4_pin, enb_pin, wheel_base_width, pwm_freq=1000):
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
        self.MIN_DUTY_CYCLE = 45  # Minimum duty cycle for effective motor operation

        # Wheelbase width for differential drive calculations transformed to meters
        self.wheel_width = (wheel_base_width / 100)

        # Define max and min velocity for mapping
        self.V_max = 3.14  # Maximum linear velocity in m/s
        self.V_min = 0.31  # Minimum effective linear velocity in m/s

    def map_velocity_to_duty_cycle(self, velocity):
        """
        Maps the linear velocity to a PWM duty cycle.
        
        :param velocity: Desired linear velocity of the robot (in m/s).
        :return: Mapped duty cycle (45-100).
        """
        # Clip velocity to ensure it's within the expected range
        velocity = max(min(velocity, self.V_max), self.V_min)

        # Apply the mapping formula
        duty_cycle = self.MIN_DUTY_CYCLE + ((velocity - self.V_min) / (self.V_max - self.V_min)) * (100 - self.MIN_DUTY_CYCLE)
        return duty_cycle

    def move(self, linear_velocity, angular_velocity):
        """
        Move the robot based on desired linear and angular velocities using differential drive.

        Example: 
        A robot with a linear velocity of  1 {m/s}  and an angular velocity of  0.5 {rad/s}.
        - Turning radius  R :

            R = 1/0.5 = 2

        --> The robot will follow a circular path with a radius of 2 meters. The larger the radius, the gentler the turn. A smaller radius means a sharper turn.
        
        :param linear_velocity: Desired linear velocity of the robot's center (in m/s).
        :param angular_velocity: Desired angular velocity of the robot (rad/s).
        """
        # Calculate wheel velocities based on linear and angular velocity
        left_wheel_speed = linear_velocity - (angular_velocity * self.wheel_width / 2)
        right_wheel_speed = linear_velocity + (angular_velocity * self.wheel_width / 2)

        # Map wheel velocities to PWM duty cycles
        duty_cycle_l = self.map_velocity_to_duty_cycle(left_wheel_speed)
        duty_cycle_r = self.map_velocity_to_duty_cycle(right_wheel_speed)

        # Set motor direction based on the sign of the velocities
        if left_wheel_speed >= 0:
            GPIO.output(self.IN1, GPIO.HIGH)
            GPIO.output(self.IN2, GPIO.LOW)
        else:
            GPIO.output(self.IN1, GPIO.LOW)
            GPIO.output(self.IN2, GPIO.HIGH)

        if right_wheel_speed >= 0:
            GPIO.output(self.IN3, GPIO.HIGH)
            GPIO.output(self.IN4, GPIO.LOW)
        else:
            GPIO.output(self.IN3, GPIO.LOW)
            GPIO.output(self.IN4, GPIO.HIGH)

        # Apply the calculated duty cycles to PWM
        self.pwmA.ChangeDutyCycle(abs(duty_cycle_l))
        self.pwmB.ChangeDutyCycle(abs(duty_cycle_r))

    def spin(self, angular_velocity):
        """
        Spin the rover in place based on angular velocity.
        
        :param angular_velocity: Desired angular velocity (-100 to +100).
        """
        base_speed = abs(angular_velocity)  # Use absolute value of angular velocity for spinning

        if angular_velocity >= 0:  # Spin left
            GPIO.output(self.IN1, GPIO.LOW)
            GPIO.output(self.IN2, GPIO.HIGH)
            GPIO.output(self.IN3, GPIO.HIGH)
            GPIO.output(self.IN4, GPIO.LOW)
        else:  # Spin right
            GPIO.output(self.IN1, GPIO.HIGH)
            GPIO.output(self.IN2, GPIO.LOW)
            GPIO.output(self.IN3, GPIO.LOW)
            GPIO.output(self.IN4, GPIO.HIGH)
        
        self.pwmA.ChangeDutyCycle(self.map_velocity_to_duty_cycle(base_speed))
        self.pwmB.ChangeDutyCycle(self.map_velocity_to_duty_cycle(base_speed))

    def stop(self):
        """
        Stop the robot immediately.
        """
        GPIO.output(self.IN1, GPIO.LOW)
        GPIO.output(self.IN2, GPIO.LOW)
        GPIO.output(self.IN3, GPIO.LOW)
        GPIO.output(self.IN4, GPIO.LOW)
        self.pwmA.ChangeDutyCycle(0)
        self.pwmB.ChangeDutyCycle(0)
        self.current_speed_right = 0
        self.current_speed_left = 0

    def cleanup(self):
        """
        Cleanup GPIO and PWM resources.
        """
        self.pwmA.stop()
        self.pwmB.stop()
        GPIO.cleanup()

    def _timed_move(self, linear_velocity, angular_velocity, time):
        print("Test 2: Move forward with left turn")
        self.move(linear_velocity=linear_velocity, angular_velocity=angular_velocity)
        time.sleep(time)
        self.stop()

# Test the MotorDriver class
if __name__ == "__main__":
    motor = MotorDriver(in1_pin=24, in2_pin=23, ena_pin=12, in3_pin=22, in4_pin=27, enb_pin=13, wheel_base_width=0.5)
    print("starting motor tests...")
    time.sleep(3)

    try:
        print("Test 1: Move forward with no angular velocity")
        motor.move(linear_velocity=1.5, angular_velocity=0)
        time.sleep(3)
        motor.stop()
        time.sleep(2)

        print("Test 2: Move forward with left turn")
        motor.move(linear_velocity=1.5, angular_velocity=3.0)
        time.sleep(3)
        motor.stop()
        time.sleep(2)

        print("Test 3: Move forward with right turn")
        motor.move(linear_velocity=1.5, angular_velocity=-1.0)
        time.sleep(3)
        motor.stop()
        time.sleep(2)

        print("Test 4: Spin in place left")
        motor.spin(angular_velocity=1.0)
        time.sleep(2)
        motor.stop()
        time.sleep(2)

        print("Test 5: Spin in place right")
        motor.spin(angular_velocity=-1.0)
        time.sleep(2)
        motor.stop()
        time.sleep(2)

        print("Finished tests!")
        
    except KeyboardInterrupt:
        pass
    finally:
        motor.cleanup()