from flask import Flask, Response
import subprocess

app = Flask(__name__)

@app.route('/')
def index():
    return Response(stream(), mimetype='multipart/x-mixed-replace; boundary=frame')

def stream():
    # Start the libcamera-vid process to capture video
    process = subprocess.Popen(['libcamera-vid', '--stdout', '-o', '-'],
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    while True:
        frame = process.stdout.read(4096)  # Adjust the buffer size if needed
        if not frame:
            break
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n\r\n')

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)