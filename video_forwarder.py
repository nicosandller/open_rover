# First run camera operation here
# libcamera-vid -t 0 --inline --width 1280 --height 720 --framerate 30 --codec h264 -o - | ffmpeg -i - -c:v copy -hls_time 4 -hls_list_size 0 -hls_flags delete_segments -f hls /home/nico/camera_streamer/stream.m3u8
# source venv/bin/activate

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