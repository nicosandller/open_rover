import cv2
import time
import RPi.GPIO as GPIO
from flask_socketio import SocketIO
from flask import Flask, render_template, Response


from motor import MotorDriver
from camera import CameraHandler

class RoverWebServer:
    def __init__(self, motor_driver, camera_handler, led_pin=25, camera_angle_pin=13):
        self.app = Flask(__name__)
        self.socketio = SocketIO(self.app)
        self.camera_handler = camera_handler
        self.motor_driver = motor_driver
        # Default states
        self.stream_on = False
        self.motors_on = True  
        self.lights_on = False 
        self._setup_routes()

        # Servos
        GPIO.setmode(GPIO.BCM)

        # setup rover lights pin as output
        self.led_pin = led_pin
        GPIO.setup(led_pin, GPIO.OUT)

        # Setup camera angle control servo GPIO 13
        GPIO.setup(camera_angle_pin, GPIO.OUT)
        self.pwm_camera_angle = GPIO.PWM(camera_angle_pin, 50)  # Frequency set to 50Hz
        self.pwm_camera_angle.start(0)

    def _setup_routes(self):
        @self.app.route('/')
        def index():
            return render_template('index.html')

        @self.app.route('/video_feed')
        def video_feed():
            if self.stream_on:
                return Response(self.generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')
            else:
                return Response(status=204)  # No Content

        @self.socketio.on('joystick_move')
        def handle_joystick_move(data):
            coordinates = data.get('coordinates', (0, 0))
            forward, rightward = coordinates
            # if either of the coordinates is less than 15% then set it to zero
            forward = 0 if (-20 <= forward <= 20) else forward
            rightward = 0 if (-15 <= rightward <= 15) else rightward
        
            print(f"JOYSTICK: forward {forward}%, rightward {rightward}%")
    
            if self.motors_on:
                if (forward==0) & (rightward==0):
                    self.motor_driver.stop()
                else:
                    self.motor_driver.move(forward, rightward)

        @self.socketio.on('connect')
        def handle_connect():
            # Emit the current stream state to the client upon connection or refresh
            self.socketio.emit('stream_state', {'status': self.stream_on})
            self.socketio.emit('motors_state', {'status': self.motors_on})
            self.socketio.emit('light_state', {'status': self.lights_on})

        @self.socketio.on('toggle_stream')
        def handle_toggle_stream(data):
            # handles streaming toggle slider button
            self.stream_on = data.get('status', False)
            print(f"Stream toggled: {'On' if self.stream_on else 'Off'}")
            # Emit the updated stream state to all clients
            self.socketio.emit('stream_state', {'status': self.stream_on})

        @self.socketio.on('toggle_motors')
        def handle_toggle_motors(data):
            # handles motor toggle slider button
            self.motors_on = data.get('status', False)
            print(f"Motors toggled: {'On' if self.motors_on else 'Off'}")
            # Emit the updated stream state to all clients
            self.socketio.emit('motors_state', {'status': self.motors_on})

        @self.socketio.on('toggle_lights')
        def handle_toggle_lights(data):
            # handles light toggle slider button
            self.lights_on = data.get('status', False)
            print(f"Light toggled: {'On' if self.lights_on else 'Off'}")
            # Emit the updated stream state to all clients
            self.socketio.emit('light_state', {'status': self.lights_on})
            
            # Change the pin state
            if self.lights_on:
                GPIO.output(self.led_pin, GPIO.HIGH)
            else:
                GPIO.output(self.led_pin, GPIO.LOW)

        @self.socketio.on('camera_tilt')
        def handle_camera_tilt(data):
            # 0 is camera safe position | 90 is front view  | 180 is ceiling view |  240 is back view
            # Get the tilt angle from data
            tilt_angle = data.get('angle', 90)  # Default to 90 if not provided

            # Ensure the angle is within the valid range (0 to 240)
            tilt_angle = max(0, min(240, tilt_angle))

            # Apply the angle to the servo control pin
            # Assuming self.servo_pwm is a PWM instance controlling the servo
            duty_cycle = (tilt_angle / 36) + 2 # converting angle to duty cycle
            self.pwm_camera_angle.ChangeDutyCycle(duty_cycle)
            print(f"Camera tilt set to {tilt_angle} degrees")

    def generate_frames(self):
        while True:
            frame = self.camera_handler.get_still()
            if frame is not None:
                # Re-encode the modified image back to JPEG format
                _, jpeg_frame = cv2.imencode('.jpg', frame)
                modified_jpeg_frame = jpeg_frame.tobytes()
                yield (b'--frame\r\n'
                    b'Content-Type: image/jpeg\r\n\r\n' + modified_jpeg_frame + b'\r\n')
            else:
                print("Warning: No frame received from camera handler.")
                time.sleep(0.1)  # Prevent a tight loop if no frames are received

    def start(self):
        self.socketio.run(self.app, host='0.0.0.0', port=5001, allow_unsafe_werkzeug=True)


if __name__ == "__main__":
    # TODO: change enb_pin to GPIO18 (shares same PWM channel as GPIO12) - This is the left motor
    motor_driver = MotorDriver(in1_pin=24, in2_pin=23, ena_pin=12, in3_pin=22, in4_pin=27, enb_pin=18)
    camera_driver = CameraHandler(width=960, height=540, fps=30)

    web_server = RoverWebServer(motor_driver, camera_driver, 25)

    print("Initializing system...")
    # TODO: Add any necessary initialization logic here
    time.sleep(2)

    print("Initialization complete. Starting webserver...")
    # Start the web server in a separate process
    # web_server_process = multiprocessing.Process(target=self.web_server.start)
    # web_server_process.start()
    web_server.start()
    print("Web server started. Access the rover's control interface via the web browser on http://raspberrypi.local:5001")