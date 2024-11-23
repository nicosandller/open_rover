# Open Rover

Open Rover is a project designed to control a rover using a web interface. The rover can be navigated manually using joystick.

## Features

- **Live Video Streaming**: The rover provides a live video feed from its camera, which can be toggled on or off via the web interface.
- **Joystick Controls**: Users can control the rover's movement using a joystick interface on the web page.
- **Explorer Mode**: When enabled, the rover navigates autonomously using vision-based navigation.
- **Web Interface**: Access the rover's control interface through a web browser.

## Components

- **RoverWebServer**: A Flask-based web server that handles video streaming and WebSocket communication for joystick and toggle controls.
- **MotorDriver**: A class to control the rover's motors using GPIO pins on a Raspberry Pi.
- **CameraHandler**: Manages the camera feed for live streaming.
- **Web Interface**: HTML and JavaScript files to provide a user-friendly control panel.

## Setup Instructions

1. **Hardware Setup**:
   - Connect the motors to the Raspberry Pi using the specified GPIO pins.
   - Attach a compatible camera to the Raspberry Pi.

2. **Software Setup**:
   - Ensure you have Python and the necessary libraries installed (`Flask`, `Flask-SocketIO`, `RPi.GPIO`, `OpenCV`).
   - Clone the repository and navigate to the project directory.

3. **Permissions**:
   - Change permissions to be able to read the model file if necessary:
     ```bash
     chmod +x /path_to/model.eim
     ```

4. **Running the Rover**:
   - SSH into your Raspberry Pi:
     ```bash
     ssh pi@raspberrypi.local
     ```
   - Clone the repository and navigate to the project directory:
     ```bash
     git clone https://github.com/your_username/open_rover.git
     cd open_rover
     ```
   - Create a virtual environment:
     ```bash
     python3 -m venv venv
     ```
   - Activate the virtual environment:
     ```bash
     source venv/bin/activate
     ```
   - Install the required packages:
     ```bash
     pip install -r requirements.txt
     ```
   - Execute the `rover.py` script to start the system:
     ```bash
     python rover.py
     ```
   - Access the web interface at `http://raspberrypi.local:5001` to control the rover.

## Usage

- **Video Stream**: Toggle the video stream on or off using the "Video Stream" switch on the web interface.
- **Motors**: Enable or disable the motors using the "Motors" switch.
- **Joystick**: Use the on-screen joystick to manually control the rover's movement.

## Notes

- Ensure the Raspberry Pi is connected to the same network as the device accessing the web interface.
- The rover's autonomous navigation relies on an external API for vision-based instructions.

## Troubleshooting

- If the video stream does not display, ensure the camera is properly connected and permissions are set.
- Check the console logs for any connection errors or warnings.

For further assistance, refer to the source code and comments within the files for detailed implementation details.


## How to Set Up and Verify Auto-Startup

1. **Make the Startup Script Executable**:
   - Run the following command to make `startup.sh` executable:
     ```bash
     chmod +x startup.sh
     ```

2. **Edit Crontab for Auto-Startup**:
   - Open the crontab editor:
     ```bash
     crontab -e
     ```
   - Add the following line to schedule the script to run at boot:
     ```
     @reboot /home/pi/open_rover/startup.sh > /home/pi/open_rover/rover.log 2>&1
     ```

3. **Verify Crontab Entry**:
   - Check if the crontab entry was added successfully:
     ```bash
     crontab -l
     ```

4. **Reboot and Test**:
   - Reboot the Raspberry Pi to test the auto-startup:
     ```bash
     sudo reboot
     ```

5. **Check the Logs**:
   - After rebooting, read the logs to ensure the script ran correctly:
     ```bash
     cat /home/pi/open_rover/rover.log
     ```

6. **Confirm the Web Server is Running**:
   - Verify that the Python web server is running:
     ```bash
     ps aux | grep python
     ```
   - You should see an output similar to:
     ```
     pi         628  6.5  5.0 848080 21436 ?        Sl   12:03   0:08 python webserver.py
     pi        2216  0.0  0.4   6088  1792 pts/0    S+   12:05   0:00 grep --color=auto python
     ```

7. **Kill webserver**:
    ```python
      kill <PID>
    ```