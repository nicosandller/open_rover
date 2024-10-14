import RPi.GPIO as GPIO
import time

class MotorDriver:
    """
    DC motor driver with L298N chip using differential drive principles.

    :param wheel_base_width: Distance between wheels in meters.
    :param pwm_freq: PWM frequency in Hz. Default is 1000.
    :param debug: Enable debug output. Default is False.
    """
    def __init__(self, in1_pin, in2_pin, ena_pin, in3_pin, in4_pin, enb_pin, wheel_base_width, min_duty_cycle, v_max, v_min, pwm_freq=1000, debug=False):
        # Motor A (Left)
        self.IN1 = in1_pin
        self.IN2 = in2_pin
        self.ENA = ena_pin
        
        # Motor B (Right)
        self.IN3 = in3_pin
        self.IN4 = in4_pin
        self.ENB = enb_pin

        # Minimum speed threshold
        self.MIN_DUTY_CYCLE = min_duty_cycle  # Minimum duty cycle for effective motor operation
        # Wheelbase width for differential drive calculations transformed to meters
        self.wheel_width = (wheel_base_width / 100)

        # Define max and min velocity for mapping
        self.V_max = v_max  # Maximum linear velocity in m/s
        self.V_min = v_min  # Minimum effective linear velocity in m/s
        self.debug = debug
        
        self._setup_motors(pwm_freq)
        
    def return_v_max(self):
        """Get the maximum linear velocity."""
        return self.V_max

    def return_v_min(self):
        """Get the minimum effective linear velocity."""
        return self.V_min

    def _setup_motors(self, pwm_freq):
        """
        Setup the motors with the specified PWM frequency.
        """
        GPIO.setmode(GPIO.BCM)
        
        # Setup Motor A in a loop
        for pin in [self.IN1, self.IN2, self.ENA]:
            GPIO.setup(pin, GPIO.OUT)
        
        # Setup Motor B in a loop
        for pin in [self.IN3, self.IN4, self.ENB]:
            GPIO.setup(pin, GPIO.OUT)
        
        # Initialize PWM for both motors
        self.pwmA = GPIO.PWM(self.ENA, pwm_freq)
        self.pwmB = GPIO.PWM(self.ENB, pwm_freq)
        self.pwmA.start(0)
        self.pwmB.start(0)
            
    def map_velocity_to_duty_cycle(self, velocity):
        """
        Maps linear velocity to PWM duty cycle.
        
        :param velocity: Desired linear velocity in m/s.
        :return: Mapped duty cycle (45-100).
        """
        # Use absolute value of velocity for mapping
        abs_velocity = abs(velocity)
        
        # Clip absolute velocity to ensure it's within the expected range
        abs_velocity = max(min(abs_velocity, self.V_max), self.V_min)

        # Apply the mapping formula
        duty_cycle = self.MIN_DUTY_CYCLE + ((abs_velocity - self.V_min) / (self.V_max - self.V_min)) * (100 - self.MIN_DUTY_CYCLE)

        return duty_cycle

    def _calculate_wheel_speeds(self, linear_velocity, angular_velocity):
        """
        Calculate wheel speeds based on linear and angular velocity.

        :param linear_velocity: Desired linear velocity of the robot's center in m/s.
        :param angular_velocity: Desired angular velocity of the robot in rad/s.
        :return: Left and right wheel speeds in m/s.
        """
        left_wheel_speed = linear_velocity - (angular_velocity * self.wheel_width / 2)
        right_wheel_speed = linear_velocity + (angular_velocity * self.wheel_width / 2)

        if self.debug:   
            print(f"Left wheel speed: {left_wheel_speed}, Right wheel speed: {right_wheel_speed}")

        return left_wheel_speed, right_wheel_speed

    def _set_motor_direction(self, linear_velocity):
        """
        Set the direction for both motors based on the sign of linear_velocity.
        """
        if linear_velocity >= 0:  # Forward
            GPIO.output(self.IN1, GPIO.HIGH)
            GPIO.output(self.IN2, GPIO.LOW)
            GPIO.output(self.IN3, GPIO.HIGH)
            GPIO.output(self.IN4, GPIO.LOW)
            if self.debug:
                print("Moving forward")
        else:  # Backward
            GPIO.output(self.IN1, GPIO.LOW)
            GPIO.output(self.IN2, GPIO.HIGH)
            GPIO.output(self.IN3, GPIO.LOW)
            GPIO.output(self.IN4, GPIO.HIGH)
            if self.debug:
                print("Moving backward")

    def move(self, linear_velocity, angular_velocity):
        """
        Move the robot based on desired linear and angular velocities.

        Example: 
                A robot with a linear velocity of  1 {m/s}  and an angular velocity of  0.5 {rad/s}.
                - Turning radius  R :

                    R = 1/0.5 = 2

                --> The robot will follow a circular path with a radius of 2 meters. The larger the radius, the gentler the turn. A smaller radius means a sharper turn.

        :param linear_velocity: Desired linear velocity of the robot's center in m/s.
        :param angular_velocity: Desired angular velocity of the robot in rad/s.
        """
        if self.debug:
            print(f"Linear velocity: {linear_velocity}, Angular velocity: {angular_velocity}, Wheel width: {self.wheel_width}")

        # Calculate wheel velocities
        left_wheel_speed, right_wheel_speed = self._calculate_wheel_speeds(linear_velocity, angular_velocity)

        # Map wheel velocities to PWM duty cycles
        duty_cycle_l = self.map_velocity_to_duty_cycle(left_wheel_speed)
        duty_cycle_r = self.map_velocity_to_duty_cycle(right_wheel_speed)
        # Print duty cycles if debug is True
        if self.debug:
            print(f"Left duty cycle: {duty_cycle_l:.2f}, Right duty cycle: {duty_cycle_r:.2f}")
            if duty_cycle_l > duty_cycle_r:
                print("Turning right")
            elif duty_cycle_r > duty_cycle_l:
                print("Turning left")
            else:
                print("Moving straight")    

        # Set motor direction
        self._set_motor_direction(linear_velocity)

        # Apply the calculated duty cycles to PWM
        self.pwmA.ChangeDutyCycle(abs(duty_cycle_r))
        self.pwmB.ChangeDutyCycle(abs(duty_cycle_l))

    def _determine_spin_direction(self, angular_velocity):
        """
        Determine and set the spin direction based on angular velocity.

        When the angular velocity is positive, the spin will be to the left. 
        When the angular velocity is negative, the spin will be to the right.
        
        :param angular_velocity: Desired angular velocity in rad/s.
        :return: Direction string ("left" or "right")
        """
        if angular_velocity >= 0:  # Spin left
            # Set the A motor forward and B motor backward
            GPIO.output(self.IN1, GPIO.HIGH)
            GPIO.output(self.IN2, GPIO.LOW)
            GPIO.output(self.IN3, GPIO.LOW)
            GPIO.output(self.IN4, GPIO.HIGH)

            return "left"
        else:  # Spin right
            # Set the A motor backward and B motor forward
            GPIO.output(self.IN1, GPIO.LOW)
            GPIO.output(self.IN2, GPIO.HIGH)
            GPIO.output(self.IN3, GPIO.HIGH)
            GPIO.output(self.IN4, GPIO.LOW)
            return "right"

    def spin(self, angular_velocity):
        """
        Spin the rover in place based on angular velocity.
        
        :param angular_velocity: Desired angular velocity in rad/s. Positive for left, negative for right.
        """
        if self.debug:
            print(f"Spinning with angular velocity: {angular_velocity}")

        # Determine and set spin direction
        direction = self._determine_spin_direction(angular_velocity)

        if self.debug:
            print(f"Spinning {direction}")

        # calculate the speed of both wheels turning in opposite directions to achieve the angular velocity
        wheel_speed = angular_velocity * self.wheel_width / 2
        # convert to duty cycle    
        duty_cycle = self.map_velocity_to_duty_cycle(wheel_speed)
        
        if self.debug:
            print(f"Wheel speed: {wheel_speed}, Duty cycle: {duty_cycle}")

        # Apply duty cycle to both motors
        self.pwmA.ChangeDutyCycle(duty_cycle)
        self.pwmB.ChangeDutyCycle(duty_cycle)

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

    def cleanup(self):
        """
        Cleanup GPIO and PWM resources.
        """
        self.pwmA.stop()
        self.pwmB.stop()
        GPIO.cleanup()

    def _timed_move(self, linear_velocity, angular_velocity, seconds=0.5):
        """
        Move the robot for a specified duration.
        
        :param linear_velocity: Desired linear velocity of the robot's center in m/s.
        :param angular_velocity: Desired angular velocity of the robot in rad/s.
        :param seconds: Duration of movement in seconds.
        """
        self.move(linear_velocity=linear_velocity, angular_velocity=angular_velocity)
        time.sleep(seconds)
        self.stop()

    def _variable_move(self, velocities, angular_velocities, spacing=0.2):
        """
        Move the robot with variable velocities and angular velocities.
        
        :param velocities: List of linear velocities in m/s.
        :param angular_velocities: List of angular velocities in rad/s.
        :param spacing: Time spacing between each movement in seconds. Default is 0.2 seconds.
        """
        for i in range(len(velocities)):
            self.move(linear_velocity=velocities[i], angular_velocity=angular_velocities[i])
            time.sleep(spacing)
            if self.debug:
                print(f"Moving with velocities: {velocities[i]} and angular velocities: {angular_velocities[i]}")

        self.stop()

