#!/bin/bash

# Navigate to the specified directory
cd /home/nico/camera_streamer || exit

# Activate the virtual environment
source venv/bin/activate

# make sure depenendices are installed
pip install -r requirements.txt

# pull latest changes
git pull

# Run the Python module
python -m webserver