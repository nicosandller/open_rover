from flask import Flask, Response
import subprocess

app = Flask(__name__)

def generate_frames():
    process = subprocess.Popen(['libcamera-vid', '--codec', 'mjpeg', '--inline', '-o', '-', '-t', '0'],
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    buffer = b''

    try:
        while True:
            chunk = process.stdout.read(1024)
            if not chunk:
                print("No more data from libcamera-vid, breaking loop.")
                print(process.stderr.read().decode('utf-8'))  # Print stderr output
                break
            buffer += chunk
            end = buffer.find(b'\xff\xd9')

            if end != -1:
                frame = buffer[:end+2]
                buffer = buffer[end+2:]
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

            if len(buffer) > 1_000_000:  # Reset if buffer gets too large
                print("Buffer size exceeded limit, resetting buffer.")
                buffer = b''
    except Exception as e:
        print(f"Error while generating frames: {e}")
    finally:
        process.stdout.close()
        process.stderr.close()
        process.terminate()
        print("Subprocess terminated.")


@app.route('/')
def index():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)