if __name__ == "__main__":
    motor = MotorDriver(
        in1_pin=24, 
        in2_pin=23, 
        ena_pin=12, 
        in3_pin=22, 
        in4_pin=27, 
        enb_pin=13, 
        wheel_base_width=22,
        min_duty_cycle=45, 
        v_max=3.14, v_min=0.31, debug=True
    )

    print("starting motor tests...")
    time.sleep(3)

    try:
        print("Test 1: Move forward with no angular velocity")
        motor._timed_move(linear_velocity=1.5, angular_velocity=0, seconds=0.5)
        time.sleep(2)

        print("Test 2: Move backward with no angular velocity")
        motor._timed_move(linear_velocity=-1.5, angular_velocity=0, seconds=0.5)
        time.sleep(2)

        print("Test 3: Move forward with left turn")
        motor._timed_move(linear_velocity=1, angular_velocity=5, seconds=1)
        time.sleep(2)

        print("Test 4: Move backwards back in place turning left")
        motor._timed_move(linear_velocity=-1, angular_velocity=-5, seconds=1)
        time.sleep(2)

        print("Test 5: Move forward with right turn")
        motor._timed_move(linear_velocity=1, angular_velocity=-5, seconds=1)
        time.sleep(2)

        print("Test 6: Move backwards back in place turning right")
        motor._timed_move(linear_velocity=-1, angular_velocity=5, seconds=1)
        time.sleep(2)

        print("Test 7: Spin left")
        motor.spin(angular_velocity=-7)
        time.sleep(2)
        motor.stop()

        print("Test 8: Spin right")
        motor.spin(angular_velocity=7)
        time.sleep(2)
        motor.stop()

        print("Finished tests!")
        
    except KeyboardInterrupt:
        pass
    finally:
        motor.cleanup()

# from motor import MotorDriver
# motor = MotorDriver(in1_pin=24, in2_pin=23, ena_pin=12, in3_pin=22, in4_pin=27, enb_pin=13, wheel_base_width=22,min_duty_cycle=45, v_max=3.14, v_min=0.31, debug=True)
# motor._timed_move(1, 0, 0.5)
# motor._variable_move([1, 2, 5], [1, 2, 5])
# motor.spin(1)
# motor.cleanup()