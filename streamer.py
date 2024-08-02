from flask import Flask, Response
import subprocess
import cv2
import numpy as np
from edge_impulse_linux.runner import ImpulseRunner
import sys
import multiprocessing

app = Flask(__name__)

width = 960
height = 540

# Get the model path from the command-line argument
if len(sys.argv) < 2:
    print("Usage: python streamer.py <MODEL_PATH>")
    sys.exit(1)

MODEL_PATH = sys.argv[1]

def classify_worker(input_queue, output_queue, model_path, array_shape, dtype):
    runner = ImpulseRunner(model_path)
    runner.init()
    array_size = int(np.prod(array_shape))
    shared_array = np.frombuffer(multiprocessing.Array('B', array_size).get_obj(), dtype=dtype).reshape(array_shape)
    
    while True:
        try:
            frame_number = input_queue.get()
            if frame_number is None:  # Sentinel value to end the process
                break

            # Read from shared array
            image = shared_array.copy()

            # Log the shape and type of the image to ensure correctness
            print(f"Processing frame {frame_number}: shape={image.shape}, dtype={image.dtype}")

            # Convert image to RGB and resize for the model
            resized = cv2.resize(image, (320, 320))
            rgb_frame = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
            features = np.expand_dims(rgb_frame.astype(np.float32), axis=0)
            features_list = features.tolist()

            # Run inference and catch any issues during classification
            try:
                result = runner.classify(features_list)
                output_queue.put((frame_number, result))
            except Exception as classify_error:
                print(f"Classification error on frame {frame_number}: {classify_error}")
                output_queue.put((frame_number, None))

        except Exception as e:
            print(f"Error during classification setup: {e}")
            output_queue.put((frame_number, None))

input_queue = multiprocessing.Queue(maxsize=10)
output_queue = multiprocessing.Queue(maxsize=10)

# Ensure that the image dimensions are integers
height = int(height)
width = int(width)
channels = 3  # Assuming 3 channels for an RGB image

# Correctly defining the image shape
image_shape = (height, width, channels)
image_dtype = np.uint8

# Create shared array
shared_array_base = multiprocessing.Array('B', int(np.prod(image_shape)))
shared_array = np.frombuffer(shared_array_base.get_obj(), dtype=image_dtype).reshape(image_shape)

# Start classification process
classification_process = multiprocessing.Process(target=classify_worker, args=(input_queue, output_queue, MODEL_PATH, image_shape, image_dtype))
classification_process.start()

def generate_frames():
    global shared_array
    process = subprocess.Popen(
                ['libcamera-vid', '--codec', 'mjpeg', '--inline', '-o', '-', '-t', '0', '--width', str(width), '--height', str(height)],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
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
                try:
                    image = cv2.imdecode(np.frombuffer(frame, np.uint8), cv2.IMREAD_COLOR)
                except Exception as decode_error:
                    print(f"Error decoding frame {frame_count}: {decode_error}")
                    continue

                # Ensure the image was decoded correctly
                if image is None:
                    print(f"Failed to decode frame {frame_count}")
                    continue

                shared_array[:] = image[:]

                # Enqueue frame number for classification in a separate process
                if frame_count % skip_classification == 0:
                    if not input_queue.full():
                        input_queue.put(frame_count)

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
        input_queue.put(None)  # Sentinel to stop the classify_worker process
        classification_process.join()
        print("Subprocess terminated.")

@app.route('/')
def index():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)