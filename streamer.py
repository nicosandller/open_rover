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
from config import (width, height, channels, frames_to_skip, fps, upload_threshold, upload_to_ei, debug)
from utils import upload_image_to_edge_impulse, draw_bounding_boxes
from camera_handler import CameraHandler

app = Flask(__name__)

# queues 
in_queue = multiprocessing.Queue(maxsize=10)
out_queue = multiprocessing.Queue(maxsize=10)
up_queue = multiprocessing.Queue(maxsize=10)

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

def upload_worker(up_queue):
    global upload_to_ei

    while True:
        image_to_upload = up_queue.get()
        if image_to_upload is None:  # Sentinel value to end the process
            break
        try:
            if upload_to_ei:
                print(upload_image_to_edge_impulse(image_to_upload, api_key))
                pass
        except Exception as e:
            print(f"Upload failed: {e}")

def classification_worker(in_queue, out_queue, up_queue, shared_array_base, array_shape, dtype, lock):
    global upload_threshold

    runner = ImageImpulseRunner(MODEL_PATH)
    try:
        runner.init()
    except Exception as init_error:
        # out_queue.put(('init_error', str(init_error)))
        print('classification worker error: init_error', str(init_error))
        return

    # Attach to the shared array
    shared_array = np.frombuffer(shared_array_base.get_obj(), dtype=dtype).reshape(array_shape)

    while True:
        try:
            frame_number = in_queue.get()
            if frame_number is None:  # Sentinel value to end the process
                break

            # Read from shared array with lock
            with lock:
                image = shared_array.copy()

            # Convert image to RGB
            # TODO: test if this is needed?
            frame_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

            # Extract features from the image using the runner's built-in method
            try:
                features, cropped = runner.get_features_from_image(frame_rgb)
            except Exception as feature_error:
                # out_queue.put((frame_number, 'feature_extraction_error', str(feature_error)))
                print("Error getting features")
                continue

            # Run inference and catch any issues during classification
            try:
                result = runner.classify(features)
                # if there's any detections
                if len(result["result"]["bounding_boxes"]) > 0:
                    # Send them to draw bounding boxes
                    out_queue.put((frame_number, result["result"]["bounding_boxes"]))
                    # Create an array of all predicted prob 'value'
                    confidence_values = [bb['value'] for bb in result["result"]["bounding_boxes"]]
                    # Upload if there's a detection with matching confidence
                    if any(value <= upload_threshold for value in confidence_values):
                        # Upload to Edge Impulse
                        up_queue.put(image)
                        # print(upload_image_to_edge_impulse(image, api_key))
                    
            except Exception as classify_error:
                print("Classification error: ", classify_error)
                # out_queue.put((frame_number, 'classification_error', str(classify_error)))

        except Exception as e:
            print("Some unspecific error whilst classifying: ", e)
            # out_queue.put((None, 'general_error', str(e)))

def yield_frames():
    global shared_array, frames_to_skip, fps, width, height
    latest_result = False
    frame_count = 0

    # Initialize the camera handler
    cam = CameraHandler(width=width, height=height, fps=fps)  # fps can be adjusted if needed
    
    try:
        while True:
            # Get a still image using the CameraHandler class
            decoded_image = cam.get_still()

            if decoded_image is None:
                print(f"Failed to retrieve frame...")
                continue

            if frame_count % frames_to_skip == 0:
                if not in_queue.full():
                    # Write decoded image to shared array with lock
                    with lock:
                        shared_array[:] = decoded_image[:]

                    in_queue.put(frame_count)

            # Check and handle the output queue for results
            try:
                while not out_queue.empty():
                    latest_result = out_queue.get_nowait()
                if latest_result:
                    result_frame_number, bounding_boxes = latest_result
                    decoded_image = cam.draw_bounding_boxes(decoded_image, bounding_boxes)
                    # stop plotting the predictions after 15 frames
                    if frame_count % 30 == 0:
                        latest_result = None

            except queue.Empty:
                pass
            except Exception as e:
                print("Error whilst getting output queue: ", e)
                print("latest result: ", latest_result)
                break

            # Re-encode the modified image back to JPEG format
            _, jpeg_frame = cv2.imencode('.jpg', decoded_image)
            modified_jpeg_frame = jpeg_frame.tobytes()

            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + modified_jpeg_frame + b'\r\n')

            frame_count += 1

    except Exception as e:
        print(f"Error while generating frames: {e}")

    finally:
        cam.shut_down()
        in_queue.put(None)  # Sentinel to stop the classification_worker process
        classification_process.join()
        up_queue.put(None)  # Sentinel to stop the uploader_process process
        uploader_process.join()
        print("Subprocess terminated.")

@app.route('/')
def index():
    return Response(yield_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == "__main__":
    # Start classification worker process
    classification_process = multiprocessing.Process(
            target=classification_worker, 
            args=(
                in_queue,
                out_queue,
                up_queue,
                shared_array_base,
                image_shape,
                image_dtype,
                lock
            )
        )
    classification_process.start()
    # start the uploader worker process
    uploader_process = multiprocessing.Process(
            target=upload_worker, 
            args=(up_queue,)
        )
    uploader_process.start()

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