from flask import Flask, render_template, send_from_directory

app = Flask(__name__)
HLS_DIR = "/home/nico/camera_streamer"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/hls/<path:filename>')
def hls(filename):
    return send_from_directory(HLS_DIR, filename)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)