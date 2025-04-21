#!/bin/bash
# Railway-specific run script

echo "Starting Railway application"
cd "$(dirname "$0")"
export PYTHONUNBUFFERED=1

# Check if gunicorn exists and run with it
if command -v gunicorn &> /dev/null; then
    echo "Using gunicorn"
    exec gunicorn app:app
else
    # Fall back to built-in Flask server
    echo "Using Flask built-in server"
    python railway.py
fi 