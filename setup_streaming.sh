#!/bin/bash

# Update the package list
sudo apt-get update

# Install Python 3 and virtual environment package
# sudo apt-get install -y python3 python3-venv

# Install libcamera and necessary tools
sudo apt-get install -y libcamera-apps

# Install ffmpeg for video handling capabilities (optional but recommended)
sudo apt-get install -y ffmpeg

# install for use in pyaudio
sudo apt-get install portaudio19-dev python3-pyaudio

#re source bash
source ~/.bashrc

# Create a virtual environment
python3 -m venv venv

# Activate the virtual environment
source venv/bin/activate

# Install Flask and others inside the virtual environment
pip install -r requirements.txt

# Print completion message
echo "Setup complete!!"