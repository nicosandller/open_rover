#!/bin/bash
# Activate the virtual environment
echo "Sourcing python virtual environment."
source venv/bin/activate
# Stream
echo "Starting stream..."
python streamer.py /home/nico/camera_streamer/model.eim