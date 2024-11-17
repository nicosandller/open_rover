import cv2
import time
from flask import Flask, render_template, Response
from flask_socketio import SocketIO

class RoverWebServer:
    def __init__(self, motor_driver, camera_handler):
        self.app = Flask(__name__)
        self.socketio = SocketIO(self.app)
        self.camera_handler = camera_handler
        self.motor_driver = motor_driver
        self.stream_on = False  # Default stream state is off
        self.motors_on = True   # Default stream state is on
        self._setup_routes()

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
            forward = 0 if -20 <= forward <= 20 else forward
            rightward = 0 if -15 <= rightward <= 15 else rightward
        
            print(f"JOYSTICK: forward {forward}%, rightward {rightward}%")
    
            if self.motors_on:
                if (forward==0):
                    self.motor_driver.stop()
                else:
                    self.motor_driver.move(forward, rightward)

        @self.socketio.on('connect')
        def handle_connect():
            # Emit the current stream state to the client upon connection or refresh
            self.socketio.emit('stream_state', {'status': self.stream_on})
            self.socketio.emit('motors_state', {'status': self.motors_on})

        @self.socketio.on('toggle_stream')
        def handle_toggle_stream(data):
            # handles streaming toggle slider button
            self.stream_on = data.get('status', False)
            print(f"Stream toggled: {'On' if self.stream_on else 'Off'}")
            # Emit the updated stream state to all clients
            self.socketio.emit('stream_state', {'status': self.stream_on})

        @self.socketio.on('toggle_motors')
        def handle_toggle_explorer(data):
            # handles explorer mode toggle slider button
            self.motors_on = data.get('status', False)
            print(f"Motors toggled: {'On' if self.motors_on else 'Off'}")
            # Emit the updated stream state to all clients
            self.socketio.emit('motors_state', {'status': self.motors_on})

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
