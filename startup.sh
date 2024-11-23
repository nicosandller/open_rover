#!/bin/bash

# Navigate to the project directory
cd /home/nico/open_rover

# Pull the latest changes from git
git pull origin main

# Source the virtual environment
source /home/nico/open_rover/venv/bin/activate

# Run the web server
python webserver.py