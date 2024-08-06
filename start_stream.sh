#!/bin/bash
# Different models for different OS
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS specific commands
    echo "Starting stream for MacOS"
    MODEL_PATH="/Users/nicolassandller/repos/camera_streamer/model_files/model_mac.eim"
else
    echo "Starting stream for Linux"
    # Linux specific commands
    MODEL_PATH="/home/nico/camera_streamer/model_files/model_linux.eim"
fi

# Activate the virtual environment
echo "Sourcing python virtual environment."
source venv/bin/activate
echo "Starting stream..."
python streamer.py $MODEL_PATH