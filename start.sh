#!/bin/bash
echo "Starting the Flask application..."

# Try running with gunicorn first
if command -v gunicorn &> /dev/null; then
    echo "Using gunicorn..."
    gunicorn app:app
else
    # Fall back to basic Python if gunicorn isn't available
    echo "Using python directly..."
    python server.py
fi 