import requests
import cv2
import numpy as np
from io import BytesIO
from config import project_id
from secrets import api_key

def upload_image_to_edge_impulse(image, api_key, project_id):
    """Upload an in-memory image to Edge Impulse using the provided API key and project ID."""
    # Convert the image to JPEG format in memory
    _, image_encoded = cv2.imencode('.jpg', image)
    image_bytes = image_encoded.tobytes()
    
    # Endpoint for uploading data
    url = f"https://studio.edgeimpulse.com/v1/api/{project_id}/raw-data"
    
    # Prepare the files and data for the POST request
    files = {
        'data': ('image.jpg', image_bytes, 'image/jpeg')
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
        print("Successfully uploaded image")
    else:
        print(f"Failed to upload image: {response.content}")

# Example usage:
# This should be called within the appropriate context where the image is available in memory.
# upload_image_to_edge_impulse(image, api_key, project_id)