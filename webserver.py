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
            forward_backwards, left_rigth = coordinates
            print(f"Joystick moved: forwards / backwards {forward_backwards}%, left / right {left_rigth}%")
            # handle the joystick movement based on the coordinates
            v_max = self.motor_driver.V_max
            v_min = self.motor_driver.V_min
            forward_velocity = (forward_backwards / 100) * v_max
            if 0 < forward_velocity < v_min:
                forward_velocity = v_min
            elif 0 > forward_velocity > -v_min:
                forward_velocity = -v_min
            angular_velocity = (left_rigth / 100) * 5  
            self.motor_driver.move(forward_velocity, angular_velocity)

        @self.socketio.on('toggle_explorer')
        def handle_toggle_explorer(data):
            status = data.get('status', False)
            print(f"Explorer mode toggled: {'On' if status else 'Off'}")
            # Add logic to enable/disable explorer mode

        @self.socketio.on('connect')
        def handle_connect():
            # Emit the current stream state to the client upon connection
            self.socketio.emit('stream_state', {'status': self.stream_on})

        @self.socketio.on('toggle_stream')
        def handle_toggle_stream(data):
            self.stream_on = data.get('status', False)
            print(f"Stream toggled: {'On' if self.stream_on else 'Off'}")
            # Emit the updated stream state to all clients
            self.socketio.emit('stream_state', {'status': self.stream_on})
            # Add logic to start/stop the live stream if needed

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

# The following code is for standalone execution and can be removed if not needed
if __name__ == '__main__':
    from camera import CameraHandler
    camera = CameraHandler(width=960, height=540, fps=30)
    server = RoverWebServer(None, camera)
    server.start()