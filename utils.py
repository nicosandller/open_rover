import cv2
import json
import requests
import numpy as np
from datetime import datetime

from secrets import api_key

def draw_bounding_boxes(image, bounding_boxes, frame_width, frame_height, threshold=0.7, cropped_width=320, cropped_height=320):
    """Draw circles at the center of bounding boxes on the image."""

    # Calculate scaling factors
    x_scale = frame_width / cropped_width
    y_scale = frame_height / cropped_height

    for bb in bounding_boxes:
        # Only if confidence is high, plot it.
        confidence = bb['value']
        if confidence >= threshold:  # Keeping confidence as a float for comparison
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

def upload_image_to_edge_impulse(image, api_key, bounding_boxes, model_version):
    """
        Upload an in-memory image to Edge Impulse using the provided API key and project ID.
    """
    if not isinstance(image, np.ndarray):
        print("Error: The input image is not a valid numpy array.")
        return
    
    # Ensure the image is in uint8 format
    if image.dtype != np.uint8:
        image = image.astype(np.uint8)

    # Convert the image to JPEG format in memory
    success, image_encoded = cv2.imencode('.jpg', image)
    if not success:
        print("Error: Failed to encode the image.")
        return

    image_bytes = image_encoded.tobytes()
    
    # Endpoint for uploading data
    url = "https://ingestion.edgeimpulse.com/api/training/files"

    # Generate a unique filename using the current timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"image_{timestamp}.jpg"

    # Prepare the bounding box metadata
    bbox_meta = {
            "version": model_version,
            "labels": [],
            "x": [],
            "y": [],
            "width": [],
            "height": [],
            "value": []
    }
    for bb in bounding_boxes:
        bbox_meta['labels'].append(bb['label'])
        bbox_meta['x'].append(bb['x'])
        bbox_meta['y'].append(bb['y'])
        bbox_meta['width'].append(bb['width'])
        bbox_meta['height'].append(bb['height'])
        bbox_meta['value'].append(bb['value'])

    bbox_meta = {key: str(value) for key, value in bbox_meta.items()}

    bbox_meta = json.dumps(bbox_meta)

    # Prepare the payload
    payload = (
        ('data', (filename, image_bytes, 'image/jpeg')),
    )

    headers = {
        'x-api-key': api_key,
        'x-metadata': bbox_meta,
        'x-disallow-duplicates': 'true'
    }

    # POST request
    response = requests.post(url, headers=headers, files=payload)
    response_content = json.loads(response.content.decode('utf-8'))

    # Check if the upload was successful
    if response_content.get('success'):
        file_success = all(file.get('success', False) for file in response_content.get('files', []))
        if file_success:
            return f"Successfully uploaded {filename}."
        else:
            errors = [file.get('error') for file in response_content.get('files', []) if not file.get('success', False)]
            return f"Failed to upload {filename}: {errors}"
    else:
        return f"Failed to upload {filename}: {response.status_code} - {response.content}"
    


def test_upload_image_to_edge_impulse():
    global api_key

    # Load the image from a file
    image_path = 'test_images/camera_handler_test.jpg'
    image = cv2.imread(image_path)

    # Check if the image was loaded correctly
    if image is None:
        print(f"Failed to load image from {image_path}")
        return

    # Define mock bounding boxes
    mock_bounding_boxes = [
        {'height': 8, 'label': 'cat_face', 'value': 0.6261171698570251, 'width': 8, 'x': 216, 'y': 112}
    ]

    # Define a mock model version
    model_version = "testing uploader"

    # Call the function and print the result
    result = upload_image_to_edge_impulse(image, api_key, mock_bounding_boxes, model_version)
    print(result)

if __name__ == "__main__":
    # test 1: test upload to EI
    test_upload_image_to_edge_impulse()
