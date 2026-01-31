#!/bin/bash

# Ensure script errors are visible
set -x

echo "=============================="
echo "Starting Phoenix on Railway"
echo "PORT: $PORT"
echo "=============================="

# 1. Start the Engine in Background
# NOTE: Uses nohup and ignores errors to prevent blocking the API
echo "Starting Phoenix Engine in background..."
nohup python engine/core.py > /dev/null 2>&1 &
echo "Engine PID: $!"

# 2. Start the API Server in Foreground
# This MUST bind to 0.0.0.0:$PORT for Railway
echo "Starting Gunicorn API Server on port $PORT..."
exec gunicorn api.server:app --bind "0.0.0.0:$PORT" --workers 2 --threads 2 --timeout 120 --access-logfile - --error-logfile -
