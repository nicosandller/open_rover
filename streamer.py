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
from config import (width, height, channels, frame_count, frames_to_skip, fps, detection_threshold, upload_threshold)
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
    runner.init()

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
            features, cropped = runner.get_features_from_image(frame_rgb)

            # Run inference and catch any issues during classification
            try:
                result = runner.classify(features)
                if "bounding_boxes" in result["result"].keys():
                    output_queue.put((frame_number, result["result"]["bounding_boxes"]))
                             
                    # Create an array of all predicted prob 'value'
                    confidence_values = [bb['value'] for bb in result["result"]["bounding_boxes"]]

                    # Upload if there's a low confidence prediction
                    if any(value <= upload_threshold for value in confidence_values):
                        # upload to edge impulse
                        print(upload_image_to_edge_impulse(cropped, api_key, result["result"]["bounding_boxes"]))
                    
            except Exception as classify_error:
                print(f"Classification error on frame {frame_number}: {classify_error}")

        except Exception as e:
            print(f"Error during classification setup: {e}")

def generate_frames():
    global shared_array, frame_count, frames_to_skip, fps, width, height
    latest_result = False

    system = platform.system()

    if system == "Linux":
        # Use libcamera-vid on Linux
        process = subprocess.Popen(
            ['libcamera-vid', '--codec', 'mjpeg', '--inline', '-o', '-', '-t', '0', '--width', str(width), '--height', str(height), '--framerate', fps],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
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

                    # Convert frame to numpy array for processing
                    try:
                        image = cv2.imdecode(np.frombuffer(frame, np.uint8), cv2.IMREAD_COLOR)
                    except Exception as decode_error:
                        print(f"Error decoding frame {frame_count}: {decode_error}")
                        continue

                    if image is None:
                        print(f"Failed to decode frame {frame_count}")
                        continue

                    # Write to shared array with lock
                    with lock:
                        shared_array[:] = image[:]

                    if frame_count % frames_to_skip == 0:
                        if not input_queue.full():
                            input_queue.put(frame_count)
                        
                    try:
                        while not output_queue.empty():
                            latest_result = output_queue.get_nowait()
                        if latest_result:
                            result_frame_number, bounding_boxes = latest_result
                            image = draw_bounding_boxes(image, bounding_boxes, width, height, detection_threshold)
                    except queue.Empty:
                        pass

                    _, jpeg_frame = cv2.imencode('.jpg', image)
                    modified_frame = jpeg_frame.tobytes()

                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + modified_frame + b'\r\n')

                    frame_count += 1

                if len(buffer) > 1_000_000:
                    print("Buffer size exceeded limit, resetting buffer.")
                    buffer = b''

        except Exception as e:
            print(f"Error while generating frames: {e}")
        finally:
            process.stdout.close()
            process.stderr.close()
            process.terminate()
            input_queue.put(None)
            classification_process.join()
            print("Subprocess terminated.")

    elif system == "Darwin":
        # Use OpenCV on macOS
        cap = cv2.VideoCapture(0)  # 0 for default camera
        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    print("Failed to capture image from camera.")
                    break

                # Resize frame to match expected width and height
                frame = cv2.resize(frame, (width, height))

                # Write to shared array with lock
                with lock:
                    shared_array[:] = frame[:]

                if frame_count % frames_to_skip == 0:
                    if not input_queue.full():
                        input_queue.put(frame_count)

                try:
                    while not output_queue.empty():
                        latest_result = output_queue.get_nowait()
                    if latest_result:
                        result_frame_number, bounding_boxes = latest_result
                        frame = draw_bounding_boxes(frame, bounding_boxes, width, height, detection_threshold)
                except queue.Empty:
                    pass

                _, jpeg_frame = cv2.imencode('.jpg', frame)
                modified_frame = jpeg_frame.tobytes()

                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + modified_frame + b'\r\n')

                frame_count += 1

        except Exception as e:
            print(f"Error while capturing frames: {e}")
        finally:
            cap.release()

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