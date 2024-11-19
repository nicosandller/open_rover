#!/bin/bash

# Navigate to the specified directory
cd /home/nico/camera_streamer || exit

# Activate the virtual environment
source venv/bin/activate

# pull latest changes
git pull

# Run the Python module
python -m webserver