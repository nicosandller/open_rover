from flask import Flask, Response
import subprocess

app = Flask(__name__)

def generate_frames():
    process = subprocess.Popen(['libcamera-vid', '--codec', 'mjpeg', '--inline', '-o', '-'],
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    # Initialize buffer
    buffer = b''

    while True:
        # Read a chunk from the subprocess stdout
        chunk = process.stdout.read(1024)
        if not chunk:
            break
        buffer += chunk

        # Find the end of a frame (FF D9)
        end = buffer.find(b'\xff\xd9')

        if end != -1:
            # Extract the complete frame
            frame = buffer[:end+2]
            buffer = buffer[end+2:]

            # Yield the frame with the necessary headers
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

        # Reset buffer if it gets too large without finding a frame
        if len(buffer) > 1_000_000:  # Arbitrary size limit
            buffer = b''

@app.route('/')
def index():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)