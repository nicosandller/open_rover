import cv2
import numpy as np
from edge_impulse_linux.image import ImageImpulseRunner
import sys

# Ensure the model path is provided
if len(sys.argv) < 2:
    print("Usage: python test_preprocessing.py <MODEL_PATH>")
    sys.exit(1)

MODEL_PATH = sys.argv[1]

# Load the captured frame
frame = cv2.imread("captured_frame.jpg")

if frame is None:
    print("Error: Could not read the frame from 'captured_frame.jpg'.")
    sys.exit(1)

# Convert to RGB
frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

# Initialize the runner
runner = ImageImpulseRunner(MODEL_PATH)
model_info = runner.init()
print('Loaded runner for "' + model_info['project']['owner'] + ' / ' + model_info['project']['name'] + '"')

try:
    # Extract features from the image using the runner's built-in method
    features, cropped = runner.get_features_from_image(frame_rgb)

    # Convert features to a NumPy array for further processing
    features_array = np.array(features)

    # Print the shape and type of features
    print(f"Features extracted with shape: {features_array.shape}")

    # Classify the features
    result = runner.classify(features)

    # Print classification results
    if "classification" in result["result"].keys():
        print('Result (%d ms.) ' % (result['timing']['dsp'] + result['timing']['classification']), end='')
        for label in model_info['model_parameters']['labels']:
            score = result['result']['classification'][label]
            print('%s: %.2f\t' % (label, score), end='')
        print('', flush=True)

    elif "bounding_boxes" in result["result"].keys():
        print('Found %d bounding boxes (%d ms.)' % (len(result["result"]["bounding_boxes"]), result['timing']['dsp'] + result['timing']['classification']))
        for bb in result["result"]["bounding_boxes"]:
            print('\t%s (%.2f): x=%d y=%d w=%d h=%d' % (bb['label'], bb['value'], bb['x'], bb['y'], bb['width'], bb['height']))
            cropped = cv2.rectangle(cropped, (bb['x'], bb['y']), (bb['x'] + bb['width'], bb['y'] + bb['height']), (255, 0, 0), 1)

    if "visual_anomaly_grid" in result["result"].keys():
        print('Found %d visual anomalies (%d ms.)' % (len(result["result"]["visual_anomaly_grid"]), result['timing']['dsp'] + result['timing']['classification']))
        for grid_cell in result["result"]["visual_anomaly_grid"]:
            print('\t%s (%.2f): x=%d y=%d w=%d h=%d' % (grid_cell['label'], grid_cell['value'], grid_cell['x'], grid_cell['y'], grid_cell['width'], grid_cell['height']))
            cropped = cv2.rectangle(cropped, (grid_cell['x'], grid_cell['y']), (grid_cell['x'] + grid_cell['width'], grid_cell['y'] + grid_cell['height']), (255, 125, 0), 1)

    # Save the cropped image for inspection
    cv2.imwrite('debug.jpg', cv2.cvtColor(cropped, cv2.COLOR_RGB2BGR))

except Exception as e:
    print(f"Error during feature extraction or classification: {e}")

finally:
    if runner:
        runner.stop()