import sys
import cv2
import queue
import signal
import platform
import subprocess
import numpy as np
import multiprocessing
from flask import Flask, Response
from edge_impulse_linux.image import ImageImpulseRunner

from secrets import api_key
from old_files.config import (width, height, channels, frames_to_skip, fps, upload_threshold, stickiness)
from utils import upload_image_to_edge_impulse
from open_rover.camera import CameraHandler

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
    print("Usage: python streamer.py <MODEL_PATH> <0_1 for DEBUG> <0_1 for Upload to EI>")
    sys.exit(1)

MODEL_PATH      = sys.argv[1]
DEBUG           = int(sys.argv[2])
UPLOAD_TO_EI    = int(sys.argv[3])

# Handle termination of subprocesses with ctrl + C
def signal_handler():
    print("Termination signal received. Cleaning up...")
    in_queue.put(None)  # Sentinel to stop the classification_worker process
    classification_process.join()
    up_queue.put(None)  # Sentinel to stop the uploader_process process
    uploader_process.join()
    print("Subprocesses terminated.")
    sys.exit(0)

def upload_worker(up_queue):
    global UPLOAD_TO_EI

    while True:
        image_to_upload, bounding_boxes = up_queue.get()
        if image_to_upload is None:  # Sentinel value to end the process
            break
        try:
            if UPLOAD_TO_EI:
                print(upload_image_to_edge_impulse(image_to_upload, api_key, bounding_boxes, MODEL_PATH))
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
                    bounding_boxes = result["result"]["bounding_boxes"]
                    out_queue.put((frame_number, bounding_boxes))
                    if DEBUG:
                        print(bounding_boxes)
                    # Create an array of all predicted prob 'value'
                    confidence_values = [bb['value'] for bb in result["result"]["bounding_boxes"]]
                    # Upload if there's a detection with matching confidence
                    if any(value <= upload_threshold for value in confidence_values):
                        # Upload to Edge Impulse
                        up_queue.put((image, result["result"]["bounding_boxes"]))
                    
            except Exception as classify_error:
                print("Classification error: ", classify_error)
                # out_queue.put((frame_number, 'classification_error', str(classify_error)))

        except Exception as e:
            print("Some unspecific error whilst classifying: ", e)
            # out_queue.put((None, 'general_error', str(e)))

def yield_frames():
    global shared_array, frames_to_skip, fps, width, height, stickiness
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
                    if frame_count % stickiness == 0:
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

@app.route('/')
def index():
    return Response(yield_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == "__main__":
    # Register the signal handler for SIGINT (Ctrl+C)
    signal.signal(signal.SIGINT, signal_handler)
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

    try:
        # Start running the application
        app.run(host='0.0.0.0', port=app_port)
    except Exception as e:
        print(f"Error occurred: {e}")
    finally:
        signal_handler()  # Call the signal handler to clean up