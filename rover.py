"""
This module serves as the entry point for the rover, activated upon power-up.

The module first executes an initialization routine and performs system tests.

Subsequently, it initializes a web server with the following features:
    - A live stream video feed from the camera, which is off by default and can be toggled on or off via a button.
    - Joystick controls for rover navigation, with a button to enable or disable human control.
    - Display of rover state metrics, such as battery percentage.
    - A button to toggle "explorer mode" on or off.

Explorer mode allows the rover to autonomously navigate and search for cats within a household environment.
    - Vision navigation is facilitated by API calls that provide information based on images captured every second.
    - The API returns precise navigation instructions for the rover.
    - These instructions are also displayed on the web interface via a navigation log.
"""

import time
from camera import CameraHandler
from motor import MotorDriver
import multiprocessing
# import requests
from webserver import RoverWebServer
import multiprocessing

class RoverController:
    def __init__(self, motor_driver, camera_handler):
        self.motor = motor_driver
        self.camera = camera_handler

        self.web_server = RoverWebServer(motor_driver, camera_handler)

    def initialize_system(self):
        # Run initialization routine and tests
        print("Initializing system...")
        # TODO: Add any necessary initialization logic here
        time.sleep(2)
        print("Initialization complete.")
        print("Starting webserver...")
        # Start the web server in a separate process
        # web_server_process = multiprocessing.Process(target=self.web_server.start)
        # web_server_process.start()
        self.web_server.start()
        print("Web server started. Access the rover's control interface via the web browser on http://raspberrypi.local:5001")

    def run(self):
        self.initialize_system()


if __name__ == "__main__":
    motor = MotorDriver(in1_pin=24, in2_pin=23, ena_pin=12, in3_pin=22, in4_pin=27, enb_pin=13, wheel_base_width=22, min_duty_cycle=45, v_max=3.14, v_min=0.31, debug=True)
    camera = CameraHandler(width=960, height=540, fps=30)
    rover = RoverController(motor, camera)
    rover.run()