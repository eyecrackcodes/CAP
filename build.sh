#!/bin/bash
# Build script for Railway

# Install dependencies
pip install -r requirements.txt

# Make scripts executable
chmod +x railway-run.sh
chmod +x start.sh

echo "Build complete!" 