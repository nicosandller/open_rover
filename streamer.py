import sys
import cv2
import queue
import subprocess
import numpy as np
import multiprocessing
from flask import Flask, Response
from edge_impulse_linux.image import ImageImpulseRunner

from config import (width, height, channels, frame_count, frames_to_skip, fps)

app = Flask(__name__)

# queues 
input_queue = multiprocessing.Queue(maxsize=10)
output_queue = multiprocessing.Queue(maxsize=10)

# Correctly defining the image shape
image_shape = (height, width, channels)
image_dtype = np.uint8

# Create shared array with a lock for parallel priocessing
lock = multiprocessing.Lock()
shared_array_base = multiprocessing.Array('B', int(np.prod(image_shape)), lock=lock)
shared_array = np.frombuffer(shared_array_base.get_obj(), dtype=image_dtype).reshape(image_shape)

# Get the model path from the command-line argument
if len(sys.argv) < 2:
    print("Usage: python streamer.py <MODEL_PATH>")
    sys.exit(1)

MODEL_PATH = sys.argv[1]

def classification_worker(input_queue, output_queue, shared_array_base, array_shape, dtype, lock):
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

            # Log the shape and type of the image to ensure correctness
            print(f"Processing frame {frame_number}: shape={image.shape}, dtype={image.dtype}")

            # Convert image to RGB
            frame_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

            # Extract features from the image using the runner's built-in method
            features, cropped = runner.get_features_from_image(frame_rgb)

            # Run inference and catch any issues during classification
            try:
                result = runner.classify(features)
                # output_queue.put((frame_number, result))
                if "bounding_boxes" in result["result"].keys():
                    print('Found %d bounding boxes (%d ms.)' % (len(result["result"]["bounding_boxes"]), result['timing']['dsp'] + result['timing']['classification']))
                    for bb in result["result"]["bounding_boxes"]:
                        print('\t%s (%.2f): x=%d y=%d w=%d h=%d' % (bb['label'], bb['value'], bb['x'], bb['y'], bb['width'], bb['height']))

                    # Save the cropped image for inspection
                    cv2.imwrite('debug_cropped.jpg', cv2.cvtColor(cropped, cv2.COLOR_RGB2BGR))
                    # Send the boxes out back to main process
                    output_queue.put((frame_number, result["result"]["bounding_boxes"]))

            except Exception as classify_error:
                print(f"Classification error on frame {frame_number}: {classify_error}")
                # output_queue.put((frame_number, None))

        except Exception as e:
            print(f"Error during classification setup: {e}")
            # output_queue.put((frame_number, None))

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

def draw_bounding_boxes(image, bounding_boxes, cropped_width=320, cropped_height=320):
    """Draw circles at the center of bounding boxes on the image."""
    global width, height

    # Calculate scaling factors
    x_scale = width / cropped_width
    y_scale = height / cropped_height

    for bb in bounding_boxes:
        confidence = bb['value']
        # Only if confidence is high, plot it.
        if confidence > 0.7:  # Keeping confidence as a float for comparison
            # Extract bounding box details and scale them to original image size
            x = int(bb['x'] * x_scale)
            y = int(bb['y'] * y_scale)
            w = int(bb['width'] * x_scale)
            h = int(bb['height'] * y_scale)
            label = bb['label']

            # Calculate the center of the bounding box
            center_x = x + w // 2
            center_y = y + h // 2

            # Draw a solid circle at the center of the bounding box (in red)
            cv2.circle(image, (center_x, center_y), 10, (0, 0, 255), -1)
            # # Draw the rectangle (in red)
            # cv2.rectangle(image, (x, y), (x + w, y + h), (0, 0, 255), 2)

            # Put the label and confidence score above the bounding box
            label_text = f"{label} ({confidence:.2f})"
            cv2.putText(image, label_text, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 2)

    return image

def generate_frames():
    global shared_array, frame_count, frames_to_skip, fps
    latest_result = False

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

                # Ensure the image was decoded correctly
                if image is None:
                    print(f"Failed to decode frame {frame_count}")
                    continue

                # for debugging
                # cv2.imwrite('debug_image_0.jpg', image)

                # Write to shared array with lock
                with lock:
                    shared_array[:] = image[:]

                # Enqueue frame number for classification in a separate process
                if frame_count % frames_to_skip == 0:
                    if not input_queue.full():
                        input_queue.put(frame_count)
                        
                # Check for classification results and draw bounding boxes
                try:
                    while not output_queue.empty():
                        latest_result = output_queue.get_nowait()
                    if latest_result:
                        result_frame_number, bounding_boxes = latest_result
                        # if result_frame_number == frame_count:
                        image = draw_bounding_boxes(image, bounding_boxes)
                except queue.Empty:
                    pass

                # Encode the modified image back to JPEG format
                _, jpeg_frame = cv2.imencode('.jpg', image)
                modified_frame = jpeg_frame.tobytes()

                # Always yield the frame to render it
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + modified_frame + b'\r\n')

                frame_count += 1

            if len(buffer) > 1_000_000:  # Reset if buffer gets too large
                print("Buffer size exceeded limit, resetting buffer.")
                buffer = b''

    except Exception as e:
        print(f"Error while generating frames: {e}")
    finally:
        process.stdout.close()
        process.stderr.close()
        process.terminate()
        input_queue.put(None)  # Sentinel to stop the classification_worker process
        classification_process.join()
        print("Subprocess terminated.")

@app.route('/')
def index():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)