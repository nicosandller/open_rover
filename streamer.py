from flask import Flask, Response
import subprocess
import cv2
import numpy as np
from edge_impulse_linux.runner import ImpulseRunner
import sys
import multiprocessing
import queue

app = Flask(__name__)

width = '960'
height = '540'

# Get the model path from the command-line argument
if len(sys.argv) < 2:
    print("Usage: python streamer.py <MODEL_PATH>")
    sys.exit(1)

MODEL_PATH = sys.argv[1]

# Function to initialize and run classification in a separate process
def classify_worker(input_queue, output_queue, model_path):
    runner = ImpulseRunner(model_path)
    runner.init()
    while True:
        try:
            frame_number, image = input_queue.get()
            if frame_number is None:  # Sentinel value to end the process
                break

            # Convert image to RGB and resize for the model
            resized = cv2.resize(image, (320, 320))
            rgb_frame = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
            features = np.expand_dims(rgb_frame.astype(np.float32), axis=0)
            features_list = features.tolist()

            # Run inference
            result = runner.classify(features_list)
            output_queue.put((frame_number, result))
        except Exception as e:
            print(f"Error during classification: {e}")
            output_queue.put((frame_number, None))

# Queues for communication between processes
input_queue = multiprocessing.Queue(maxsize=10)
output_queue = multiprocessing.Queue(maxsize=10)

# Start classification process
classification_process = multiprocessing.Process(target=classify_worker, args=(input_queue, output_queue, MODEL_PATH))
classification_process.start()

def generate_frames():
    process = subprocess.Popen(['libcamera-vid', '--codec', 'mjpeg', '--inline', '-o', '-', '-t', '0', '--width', width, '--height', height],
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    buffer = b''

    frame_count = 0
    skip_classification = 10  # Number of frames to skip classification

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

                # Convert frame to numpy array for processing
                image = cv2.imdecode(np.frombuffer(frame, np.uint8), cv2.IMREAD_COLOR)

                # Enqueue frame for classification in a separate process
                if frame_count % skip_classification == 0:
                    if not input_queue.full():
                        input_queue.put((frame_count, image))

                # Always yield the frame to render it
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

                frame_count += 1

            if len(buffer) > 1_000_000:  # Reset if buffer gets too large
                print("Buffer size exceeded limit, resetting buffer.")
                buffer = b''

            # Check for classification results
            try:
                while not output_queue.empty():
                    frame_number, result = output_queue.get_nowait()
                    if result and result['result']['classification']:
                        print(f"Detection in frame {frame_number}: {result['result']['classification']}")
            except queue.Empty:
                pass

    except Exception as e:
        print(f"Error while generating frames: {e}")
    finally:
        process.stdout.close()
        process.stderr.close()
        process.terminate()
        input_queue.put((None, None))  # Sentinel to stop the classify_worker process
        classification_process.join()
        print("Subprocess terminated.")

@app.route('/')
def index():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)