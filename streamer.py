from flask import Flask, Response
import subprocess

app = Flask(__name__)

def generate_frames():
    # Start the libcamera-vid process to capture video
    process = subprocess.Popen(['libcamera-vid', '--codec', 'mjpeg', '--inline', '-o', '-'],
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    while True:
        # Read MJPEG frame from stdout
        frame = process.stdout.read(1024)
        if not frame:
            break
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/')
def index():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)