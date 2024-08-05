import sys
import cv2
import queue
import platform
import subprocess
import numpy as np
import multiprocessing
from flask import Flask, Response
from edge_impulse_linux.image import ImageImpulseRunner

from secrets import api_key
from config import (width, height, channels, frame_count, frames_to_skip, fps, detection_threshold, upload_threshold, debug)
from utils import upload_image_to_edge_impulse, draw_bounding_boxes

app = Flask(__name__)

# queues 
input_queue = multiprocessing.Queue(maxsize=10)
output_queue = multiprocessing.Queue(maxsize=10)

# Correctly defining the image shape
image_shape = (height, width, channels)
image_dtype = np.uint8

# Create shared array with a lock for parallel processing
lock = multiprocessing.Lock()
shared_array_base = multiprocessing.Array('B', int(np.prod(image_shape)), lock=lock)
shared_array = np.frombuffer(shared_array_base.get_obj(), dtype=image_dtype).reshape(image_shape)

# Get the model path from the command-line argument
if len(sys.argv) < 2:
    print("Usage: python streamer.py <MODEL_PATH>")
    sys.exit(1)

MODEL_PATH = sys.argv[1]

def classification_worker(input_queue, output_queue, shared_array_base, array_shape, dtype, lock):
    global upload_threshold

    runner = ImageImpulseRunner(MODEL_PATH)
    try:
        runner.init()
    except Exception as init_error:
        # output_queue.put(('init_error', str(init_error)))
        print('classification worker error: init_error', str(init_error))
        return

    # Attach to the shared array
    shared_array = np.frombuffer(shared_array_base.get_obj(), dtype=dtype).reshape(array_shape)

    while True:
        try:
            frame_number = input_queue.get()
            if frame_number is None:  # Sentinel value to end the process
                break

            # Read from shared array with lock
            with lock:
                image = shared_array.copy()

            # Convert image to RGB
            frame_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

            # Extract features from the image using the runner's built-in method
            try:
                features, cropped = runner.get_features_from_image(frame_rgb)
            except Exception as feature_error:
                # output_queue.put((frame_number, 'feature_extraction_error', str(feature_error)))
                print("Error getting features")
                continue

            # Run inference and catch any issues during classification
            try:
                result = runner.classify(features)
                if "bounding_boxes" in result["result"]:
                    output_queue.put((frame_number, result["result"]["bounding_boxes"]))
                             
                    # Create an array of all predicted prob 'value'
                    confidence_values = [bb['value'] for bb in result["result"]["bounding_boxes"]]

                    # Upload if there's a low confidence prediction
                    if any(value <= upload_threshold for value in confidence_values):
                        # Upload to Edge Impulse
                        print(upload_image_to_edge_impulse(cropped, api_key, result["result"]["bounding_boxes"]))
                    
            except Exception as classify_error:
                print("Classification error: ", classify_error)
                # output_queue.put((frame_number, 'classification_error', str(classify_error)))

        except Exception as e:
            print("Some unspecific error whilst classifying: ", e)
            # output_queue.put((None, 'general_error', str(e)))

def generate_frames():
    global shared_array, frame_count, frames_to_skip, fps, width, height
    latest_result = False

    system = platform.system()
    buffer = b''
    cap = None
    process = None
    decoded_image = None  # Initialize the image variable

    if system == "Linux":
        # Use libcamera-vid on Linux
        process = subprocess.Popen(
            ['libcamera-vid', '--codec', 'mjpeg', '--inline', '-o', '-', '-t', '0', '--width', str(width), '--height', str(height), '--framerate', fps],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
    elif system == "Darwin":
        # Use OpenCV on macOS
        cap = cv2.VideoCapture(0)  # 0 for default camera

    try:
        while True:
            if system == "Linux":
                # Read frame data from libcamera-vid
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
                    try:
                        decoded_image = cv2.imdecode(np.frombuffer(frame, np.uint8), cv2.IMREAD_COLOR)
                    except Exception as decode_error:
                        print(f"Error decoding frame {frame_count}: {decode_error}")

            elif system == "Darwin":
                # Read frame data from OpenCV capture
                ret, decoded_image = cap.read()
                if not ret:
                    print("Failed to capture image from camera.")
                    decoded_image = None
                else:
                    # Resize frame to match expected width and height
                    decoded_image = cv2.resize(decoded_image, (width, height))

            if decoded_image is None:
                print(f"Failed to retrieve frame...")
                continue

            if frame_count % frames_to_skip == 0:
                if not input_queue.full():
                    # Write decoded image to shared array with lock
                    with lock:
                        shared_array[:] = decoded_image[:]

                    input_queue.put(frame_count)

            # Check and handle the output queue for results
            try:
                while not output_queue.empty():
                    latest_result = output_queue.get_nowait()
                if latest_result:
                    result_frame_number, bounding_boxes = latest_result
                    decoded_image = draw_bounding_boxes(decoded_image, bounding_boxes, width, height, detection_threshold)
            except queue.Empty:
                pass
            except Exception as e:
                print("Error whilst getting output queue: ", e)
                print("latest result: ", latest_result)
                break

            # Encode the modified image back to JPEG format
            _, jpeg_frame = cv2.imencode('.jpg', decoded_image)
            modified_jpeg_frame = jpeg_frame.tobytes()

            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + modified_jpeg_frame + b'\r\n')

            frame_count += 1

            if len(buffer) > 1_000_000:
                print("Buffer size exceeded limit, resetting buffer.")
                buffer = b''

    except Exception as e:
        print(f"Error while generating frames: {e}")

    finally:
        if system == "Linux":
            process.stdout.close()
            process.stderr.close()
            process.terminate()
        elif system == "Darwin":
            cap.release()
        input_queue.put(None)  # Sentinel to stop the classification_worker process
        classification_process.join()
        print("Subprocess terminated.")

@app.route('/')
def index():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == "__main__":
    # Start classification process
    classification_process = multiprocessing.Process(
            target=classification_worker, 
            args=(
                input_queue,
                output_queue,
                shared_array_base,
                image_shape,
                image_dtype,
                lock
            )
        )
    classification_process.start()

    # Check platform and set appropriate port
    system = platform.system()
    if system == "Linux":
        app_port = 5000
    elif system == "Darwin":
        app_port = 5001
    else:
        print(f"Unsupported system: {system}")
        exit(1)

    # Start running the application
    app.run(host='0.0.0.0', port=app_port)