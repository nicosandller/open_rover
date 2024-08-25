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

    def draw_bounding_boxes(self, image, bounding_boxes, model_input_width=320, model_input_height=320):
        """
            Draw circles at the center of bounding boxes on the image.

        Original image is cropped to its shortest side (usually the height). 
        For example a 960 x 540 picture turns into a 540x540 picture, then it gets resized to 320x320
        The model returns the detection coordinates on this last cropped and resized version.
        This function maps the coordinates back to the original size.
        """

        min_coordinate = min(self.width, self.height)

        for bb in bounding_boxes:
            # Only if confidence is high, plot it (?)
            confidence = bb['value']
            # Extract bounding box details and scale them to original image size
            x = float(bb['x'])
            y = float(bb['y'])
            w = int(bb['width'])
            h = int(bb['height'])
            label = bb['label']

            x_resized = int((x * (min_coordinate / model_input_width)) + (min_coordinate - model_input_width))

            y_resized = int(y * (min_coordinate / model_input_height))

            # Draw a solid circle at the center of the bounding box (in red)
            cv2.circle(image, (x_resized, y_resized), 10, (0, 0, 255), -1)

            # Put the label and confidence score above the bounding box
            label_text = f"{label} ({confidence:.2f})"
            cv2.putText(image, label_text, (x_resized, y_resized - 10), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 2)

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
    cam = CameraHandler(width=960, height=540, fps=30)
    try:
        # Test 1: capture still
        print("Test 1: capture still")
        image = cam.get_still()
        if image is not None:
            # Save the captured image
            cv2.imwrite('test_images/camera_handler_test.jpg', image)
            print("Image captured successfully.")


        # Test 2: annotation
        print("Test 2: annotation")
        # image_20240805_210136
        data = {"sampleId":1127881946, "boundingBoxes":[{"label":1,"x":99,"y":115,"width":29,"height":29, "value": 0.75}]}
        image_path = 'test_images/image_to_classify.jpg'
        image = cv2.imread(image_path)

        # TODO: create an integrated test
        # from edge_impulse_linux.image import ImageImpulseRunner
        # runner = ImageImpulseRunner("/Users/nicolassandller/repos/camera_streamer/model_mac.eim")
        # runner.init()
        # frame_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        # features, cropped = runner.get_features_from_image(frame_rgb)
        # cv2.imwrite('test_images/cropped_image_to_classify.jpg', cropped)
        # result = runner.classify(features)
        # print("Classification: ", result)

        if image is not None:
            # Mock bounding boxes data
            mock_bounding_boxes =  [
                    {'height': 8, 'label': 'cat_face', 'value': 0.6137110590934753, 'width': 8, 'x': 80, 'y': 192}
            ]

            # Draw bounding boxes on the loaded image
            annotated_image = cam.draw_bounding_boxes(image, mock_bounding_boxes)

            # Save the annotated image
            cv2.imwrite('test_images/bb_image_to_classify.jpg', annotated_image)
            print("Annotated image saved successfully.")

    finally:
        cam.shut_down()