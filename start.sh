#!/bin/bash

# 1. Start the Engine in Background
# This process collects data 24/7 and writes to state.json
echo "Starting Phoenix Engine..."
python engine/core.py &

# 2. Start the API Server in Foreground
# This process serves state.json to the internet
# Gunicorn is used for production stability
echo "Starting Phoenix API..."
gunicorn api.server:app --bind 0.0.0.0:$PORT --workers 4 --threads 2
