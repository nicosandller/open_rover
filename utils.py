import cv2
import numpy as np
import requests

def upload_image_to_edge_impulse(image, api_key, project_id):
    """Upload an in-memory image to Edge Impulse using the provided API key and project ID."""
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
    url = f"https://ingestion.edgeimpulse.com/api/{project_id}/raw"
    
    # Prepare the files and data for the POST request
    files = {
        'files': ('image.jpg', image_bytes, 'image/jpeg')
    }
    data = {
        'filename': 'image.jpg'
    }
    headers = {
        'x-api-key': api_key
    }

    # Send POST request
    response = requests.post(url, files=files, data=data, headers=headers)

    # Check response
    if response.status_code == 200:
        print("Successfully uploaded image.")
    else:
        print(f"Failed to upload image: {response.status_code} - {response.content}")