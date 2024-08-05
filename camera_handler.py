import cv2
import platform
import subprocess
import numpy as np

class CameraHandler:
    def __init__(self, width=1920, height=1080, fps=30):
        self.system = platform.system()
        self.cap = None
        self.process = None
        self.width = width
        self.height = height
        self.fps = fps

        if self.system == "Linux":
            self.init_linux_camera()
        elif self.system == "Darwin":
            self.init_macos_camera()
        else:
            raise NotImplementedError(f"Unsupported system: {self.system}")

    def init_linux_camera(self):
        # Set up for libcamera-vid with additional parameters
        self.process = subprocess.Popen(
            ['libcamera-vid', '--codec', 'mjpeg', '--inline', '-o', '-', '-t', '0', 
             '--width', str(self.width), '--height', str(self.height), '--framerate', str(self.fps)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )

    def init_macos_camera(self):
        # Set up for OpenCV VideoCapture
        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            raise Exception("Failed to open camera on macOS.")
        # self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        # self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        # self.cap.set(cv2.CAP_PROP_FPS, int(self.fps))

    def get_still(self):
        if self.system == "Linux":
            return self.get_linux_still()
        elif self.system == "Darwin":
            return self.get_macos_still()

    def get_linux_still(self):
        if not self.process:
            raise Exception("Linux camera process is not initialized.")

        buffer = b''
        while True:
            chunk = self.process.stdout.read(1024)
            if not chunk:
                print("No more data from libcamera-vid.")
                break
            buffer += chunk
            end = buffer.find(b'\xff\xd9')  # JPEG end of image marker

            if end != -1:
                frame = buffer[:end+2]
                buffer = buffer[end+2:]
                # decode image
                decoded_frame = cv2.imdecode(np.frombuffer(frame, np.uint8), cv2.IMREAD_COLOR)
                if decoded_frame is not None:
                    return decoded_frame

            # Check if buffer is too large and reset if necessary
            if len(buffer) > 1_000_000:
                print("Buffer size exceeded limit, resetting buffer.")
                buffer = b''

        return None

    def get_macos_still(self):
        if not self.cap:
            raise Exception("macOS camera is not initialized.")

        ret, frame = self.cap.read()
        if ret:
            resized_frame = cv2.resize(frame, (self.width, self.height))
            return resized_frame
        else:
            print("Failed to capture image from macOS camera.")
            return None

    def draw_bounding_boxes(self, image, bounding_boxes, cropped_width=320, cropped_height=320):
        """Draw circles at the center of bounding boxes on the image."""

        # Calculate scaling factors
        x_scale = self.width / cropped_width
        y_scale = self.height / cropped_height

        for bb in bounding_boxes:
            # Only if confidence is high, plot it (?)
            confidence = bb['value']
            # Extract bounding box details and scale them to original image size
            x = int(bb['x'] * x_scale)
            y = int(bb['y'] * y_scale)
            w = int(bb['width'])
            h = int(bb['height'])
            label = bb['label']

            # Calculate the center of the bounding box
            center_x = x + w // 2
            center_y = y + h // 2

            # Draw a solid circle at the center of the bounding box (in red)
            cv2.circle(image, (center_x, center_y), 10, (0, 0, 255), -1)

            # Put the label and confidence score above the bounding box
            label_text = f"{label} ({confidence:.2f})"
            cv2.putText(image, label_text, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 2)

        return image

    def shut_down(self):
        if self.system == "Linux" and self.process:
            self.process.stdout.close()
            self.process.stderr.close()
            self.process.terminate()
        elif self.system == "Darwin" and self.cap:
            self.cap.release()

# Test: python camera_handler.py
if __name__ == "__main__":
    # Initialize CameraHandler with custom resolution and frame rate
    cam = CameraHandler(width=320, height=320, fps=30)
    try:
        image = cam.get_still()
        if image is not None:
            cv2.imwrite('camera_handler_test.jpg', image)
            print("Image captured successfully.")
    finally:
        cam.shut_down()